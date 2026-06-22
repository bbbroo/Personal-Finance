from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import RecurringTransaction, Transaction
from app.services.audit_service import record_audit


def detect_recurring_transactions(db: Session) -> int:
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
        db.flush()
        record_audit(db, entity_type="recurring_transaction", entity_id=row.id, action="detect_create", after=row, source="system")
        db.flush()
        created += 1
    return created
