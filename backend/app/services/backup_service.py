from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.maintenance import set_restore_in_progress
from app.core.paths import BACKUPS_DIR, DAILY_BACKUPS_DIR, PRE_IMPORT_BACKUPS_DIR, PRE_RESTORE_BACKUPS_DIR
from app.core.security import sha256_file
from app.models.domain import BackupManifest
from app.services.audit_service import record_audit


BACKUP_DIRS = {
    "pre_import": PRE_IMPORT_BACKUPS_DIR,
    "daily": DAILY_BACKUPS_DIR,
    "pre_restore": PRE_RESTORE_BACKUPS_DIR,
    "manual": BACKUPS_DIR / "manual",
    "pre_rollback": BACKUPS_DIR / "pre_rollback",
}


def _database_path(db: Session) -> Path:
    url = db.get_bind().url
    if url.drivername != "sqlite":
        raise RuntimeError("Only SQLite backups are supported.")
    database = url.database
    if database is None:
        raise RuntimeError("SQLite database path is unavailable.")
    return Path(database).resolve()


def _schema_version(db: Session) -> str:
    try:
        version = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        return version or "unversioned"
    except Exception:
        return "unversioned"


def validate_sqlite(path: Path) -> None:
    conn = None
    try:
        conn = sqlite3.connect(path)
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            raise ValueError(result[0] if result else "No integrity result")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        required_tables = {"audit_log"}
        missing_tables = sorted(required_tables - tables)
        if missing_tables:
            raise ValueError(f"Missing required application table(s): {', '.join(missing_tables)}")
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "BACKUP_VALIDATION_FAILED",
                "message": "The SQLite backup failed integrity validation.",
                "details": {"path": str(path), "error": str(exc)},
                "recommended_action": "Create a new backup or choose a different restore file.",
            },
        ) from exc
    finally:
        if conn is not None:
            conn.close()


def _manifest_path_for_backup(source: Path) -> Path:
    return source.with_suffix(".manifest.json")


def validate_backup_manifest(source: Path) -> dict:
    manifest_path = _manifest_path_for_backup(source)
    if not source.exists() or not manifest_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "BACKUP_NOT_FOUND",
                "message": "Backup database or manifest file was not found.",
                "details": {"backup_path": str(source), "manifest_path": str(manifest_path)},
                "recommended_action": "Choose a backup created by this app.",
            },
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "BACKUP_MANIFEST_INVALID",
                "message": "Backup manifest is not valid JSON.",
                "details": {"manifest_path": str(manifest_path), "error": str(exc)},
                "recommended_action": "Choose a different backup.",
            },
        ) from exc
    required = {"app_version", "schema_version", "created_at", "backup_type", "database_sha256"}
    missing = sorted(required - set(manifest))
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "BACKUP_MANIFEST_INCOMPLETE",
                "message": "Backup manifest is missing required fields.",
                "details": {"missing": missing, "manifest_path": str(manifest_path)},
                "recommended_action": "Choose a backup created by this version of the app.",
            },
        )
    if sha256_file(source) != manifest.get("database_sha256"):
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "BACKUP_HASH_MISMATCH",
                "message": "Backup hash does not match its manifest.",
                "details": {"backup_path": str(source)},
                "recommended_action": "Do not restore this backup; choose a valid backup.",
            },
        )
    return manifest


def _validate_schema_compatible(db: Session, manifest: dict[str, Any]) -> None:
    active_schema = _schema_version(db)
    backup_schema = manifest.get("schema_version")
    if backup_schema != active_schema:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "BACKUP_SCHEMA_MISMATCH",
                "message": "Backup schema version is not supported by this app version.",
                "details": {"active_schema_version": active_schema, "backup_schema_version": backup_schema},
                "recommended_action": "Restore using the app version that created the backup, or migrate the backup through a supported upgrade path.",
            },
        )


def _sidecar_paths(active_path: Path) -> list[Path]:
    return [active_path.with_name(active_path.name + "-wal"), active_path.with_name(active_path.name + "-shm")]


def _checkpoint_and_remove_sidecars(db: Session, active_path: Path) -> list[str]:
    warnings: list[str] = []
    try:
        db.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
    except Exception as exc:
        warnings.append(f"SQLite WAL checkpoint warning: {exc}")
    for sidecar in _sidecar_paths(active_path):
        if sidecar.exists():
            try:
                sidecar.unlink()
            except Exception as exc:
                warnings.append(f"Could not remove stale SQLite sidecar {sidecar.name}: {exc}")
    return warnings


