from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import Account, AccountBalanceSnapshot
from app.schemas.common import AccountCreate, AccountUpdate, BalanceCreate
from app.services.audit_service import record_audit
from app.services.serialization import as_dict


def list_accounts(db: Session) -> list[Account]:
    return list(db.scalars(select(Account).order_by(Account.name)))


def create_account(db: Session, payload: AccountCreate) -> Account:
    account = Account(**payload.model_dump())
    db.add(account)
    db.flush()
    record_audit(db, entity_type="account", entity_id=account.id, action="create", after=account)
    return account


def update_account(db: Session, account: Account, payload: AccountUpdate) -> Account:
    before = as_dict(account)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    db.flush()
    record_audit(db, entity_type="account", entity_id=account.id, action="update", before=before, after=account)
    return account


def delete_account(db: Session, account: Account) -> None:
    if account.transactions or account.holdings or account.balances:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "ACCOUNT_HAS_FINANCIAL_HISTORY",
                "message": "Accounts with balances, transactions, or holdings are deactivated instead of deleted.",
                "details": {"account_id": account.id},
                "recommended_action": "Set the account inactive if you want to hide it.",
            },
        )
    before = as_dict(account)
    db.delete(account)
    record_audit(db, entity_type="account", entity_id=account.id, action="delete", before=before)


def add_balance(db: Session, account: Account, payload: BalanceCreate) -> AccountBalanceSnapshot:
    if payload.balance_cents is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "BALANCE_UNKNOWN",
                "message": "A missing balance cannot be saved as zero.",
                "details": {"account_id": account.id},
                "recommended_action": "Enter a known balance or leave the account without a snapshot.",
            },
        )
    snapshot = AccountBalanceSnapshot(
        account_id=account.id,
        snapshot_date=payload.snapshot_date,
        balance_cents=payload.balance_cents,
        balance_kind=payload.balance_kind,
        source_type=payload.source_type,
        confidence=payload.confidence,
        is_reconciled=payload.is_reconciled,
    )
    db.add(snapshot)
    db.flush()
    record_audit(
        db,
        entity_type="account_balance",
        entity_id=snapshot.id,
        action="create",
        after=snapshot,
        source=payload.source_type,
    )
    return snapshot
