from __future__ import annotations

from datetime import date

from app.models.domain import AccountStatement, BudgetCategoryPlan, BudgetPeriod, RolloverLedger
from app.services.budget_service import calculate_budget_plan
from app.services.reconciliation_service import run_reconciliation
from app.tests.factories import account, category, transaction


def test_reconciliation_matched_and_mismatch(db):
    acct = account(db)
    transaction(db, acct.id, -2000, date(2026, 6, 5), "Groceries")
    matched = AccountStatement(
        account_id=acct.id,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        opening_balance_cents=10000,
        ending_balance_cents=8000,
    )
    db.add(matched)
    db.flush()
    run = run_reconciliation(db, matched)
    assert run.status == "matched"
    mismatch = AccountStatement(
        account_id=acct.id,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        opening_balance_cents=10000,
        ending_balance_cents=7000,
    )
    db.add(mismatch)
    db.flush()
    run = run_reconciliation(db, mismatch)
    assert run.status == "mismatch"
    assert run.difference_cents == 1000


def test_budget_rollover_calculation(db):
    acct = account(db)
    cat = category(db, "Groceries", "expense")
    period = BudgetPeriod(period_type="monthly", start_date=date(2026, 6, 1), end_date=date(2026, 6, 30))
    db.add(period)
    db.flush()
    plan = BudgetCategoryPlan(
        budget_period_id=period.id,
        category_id=cat.id,
        planned_cents=10000,
        rollover_enabled=True,
        plan_type="flexible",
    )
    db.add(plan)
    db.add(
        RolloverLedger(
            category_id=cat.id,
            budget_period_id=period.id,
            starting_rollover_cents=1000,
            budgeted_cents=10000,
            actual_cents=0,
            adjustment_cents=0,
            ending_rollover_cents=0,
        )
    )
    transaction(db, acct.id, -2000, date(2026, 6, 3), "Groceries", category_id=cat.id)
    db.flush()
    summary = calculate_budget_plan(db, plan)
    assert summary["available_cents"] == 11000
    assert summary["actual_cents"] == 2000
    assert summary["ending_rollover_cents"] == 9000
