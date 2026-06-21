from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.security import normalized_hash
from app.models.domain import Transaction, TransactionSplit, utc_now
from app.schemas.common import TransactionCreate, TransactionUpdate
from app.services.audit_service import record_audit
from app.services.serialization import as_dict


def clean_merchant(description: str | None) -> str | None:
    if not description:
        return None
    return " ".join(description.replace("*", " ").replace("#", " ").split()).title()[:255]


def transaction_fingerprint(
    account_id: str, transaction_date: date | str, amount_cents: int, description: str | None
) -> str:
    merchant = clean_merchant(description) or ""
    return normalized_hash([account_id, transaction_date, amount_cents, merchant])


def create_transaction(db: Session, payload: TransactionCreate, *, source: str = "manual", source_id: str | None = None):
    fingerprint = transaction_fingerprint(
        payload.account_id,
        payload.transaction_date,
        payload.amount_cents,
        payload.merchant_name or payload.original_description,
    )
    txn = Transaction(
        account_id=payload.account_id,
        transaction_date=payload.transaction_date,
        posted_date=payload.posted_date,
        original_description=payload.original_description,
        merchant_name=payload.merchant_name or clean_merchant(payload.original_description),
        amount_cents=payload.amount_cents,
        category_id=payload.category_id,
        transaction_type=payload.transaction_type,
        transfer_status=payload.transfer_status,
        fingerprint=fingerprint,
        source_type=source,
        source_id=source_id,
        created_by_import_batch_id=source_id if source == "csv_import" else None,
        notes=payload.notes,
    )
    db.add(txn)
    db.flush()
    record_audit(
        db,
        entity_type="transaction",
        entity_id=txn.id,
        action="create",
        after=txn,
        source=source,
        source_id=source_id,
    )
    return txn


def update_transaction(db: Session, txn: Transaction, payload: TransactionUpdate, *, source: str = "manual"):
    before = as_dict(txn)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(txn, key, value)
    txn.updated_at = utc_now()
    if {"merchant_name", "transaction_type"} & set(updates):
        txn.fingerprint = transaction_fingerprint(
            txn.account_id, txn.transaction_date, txn.amount_cents, txn.merchant_name or txn.original_description
        )
    db.flush()
    record_audit(
        db,
        entity_type="transaction",
        entity_id=txn.id,
        action="update",
        before=before,
        after=txn,
        source=source,
    )
    return txn


def replace_splits(db: Session, txn: Transaction, splits: list[dict]):
    total = sum(int(split["amount_cents"]) for split in splits)
    if total != txn.amount_cents:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "SPLIT_TOTAL_MISMATCH",
                "message": "Split amounts must equal the parent transaction amount.",
                "details": {"parent_amount_cents": txn.amount_cents, "split_total_cents": total},
                "recommended_action": "Adjust split lines until they match the transaction total.",
            },
        )
    before = {"splits": [as_dict(split) for split in txn.splits], "is_split": txn.is_split}
    txn.splits.clear()
    for split in splits:
        txn.splits.append(
            TransactionSplit(
                category_id=split["category_id"],
                amount_cents=int(split["amount_cents"]),
                notes=split.get("notes"),
            )
        )
    txn.is_split = bool(splits)
    txn.updated_at = utc_now()
    db.flush()
    record_audit(
        db,
        entity_type="transaction",
        entity_id=txn.id,
        action="split",
        before=before,
        after={"splits": [as_dict(split) for split in txn.splits], "is_split": txn.is_split},
        source="manual",
    )
    return txn


def possible_duplicate_exists(db: Session, fingerprint: str) -> bool:
    return db.scalar(select(Transaction.id).where(Transaction.fingerprint == fingerprint).limit(1)) is not None


def similar_transactions(
    db: Session, *, account_id: str, transaction_date: date, amount_cents: int, merchant_name: str | None
) -> list[Transaction]:
    window_start = date.fromordinal(transaction_date.toordinal() - 2)
    window_end = date.fromordinal(transaction_date.toordinal() + 2)
    query = select(Transaction).where(
        and_(
            Transaction.account_id == account_id,
            Transaction.amount_cents == amount_cents,
            Transaction.transaction_date >= window_start,
            Transaction.transaction_date <= window_end,
        )
    )
    txns = list(db.scalars(query))
    if not merchant_name:
        return txns
    needle = merchant_name.lower()
    return [
        txn
        for txn in txns
        if needle in (txn.merchant_name or txn.original_description or "").lower()
        or (txn.merchant_name or txn.original_description or "").lower() in needle
    ]