def _insert_restore_audit_events(db_path: Path, events: list[dict[str, Any]]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for event in events:
            conn.execute(
                """
                INSERT INTO audit_log (
                    id, entity_type, entity_id, action, before_json, after_json, source, source_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    "backup_restore",
                    event["entity_id"],
                    event["action"],
                    json.dumps(event.get("before")) if event.get("before") is not None else None,
                    json.dumps(event.get("after")) if event.get("after") is not None else None,
                    "system",
                    event.get("source_id"),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def create_backup(db: Session, *, backup_type: str = "manual", notes: str | None = None) -> BackupManifest:
    source_path = _database_path(db)
    if not source_path.exists():
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "DATABASE_NOT_FOUND",
                "message": "The active SQLite database file does not exist.",
                "details": {"path": str(source_path)},
                "recommended_action": "Run migrations and restart the app.",
            },
        )
    target_dir = BACKUP_DIRS.get(backup_type, BACKUPS_DIR / backup_type)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = target_dir / f"finance_{backup_type}_{stamp}.sqlite3"
    manifest_path = target_dir / f"finance_{backup_type}_{stamp}.manifest.json"

    source = sqlite3.connect(source_path)
    target = sqlite3.connect(backup_path)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    validate_sqlite(backup_path)
    database_sha = sha256_file(backup_path)
    settings = get_settings()
    manifest = {
        "app_version": settings.app_version,
        "schema_version": _schema_version(db),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "backup_type": backup_type,
        "database_sha256": database_sha,
        "source_database_path": str(source_path),
        "notes": notes,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    record = BackupManifest(
        backup_type=backup_type,
        backup_path=str(backup_path),
        manifest_path=str(manifest_path),
        app_version=settings.app_version,
        schema_version=manifest["schema_version"],
        database_sha256=database_sha,
        notes=notes,
    )
    db.add(record)
    db.flush()
    return record


def list_backups(db: Session) -> list[BackupManifest]:
    from sqlalchemy import select

    return list(db.scalars(select(BackupManifest).order_by(BackupManifest.created_at.desc())))


def restore_backup(db: Session, backup_path: str) -> dict:
    source = Path(backup_path).resolve()
    active_path = _database_path(db)
    restore_id = str(uuid.uuid4())
    audit_events: list[dict[str, Any]] = [
        {"entity_id": restore_id, "action": "restore_request", "after": {"backup_path": str(source)}}
    ]
    set_restore_in_progress(True)
    record_audit(
        db,
        entity_type="backup_restore",
        entity_id=restore_id,
        action="restore_request",
        after={"backup_path": str(source)},
        source="system",
    )
    temp_restore = active_path.with_name(f"{active_path.name}.restore_tmp")
    try:
        if source == active_path:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": "RESTORE_SOURCE_IS_ACTIVE_DATABASE",
                    "message": "The active database file cannot be restored over itself.",
                    "details": {"backup_path": str(source)},
                    "recommended_action": "Choose a backup file from the backups directory.",
                },
            )
        manifest = validate_backup_manifest(source)
        _validate_schema_compatible(db, manifest)
        validate_sqlite(source)
        record_audit(
            db,
            entity_type="backup_restore",
            entity_id=restore_id,
            action="restore_validation",
            after={"valid": True, "backup_schema_version": manifest.get("schema_version")},
            source="system",
        )
        audit_events.append(
            {
                "entity_id": restore_id,
                "action": "restore_validation",
                "after": {"valid": True, "backup_schema_version": manifest.get("schema_version")},
            }
        )
        pre_restore = create_backup(db, backup_type="pre_restore", notes=f"Before restoring {source.name}")
        record_audit(
            db,
            entity_type="backup_restore",
            entity_id=restore_id,
            action="pre_restore_backup",
            after={"pre_restore_backup_id": pre_restore.id, "pre_restore_backup_path": pre_restore.backup_path},
            source="system",
        )
        audit_events.append(
            {
                "entity_id": restore_id,
                "action": "pre_restore_backup",
                "after": {"pre_restore_backup_id": pre_restore.id, "pre_restore_backup_path": pre_restore.backup_path},
            }
        )
        sidecar_warnings = _checkpoint_and_remove_sidecars(db, active_path)
        db.commit()
        temp_restore.write_bytes(source.read_bytes())
        validate_sqlite(temp_restore)
        bind = db.get_bind()
        db.close()
        bind.dispose()
        temp_restore.replace(active_path)
        validate_sqlite(active_path)
        result = {
            "restored": True,
            "restored_from": str(source),
            "backup_schema_version": manifest.get("schema_version"),
            "pre_restore_backup_id": pre_restore.id,
            "restart_required": True,
            "sqlite_sidecar_handling": "wal_checkpoint_truncate_and_remove_stale_sidecars",
            "warnings": sidecar_warnings,
            "message": "Restore completed safely. Restart the local app so all SQLite connections reopen on the restored database.",
        }
        audit_events.extend(
            [
                {"entity_id": restore_id, "action": "restore_complete", "after": result},
                {
                    "entity_id": restore_id,
                    "action": "restart_required",
                    "after": {"restart_required": True, "reason": "SQLite database file was replaced after validation."},
                },
            ]
        )
        _insert_restore_audit_events(active_path, audit_events)
        return result
    except HTTPException as exc:
        record_audit(
            db,
            entity_type="backup_restore",
            entity_id=restore_id,
            action="restore_validation_failed",
            after={"backup_path": str(source), "error": exc.detail},
            source="system",
        )
        db.commit()
        raise
    finally:
        set_restore_in_progress(False)
        if temp_restore.exists():
            temp_restore.unlink()
