from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    BudgetCategoryPlan,
    BudgetPeriod,
    Category,
    RolloverLedger,
    SinkingFund,
    Transaction,
)


def _budget_signed_amount(amount_cents: int, category: Category | None) -> int:
    if category and category.category_type == "income":
        return amount_cents
    if category and category.category_type == "expense":
        return -amount_cents
    return abs(amount_cents) if amount_cents < 0 else amount_cents


def category_actual_cents(db: Session, category_id: str, period: BudgetPeriod) -> int:
    actual = 0
    target_category = db.get(Category, category_id)
    txns = db.scalars(
        select(Transaction).where(
            Transaction.transaction_date >= period.start_date,
            Transaction.transaction_date <= period.end_date,
            Transaction.is_hidden.is_(False),
            Transaction.transfer_status != "confirmed_transfer",
        )
    )
    for txn in txns:
        if txn.is_split and txn.splits:
            for split in txn.splits:
                if split.category_id == category_id:
                    actual += _budget_signed_amount(split.amount_cents, target_category)
        elif txn.category_id == category_id:
            actual += _budget_signed_amount(txn.amount_cents, target_category)
    return actual


def calculate_budget_plan(db: Session, plan: BudgetCategoryPlan) -> dict:
    period = db.get(BudgetPeriod, plan.budget_period_id)
    category = db.get(Category, plan.category_id)
    actual = category_actual_cents(db, plan.category_id, period)
    ledger = db.scalars(
        select(RolloverLedger).where(
            RolloverLedger.category_id == plan.category_id,
            RolloverLedger.budget_period_id == plan.budget_period_id,
        )
    ).first()
    starting = ledger.starting_rollover_cents if ledger else 0
    adjustment = ledger.adjustment_cents if ledger else 0
    available = plan.planned_cents + starting + adjustment
    if category and category.category_type == "income":
        remaining = actual - available
    else:
        remaining = available - actual
    ending = remaining if plan.rollover_enabled else 0
    return {
        "plan_id": plan.id,
        "category_id": plan.category_id,
        "category_name": category.name if category else "Unknown",
        "period_id": plan.budget_period_id,
        "planned_cents": plan.planned_cents,
        "starting_rollover_cents": starting,
        "adjustment_cents": adjustment,
        "available_cents": available,
        "actual_cents": actual,
        "remaining_cents": remaining,
        "ending_rollover_cents": ending,
        "rollover_enabled": plan.rollover_enabled,
        "confidence": "high",
    }


def budget_summary(db: Session) -> list[dict]:
    plans = list(db.scalars(select(BudgetCategoryPlan)))
    return [calculate_budget_plan(db, plan) for plan in plans]


def close_period(db: Session, period: BudgetPeriod) -> BudgetPeriod:
    plans = list(db.scalars(select(BudgetCategoryPlan).where(BudgetCategoryPlan.budget_period_id == period.id)))
    for plan in plans:
        summary = calculate_budget_plan(db, plan)
        ledger = db.scalars(
            select(RolloverLedger).where(
                RolloverLedger.category_id == plan.category_id,
                RolloverLedger.budget_period_id == plan.budget_period_id,
            )
        ).first()
        if ledger is None:
            ledger = RolloverLedger(category_id=plan.category_id, budget_period_id=plan.budget_period_id)
            db.add(ledger)
        ledger.budgeted_cents = plan.planned_cents
        ledger.actual_cents = summary["actual_cents"]
        ledger.ending_rollover_cents = summary["ending_rollover_cents"]
        from app.models.domain import utc_now

        ledger.locked_at = utc_now()
    period.status = "closed"
    from app.models.domain import utc_now

    period.closed_at = utc_now()
    db.flush()
    return period


def sinking_fund_summary(fund: SinkingFund) -> dict:
    balance = fund.current_balance_cents
    confidence = "unknown" if balance is None else "medium"
    remaining = None if balance is None else max(fund.target_cents - balance, 0)
    return {
        "id": fund.id,
        "name": fund.name,
        "target_cents": fund.target_cents,
        "current_balance_cents": balance,
        "remaining_cents": remaining,
        "monthly_set_aside_cents": fund.monthly_set_aside_cents,
        "status": fund.status,
        "confidence": confidence,
    }
