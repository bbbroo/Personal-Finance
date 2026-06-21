from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import RecurringTransaction, Transaction
from app.repositories.common import get_or_404
from app.schemas.common import RecurringCreate
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("")
def list_recurring(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(RecurringTransaction).order_by(RecurringTransaction.next_expected_date)))


@router.post("/detect")
def detect(db: Session = Depends(get_db)):
    created = 0
    merchants: dict[str, list[Transaction]] = {}
    for txn in db.scalars(select(Transaction).where(Transaction.is_hidden.is_(False))):
        key = txn.merchant_name or txn.original_description
        merchants.setdefault(key, []).append(txn)
    for merchant, txns in merchants.items():
        if len(txns) < 2:
            continue
        if db.scalars(select(RecurringTransaction).where(RecurringTransaction.merchant_name == merchant)).first():
            continue
        latest = max(txns, key=lambda txn: txn.transaction_date)
        row = RecurringTransaction(
            merchant_name=merchant,
            account_id=latest.account_id,
            category_id=latest.category_id,
            expected_amount_cents=latest.amount_cents,
            cadence="monthly",
            last_seen_date=latest.transaction_date,
            confidence="medium",
            detection_source="system_detected",
        )
        db.add(row)
        created += 1
    db.commit()
    return {"created_count": created}


@router.post("")
def create(payload: RecurringCreate, db: Session = Depends(get_db)):
    row = RecurringTransaction(**payload.model_dump())
    db.add(row)
    db.commit()
    return as_dict(row)


@router.patch("/{recurring_id}")
def update(recurring_id: str, payload: dict, db: Session = Depends(get_db)):
    row = get_or_404(db, RecurringTransaction, recurring_id)
    for key, value in payload.items():
        if hasattr(row, key):
            setattr(row, key, value)
    db.commit()
    return as_dict(row)


@router.get("/calendar")
def calendar(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(RecurringTransaction).order_by(RecurringTransaction.next_expected_date)))
