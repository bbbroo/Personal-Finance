from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import Account, AccountBalanceSnapshot
from app.repositories.common import get_or_404
from app.schemas.common import AccountCreate, AccountUpdate, BalanceCreate
from app.services import account_service
from app.services.report_service import calculate_net_worth
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts(db: Session = Depends(get_db)):
    return as_dict_list(account_service.list_accounts(db))


@router.post("")
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    account = account_service.create_account(db, payload)
    db.commit()
    return as_dict(account)


@router.get("/{account_id}")
def get_account(account_id: str, db: Session = Depends(get_db)):
    return as_dict(get_or_404(db, Account, account_id))


@router.patch("/{account_id}")
def update_account(account_id: str, payload: AccountUpdate, db: Session = Depends(get_db)):
    account = account_service.update_account(db, get_or_404(db, Account, account_id), payload)
    db.commit()
    return as_dict(account)


@router.delete("/{account_id}")
def delete_account(account_id: str, db: Session = Depends(get_db)):
    account_service.delete_account(db, get_or_404(db, Account, account_id))
    db.commit()
    return {"deleted": True}


@router.get("/{account_id}/balances")
def balances(account_id: str, db: Session = Depends(get_db)):
    get_or_404(db, Account, account_id)
    rows = db.scalars(
        select(AccountBalanceSnapshot)
        .where(AccountBalanceSnapshot.account_id == account_id)
        .order_by(AccountBalanceSnapshot.snapshot_date.desc())
    )
    return as_dict_list(rows)


@router.post("/{account_id}/balances")
def add_balance(account_id: str, payload: BalanceCreate, db: Session = Depends(get_db)):
    snapshot = account_service.add_balance(db, get_or_404(db, Account, account_id), payload)
    db.commit()
    return as_dict(snapshot)


@router.get("/{account_id}/valuation")
def account_valuation(account_id: str, db: Session = Depends(get_db)):
    get_or_404(db, Account, account_id)
    report = calculate_net_worth(db)
    account = next((row for row in report["accounts"] if row["account_id"] == account_id), None)
    return account or {"account_id": account_id, "value_cents": None, "confidence": "unknown", "warnings": ["Excluded or missing"]}
