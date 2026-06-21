from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import Transaction
from app.repositories.common import get_or_404
from app.schemas.common import SplitCreate, TransactionCreate, TransactionUpdate
from app.services.serialization import as_dict, as_dict_list
from app.services.transaction_service import create_transaction, replace_splits, update_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("")
def list_transactions(
    start_date: date | None = None,
    end_date: date | None = None,
    account_id: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(Transaction).order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
    if start_date:
        query = query.where(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.where(Transaction.transaction_date <= end_date)
    if account_id:
        query = query.where(Transaction.account_id == account_id)
    return as_dict_list(db.scalars(query))


@router.post("")
def create(payload: TransactionCreate, db: Session = Depends(get_db)):
    txn = create_transaction(db, payload)
    db.commit()
    return as_dict(txn)


@router.get("/{transaction_id}")
def get(transaction_id: str, db: Session = Depends(get_db)):
    return as_dict(get_or_404(db, Transaction, transaction_id))


@router.patch("/{transaction_id}")
def update(transaction_id: str, payload: TransactionUpdate, db: Session = Depends(get_db)):
    txn = update_transaction(db, get_or_404(db, Transaction, transaction_id), payload)
    db.commit()
    return as_dict(txn)


@router.delete("/{transaction_id}")
def delete(transaction_id: str, db: Session = Depends(get_db)):
    txn = get_or_404(db, Transaction, transaction_id)
    update_transaction(db, txn, TransactionUpdate(is_hidden=True, review_status="ignored"))
    db.commit()
    return {"hidden": True}


@router.post("/{transaction_id}/split")
def split(transaction_id: str, payload: SplitCreate, db: Session = Depends(get_db)):
    txn = replace_splits(db, get_or_404(db, Transaction, transaction_id), payload.splits)
    db.commit()
    return as_dict(txn)


@router.post("/{transaction_id}/mark-reviewed")
def mark_reviewed(transaction_id: str, db: Session = Depends(get_db)):
    txn = update_transaction(db, get_or_404(db, Transaction, transaction_id), TransactionUpdate(review_status="reviewed"))
    db.commit()
    return as_dict(txn)


@router.post("/{transaction_id}/hide")
def hide(transaction_id: str, db: Session = Depends(get_db)):
    txn = update_transaction(db, get_or_404(db, Transaction, transaction_id), TransactionUpdate(is_hidden=True))
    db.commit()
    return as_dict(txn)


@router.post("/{transaction_id}/unhide")
def unhide(transaction_id: str, db: Session = Depends(get_db)):
    txn = update_transaction(db, get_or_404(db, Transaction, transaction_id), TransactionUpdate(is_hidden=False))
    db.commit()
    return as_dict(txn)
