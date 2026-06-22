from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core.security import sha256_file
from app.services.backup_service import create_backup, restore_backup
from app.tests.factories import account


def _patch_backup_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services import backup_service

    for key in list(backup_service.BACKUP_DIRS):
        monkeypatch.setitem(backup_service.BACKUP_DIRS, key, tmp_path / "backups" / key)


def test_restore_rejects_missing_manifest(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    account(db, "Checking")
    manifest = create_backup(db, backup_type="manual", notes="valid")
    db.commit()
    backup_path = Path(manifest.backup_path)
    backup_path.with_suffix(".manifest.json").unlink()

    with pytest.raises(HTTPException) as exc:
        restore_backup(db, str(backup_path))

    assert exc.value.status_code == 404
    assert exc.value.detail["error_code"] == "BACKUP_NOT_FOUND"


def test_restore_rejects_invalid_manifest_json(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    account(db, "Checking")
    manifest = create_backup(db, backup_type="manual", notes="valid")
    db.commit()
    backup_path = Path(manifest.backup_path)
    backup_path.with_suffix(".manifest.json").write_text("{not valid json", encoding="utf-8")

    with pytest.raises(HTTPException) as exc:
        restore_backup(db, str(backup_path))

    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "BACKUP_MANIFEST_INVALID"


def test_restore_rejects_hash_mismatch(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    account(db, "Checking")
    manifest = create_backup(db, backup_type="manual", notes="valid")
    db.commit()
    backup_path = Path(manifest.backup_path)
    manifest_path = backup_path.with_suffix(".manifest.json")
    manifest_json = json.loads(manifest_path.read_text(encoding="utf-8"))
    backup_path.write_bytes(backup_path.read_bytes() + b"tamper")
    manifest_json["schema_version"] = "unversioned"
    manifest_path.write_text(json.dumps(manifest_json), encoding="utf-8")

    with pytest.raises(HTTPException) as exc:
        restore_backup(db, str(backup_path))

    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "BACKUP_HASH_MISMATCH"


def test_restore_rejects_corrupt_sqlite_file(db, tmp_path):
    corrupt = tmp_path / "corrupt.sqlite3"
    corrupt.write_bytes(b"not a sqlite database")
    corrupt.with_suffix(".manifest.json").write_text(
        json.dumps(
            {
                "app_version": "1.0.0",
                "schema_version": "unversioned",
                "created_at": "2026-06-21T00:00:00Z",
                "backup_type": "manual",
                "database_sha256": sha256_file(corrupt),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(HTTPException) as exc:
        restore_backup(db, str(corrupt))

    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "BACKUP_VALIDATION_FAILED"


def test_restore_rejects_valid_sqlite_with_missing_app_schema(db, tmp_path):
    incomplete = tmp_path / "incomplete.sqlite3"
    with sqlite3.connect(incomplete) as conn:
        conn.execute("CREATE TABLE example (id INTEGER PRIMARY KEY)")
    incomplete.with_suffix(".manifest.json").write_text(
        json.dumps(
            {
                "app_version": "1.0.0",
                "schema_version": "unversioned",
                "created_at": "2026-06-21T00:00:00Z",
                "backup_type": "manual",
                "database_sha256": sha256_file(incomplete),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(HTTPException) as exc:
        restore_backup(db, str(incomplete))

    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "BACKUP_VALIDATION_FAILED"
