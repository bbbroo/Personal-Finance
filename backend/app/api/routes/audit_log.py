from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import AuditLog
from app.services.serialization import as_dict_list

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("")
def audit_log(limit: int = 200, db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)))
