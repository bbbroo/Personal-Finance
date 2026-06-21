from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import BackupCreate, RestoreRequest
from app.services.backup_service import create_backup, list_backups, restore_backup
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/backups", tags=["backups"])


@router.get("")
def backups(db: Session = Depends(get_db)):
    return as_dict_list(list_backups(db))


@router.post("/create")
def create(payload: BackupCreate, db: Session = Depends(get_db)):
    row = create_backup(db, backup_type=payload.backup_type, notes=payload.notes)
    db.commit()
    return as_dict(row)


@router.post("/restore")
def restore(payload: RestoreRequest, db: Session = Depends(get_db)):
    return restore_backup(db, payload.backup_path)
