from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import RecurringTransaction
from app.repositories.common import get_or_404
from app.schemas.common import RecurringCreate
from app.services.audit_service import record_audit
from app.services.recurring_service import detect_recurring_transactions
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("")
def list_recurring(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(RecurringTransaction).order_by(RecurringTransaction.next_expected_date)))


@router.post("/detect")
def detect(db: Session = Depends(get_db)):
    created = detect_recurring_transactions(db)
    db.commit()
    return {"created_count": created}


@router.post("")
def create(payload: RecurringCreate, db: Session = Depends(get_db)):
    row = RecurringTransaction(**payload.model_dump())
    db.add(row)
    db.flush()
    record_audit(db, entity_type="recurring_transaction", entity_id=row.id, action="create", after=row)
    db.commit()
    return as_dict(row)


@router.patch("/{recurring_id}")
def update(recurring_id: str, payload: dict, db: Session = Depends(get_db)):
    row = get_or_404(db, RecurringTransaction, recurring_id)
    before = as_dict(row)
    for key, value in payload.items():
        if hasattr(row, key):
            setattr(row, key, value)
    db.flush()
    record_audit(db, entity_type="recurring_transaction", entity_id=row.id, action="update", before=before, after=row)
    db.commit()
    return as_dict(row)


@router.get("/calendar")
def calendar(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(RecurringTransaction).order_by(RecurringTransaction.next_expected_date)))
