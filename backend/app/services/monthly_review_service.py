from __future__ import annotations

from calendar import monthrange
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import normalized_hash
from app.models.domain import MonthlyReviewSnapshot, Transaction, utc_now
from app.services.audit_service import record_audit
from app.services.report_service import calculate_net_worth, cash_flow, spending_by_category


def _bounds(yyyy_mm: str) -> tuple[date, date]:
    year, month = [int(part) for part in yyyy_mm.split("-")]
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def _source_hash(db: Session, start: date, end: date) -> str:
    txns = db.scalars(
        select(Transaction).where(Transaction.transaction_date >= start, Transaction.transaction_date <= end)
    )
    parts = [f"{txn.id}:{txn.updated_at.isoformat()}:{txn.amount_cents}" for txn in txns]
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
    snapshot = finalize_review(db, yyyy_mm)
    snapshot.status = "regenerated"
    record_audit(db, entity_type="monthly_review", entity_id=snapshot.id, action="regenerate", after=snapshot)
    return snapshot
