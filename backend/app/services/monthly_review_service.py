from __future__ import annotations

from calendar import monthrange
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import normalized_hash
from app.models.domain import (
    AccountBalanceSnapshot,
    AccountStatement,
    BudgetCategoryPlan,
    BudgetPeriod,
    Category,
    DataQualityIssue,
    HoldingSnapshot,
    Liability,
    MonthlyReviewSnapshot,
    Price,
    ReconciliationRun,
    Transaction,
    TransactionSplit,
    utc_now,
)
from app.services.audit_service import record_audit
from app.services.report_service import calculate_net_worth, cash_flow, spending_by_category


def _bounds(yyyy_mm: str) -> tuple[date, date]:
    year, month = [int(part) for part in yyyy_mm.split("-")]
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def _row_fingerprint(label: str, row, fields: list[str]) -> str:
    values = [label, getattr(row, "id", None)]
    for field in fields:
        value = getattr(row, field, None)
        values.append(value.isoformat() if hasattr(value, "isoformat") else value)
    return ":".join(str(value) for value in values)


def _source_hash(db: Session, start: date, end: date) -> str:
    """Hash all persisted source data that can materially affect a finalized review."""
    parts: list[str] = []
    for txn in db.scalars(select(Transaction).where(Transaction.transaction_date >= start, Transaction.transaction_date <= end)):
        parts.append(
            _row_fingerprint(
                "transaction",
                txn,
                [
                    "account_id",
                    "transaction_date",
                    "amount_cents",
                    "category_id",
                    "transaction_type",
                    "transfer_status",
                    "is_hidden",
                    "is_split",
                    "updated_at",
                ],
            )
        )
    for split in db.scalars(select(TransactionSplit)):
        txn = db.get(Transaction, split.transaction_id)
        if txn and start <= txn.transaction_date <= end:
            parts.append(_row_fingerprint("transaction_split", split, ["transaction_id", "category_id", "amount_cents"]))
    for category in db.scalars(select(Category)):
        parts.append(_row_fingerprint("category", category, ["category_type", "budget_behavior", "is_active"]))
    for balance in db.scalars(select(AccountBalanceSnapshot).where(AccountBalanceSnapshot.snapshot_date <= end)):
        parts.append(
            _row_fingerprint(
                "balance",
                balance,
                ["account_id", "snapshot_date", "balance_cents", "balance_kind", "confidence", "is_reconciled", "updated_at"],
            )
        )
    for holding in db.scalars(select(HoldingSnapshot).where(HoldingSnapshot.snapshot_date <= end)):
        parts.append(
            _row_fingerprint(
                "holding",
                holding,
                [
                    "account_id",
                    "instrument_id",
                    "snapshot_date",
                    "quantity_decimal",
                    "price_decimal",
                    "market_value_cents",
                    "cost_basis_cents",
                    "cost_basis_quality",
                    "valuation_quality",
                    "confidence",
                    "is_current",
                ],
            )
        )
    for price in db.scalars(select(Price).where(Price.price_date <= end)):
        parts.append(_row_fingerprint("price", price, ["instrument_id", "price_date", "price_decimal", "status", "confidence"]))
    for period in db.scalars(select(BudgetPeriod).where(BudgetPeriod.start_date <= end, BudgetPeriod.end_date >= start)):
        parts.append(_row_fingerprint("budget_period", period, ["period_type", "start_date", "end_date", "status", "closed_at"]))
    for plan in db.scalars(select(BudgetCategoryPlan)):
        period = db.get(BudgetPeriod, plan.budget_period_id)
        if period and period.start_date <= end and period.end_date >= start:
            parts.append(_row_fingerprint("budget_plan", plan, ["budget_period_id", "category_id", "planned_cents", "rollover_enabled", "plan_type"]))
    for liability in db.scalars(select(Liability).where(Liability.status == "active")):
        parts.append(_row_fingerprint("liability", liability, ["account_id", "current_balance_cents", "minimum_payment_cents", "credit_limit_cents", "confidence", "updated_at"]))
    for statement in db.scalars(select(AccountStatement).where(AccountStatement.period_start <= end, AccountStatement.period_end >= start)):
        parts.append(_row_fingerprint("account_statement", statement, ["account_id", "period_start", "period_end", "status", "ending_balance_cents"]))
    for run in db.scalars(select(ReconciliationRun)):
        statement = db.get(AccountStatement, run.account_statement_id)
        if statement and statement.period_start <= end and statement.period_end >= start:
            parts.append(_row_fingerprint("reconciliation", run, ["account_statement_id", "difference_cents", "status", "run_at"]))
    for issue in db.scalars(select(DataQualityIssue).where(DataQualityIssue.status.in_(["open", "ignored"]))) :
        parts.append(_row_fingerprint("data_quality", issue, ["issue_type", "entity_type", "entity_id", "fingerprint", "status", "resolved_at"]))
    return normalized_hash(sorted(parts))


