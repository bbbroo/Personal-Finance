from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.maintenance import set_restore_in_progress
from app.core.paths import BACKUPS_DIR, DAILY_BACKUPS_DIR, PRE_IMPORT_BACKUPS_DIR, PRE_RESTORE_BACKUPS_DIR
from app.core.security import sha256_file
from app.models.domain import BackupManifest


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
    try:
        with sqlite3.connect(path) as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result is None or result[0] != "ok":
                raise ValueError(result[0] if result else "No integrity result")
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

    with sqlite3.connect(source_path) as source:
        with sqlite3.connect(backup_path) as target:
            source.backup(target)
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
    validate_sqlite(source)
    set_restore_in_progress(True)
    temp_restore = active_path.with_name(f"{active_path.name}.restore_tmp")
    try:
        pre_restore = create_backup(db, backup_type="pre_restore", notes=f"Before restoring {source.name}")
        db.commit()
        temp_restore.write_bytes(source.read_bytes())
        validate_sqlite(temp_restore)
        bind = db.get_bind()
        db.close()
        bind.dispose()
        temp_restore.replace(active_path)
        validate_sqlite(active_path)
        return {
            "restored": True,
            "restored_from": str(source),
            "backup_schema_version": manifest.get("schema_version"),
            "pre_restore_backup_id": pre_restore.id,
            "restart_required": True,
            "message": "Restore completed safely. Restart the local app so all SQLite connections reopen on the restored database.",
        }
    finally:
        set_restore_in_progress(False)
        if temp_restore.exists():
            temp_restore.unlink()
