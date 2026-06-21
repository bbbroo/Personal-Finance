from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import Account, AccountStatement, DataQualityIssue, ReconciliationRun, Transaction, utc_now
from app.services.audit_service import record_audit


def _transaction_balance_effect(account: Account | None, amount_cents: int) -> int:
    if account and account.balance_sign_policy in {"liability_positive", "invert_imported"}:
        return -amount_cents
    return amount_cents


def run_reconciliation(db: Session, statement: AccountStatement, tolerance_cents: int = 0) -> ReconciliationRun:
    if statement.opening_balance_cents is None or statement.ending_balance_cents is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "RECONCILIATION_MISSING_BALANCE",
                "message": "Opening and ending balances are required for reconciliation.",
                "details": {"statement_id": statement.id},
                "recommended_action": "Enter both statement balances before running reconciliation.",
            },
        )
    account = db.get(Account, statement.account_id)
    txns = db.scalars(
        select(Transaction).where(
            Transaction.account_id == statement.account_id,
            Transaction.transaction_date >= statement.period_start,
            Transaction.transaction_date <= statement.period_end,
            Transaction.is_hidden.is_(False),
        )
    )
    calculated = statement.opening_balance_cents + sum(_transaction_balance_effect(account, txn.amount_cents) for txn in txns)
    difference = calculated - statement.ending_balance_cents
    status = "matched" if abs(difference) <= tolerance_cents else "mismatch"
    statement.status = "reconciled" if status == "matched" else "mismatch"
    run = ReconciliationRun(
        account_statement_id=statement.id,
        calculated_ending_balance_cents=calculated,
        difference_cents=difference,
        status=status,
        tolerance_cents=tolerance_cents,
    )
    db.add(run)
    if status == "mismatch":
        db.add(
            DataQualityIssue(
                severity="error",
                issue_type="unreconciled",
                entity_type="account_statement",
                entity_id=statement.id,
                title="Statement reconciliation mismatch",
                description=f"Calculated ending balance differs from statement by {difference} cents.",
                recommended_action="Review missing, duplicated, or incorrectly signed transactions.",
            )
        )
    record_audit(
        db,
        entity_type="reconciliation",
        entity_id=statement.id,
        action="reconcile",
        after={"status": status, "difference_cents": difference},
        source="manual",
    )
    db.flush()
    return run


def accept_difference(db: Session, run: ReconciliationRun) -> ReconciliationRun:
    run.status = "accepted_difference"
    statement = db.get(AccountStatement, run.account_statement_id)
    if statement:
        statement.status = "accepted_difference"
    record_audit(
        db,
        entity_type="reconciliation",
        entity_id=run.id,
        action="accept_difference",
        after={"difference_cents": run.difference_cents},
        source="manual",
    )
    db.flush()
    return run