def build_review(db: Session, yyyy_mm: str) -> dict:
    start, end = _bounds(yyyy_mm)
    beginning = calculate_net_worth(db, start)
    ending = calculate_net_worth(db, end)
    flow = cash_flow(db, start, end)
    top_categories = spending_by_category(db, start, end)[:5]
    biggest = [
        {
            "id": txn.id,
            "date": txn.transaction_date.isoformat(),
            "merchant_name": txn.merchant_name,
            "amount_cents": txn.amount_cents,
        }
        for txn in db.scalars(
            select(Transaction)
            .where(Transaction.transaction_date >= start, Transaction.transaction_date <= end)
            .order_by(Transaction.amount_cents)
            .limit(5)
        )
    ]
    source_hash = _source_hash(db, start, end)
    finalized = db.scalars(select(MonthlyReviewSnapshot).where(MonthlyReviewSnapshot.review_month == yyyy_mm)).first()
    source_changed = bool(finalized and finalized.status == "finalized" and finalized.source_data_hash != source_hash)
    return {
        "review_month": yyyy_mm,
        "status": finalized.status if finalized else "draft",
        "starting_net_worth_cents": beginning["net_worth_cents"],
        "ending_net_worth_cents": ending["net_worth_cents"],
        "net_worth_change_cents": ending["net_worth_cents"] - beginning["net_worth_cents"],
        "income_cents": flow["income_cents"],
        "expenses_cents": flow["expenses_cents"],
        "savings_rate_decimal": flow["savings_rate_decimal"],
        "investment_value_change_cents": None,
        "top_spending_categories": top_categories,
        "biggest_transactions": biggest,
        "budget_variance": {},
        "data_quality_summary": {
            "net_worth_confidence": ending["confidence"],
            "warnings": ending["metadata"]["warnings"] + flow["warnings"],
        },
        "source_data_hash": source_hash,
        "source_changed_since_finalization": source_changed,
    }


def finalize_review(db: Session, yyyy_mm: str) -> MonthlyReviewSnapshot:
    review = build_review(db, yyyy_mm)
    snapshot = db.scalars(select(MonthlyReviewSnapshot).where(MonthlyReviewSnapshot.review_month == yyyy_mm)).first()
    if snapshot is None:
        snapshot = MonthlyReviewSnapshot(review_month=yyyy_mm)
        db.add(snapshot)
    snapshot.status = "finalized"
    snapshot.starting_net_worth_cents = review["starting_net_worth_cents"]
    snapshot.ending_net_worth_cents = review["ending_net_worth_cents"]
    snapshot.net_worth_change_cents = review["net_worth_change_cents"]
    snapshot.income_cents = review["income_cents"]
    snapshot.expenses_cents = review["expenses_cents"]
    snapshot.savings_rate_decimal = review["savings_rate_decimal"]
    snapshot.investment_value_change_cents = review["investment_value_change_cents"]
    snapshot.top_spending_categories_json = review["top_spending_categories"]
    snapshot.biggest_transactions_json = review["biggest_transactions"]
    snapshot.budget_variance_json = review["budget_variance"]
    snapshot.data_quality_summary_json = review["data_quality_summary"]
    snapshot.source_data_hash = review["source_data_hash"]
    snapshot.finalized_at = utc_now()
    db.flush()
    record_audit(db, entity_type="monthly_review", entity_id=snapshot.id, action="finalize", after=snapshot)
    return snapshot


def regenerate_review(db: Session, yyyy_mm: str) -> MonthlyReviewSnapshot:
    existing = db.scalars(select(MonthlyReviewSnapshot).where(MonthlyReviewSnapshot.review_month == yyyy_mm)).first()
    before = None if existing is None else {
        "id": existing.id,
        "review_month": existing.review_month,
        "status": existing.status,
        "source_data_hash": existing.source_data_hash,
    }
    snapshot = finalize_review(db, yyyy_mm)
    snapshot.status = "regenerated"
    record_audit(db, entity_type="monthly_review", entity_id=snapshot.id, action="regenerate", before=before, after=snapshot)
    return snapshot
