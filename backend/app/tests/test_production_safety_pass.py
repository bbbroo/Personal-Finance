from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.routes import budgets as budget_routes
from app.api.routes import data_quality as data_quality_routes
from app.api.routes import goals as goal_routes
from app.api.routes import liabilities as liability_routes
from app.api.routes import prices as price_routes
from app.api.routes import recurring as recurring_routes
from app.models.domain import (
    AccountBalanceSnapshot,
    AuditLog,
    BudgetCategoryPlan,
    BudgetPeriod,
    DataQualityIssue,
    Goal,
    HoldingSnapshot,
    Liability,
    LiabilityTermsHistory,
    Price,
    Transaction,
)
from app.schemas.common import (
    BudgetPeriodCreate,
    BudgetPlanCreate,
    DebtPaymentAllocationCreate,
    GoalCreate,
    HoldingCreate,
    LiabilityCreate,
    LiabilityTermsCreate,
    ManualPriceCreate,
    RecurringCreate,
    RolloverAdjust,
    SinkingFundCreate,
)
from app.services.backup_service import create_backup, restore_backup
from app.services.data_quality_service import recompute_data_quality
from app.services.holding_service import create_holding_snapshot
from app.services.monthly_review_service import build_review, finalize_review
from app.tests.factories import account, category, instrument, transaction
from app.core.security import sha256_file


def _patch_backup_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services import backup_service

    for key in list(backup_service.BACKUP_DIRS):
        monkeypatch.setitem(backup_service.BACKUP_DIRS, key, tmp_path / "backups" / key)


def _audit_actions(db, entity_type: str) -> list[str]:
    return list(db.scalars(select(AuditLog.action).where(AuditLog.entity_type == entity_type).order_by(AuditLog.created_at)))


def test_budget_goal_liability_recurring_and_data_quality_actions_are_audited(db):
    acct = account(db, "Checking")
    groceries = category(db, "Groceries", "expense")
    debt_acct = account(db, "Loan Account", account_type="liability", valuation_method="liability_balance")

    period = budget_routes.create_period(
        BudgetPeriodCreate(start_date=date(2026, 6, 1), end_date=date(2026, 6, 30)), db=db
    )
    budget_routes.update_period(period["id"], {"status": "draft"}, db=db)
    budget_routes.close(period["id"], db=db)
    plan = budget_routes.create_budget(
        BudgetPlanCreate(budget_period_id=period["id"], category_id=groceries.id, planned_cents=50000), db=db
    )
    budget_routes.update_budget(plan["id"], {"planned_cents": 60000}, db=db)
    budget_routes.adjust_rollover(
        RolloverAdjust(category_id=groceries.id, budget_period_id=period["id"], adjustment_cents=2500), db=db
    )
    fund = budget_routes.create_sinking_fund(SinkingFundCreate(name="Insurance", target_cents=120000), db=db)
    budget_routes.update_sinking_fund(fund["id"], {"current_balance_cents": 10000}, db=db)

    goal = goal_routes.create_goal(GoalCreate(name="Emergency Fund", goal_type="savings", target_cents=500000), db=db)
    goal_routes.update_goal(goal["id"], {"current_manual_cents": 10000}, db=db)
    link = goal_routes.add_link(goal["id"], {"account_id": acct.id, "allocation_percent": "100"}, db=db)
    goal_routes.delete_link(goal["id"], link["id"], db=db)

    liability = liability_routes.create_liability(
        LiabilityCreate(account_id=debt_acct.id, liability_type="personal_loan", current_balance_cents=100000, minimum_payment_cents=10000),
        db=db,
    )
    liability_routes.update_liability(liability["id"], {"minimum_payment_cents": 12000}, db=db)
    liability_routes.create_terms(
        liability["id"], LiabilityTermsCreate(effective_date=date(2026, 1, 1), apr_decimal="0.10", minimum_payment_cents=12000), db=db
    )
    payment = transaction(db, acct.id, -12000, date(2026, 6, 15), "Loan Payment", transaction_type="liability_payment")
    liability_routes.payment_allocation(
        DebtPaymentAllocationCreate(transaction_id=payment.id, liability_id=liability["id"], principal_cents=11000, interest_cents=1000, fee_cents=0, is_estimated=False, confidence="high"),
        db=db,
    )

    recurring = recurring_routes.create(RecurringCreate(merchant_name="Rent", account_id=acct.id, expected_amount_cents=-150000), db=db)
    recurring_routes.update(recurring["id"], {"status": "paused"}, db=db)

    issue = DataQualityIssue(
        severity="warning",
        issue_type="missing_data",
        entity_type="account",
        entity_id=acct.id,
        title="Manual issue",
        description="Test issue",
        recommended_action="Ignore for test",
    )
    db.add(issue)
    db.commit()
    data_quality_routes.ignore(issue.id, db=db)

    assert "create" in _audit_actions(db, "budget_period")
    assert "update" in _audit_actions(db, "budget_period")
    assert "close" in _audit_actions(db, "budget_period")
    assert "create" in _audit_actions(db, "budget_category_plan")
    assert "update" in _audit_actions(db, "budget_category_plan")
    assert "adjust" in _audit_actions(db, "rollover_ledger")
    assert "create" in _audit_actions(db, "sinking_fund")
    assert "update" in _audit_actions(db, "sinking_fund")
    assert "create" in _audit_actions(db, "goal")
    assert "update" in _audit_actions(db, "goal")
    assert "create" in _audit_actions(db, "goal_account_link")
    assert "delete" in _audit_actions(db, "goal_account_link")
    assert "create" in _audit_actions(db, "liability")
    assert "update" in _audit_actions(db, "liability")
    assert "create" in _audit_actions(db, "liability_terms")
    assert "create" in _audit_actions(db, "debt_payment_allocation")
    assert "create" in _audit_actions(db, "recurring_transaction")
    assert "update" in _audit_actions(db, "recurring_transaction")
    ignore_audit = db.scalar(select(AuditLog).where(AuditLog.entity_type == "data_quality_issue", AuditLog.action == "ignore"))
    assert ignore_audit is not None
    assert ignore_audit.before_json["status"] == "open"
    assert ignore_audit.after_json["status"] == "ignored"


def test_restore_rejects_schema_mismatch_hash_mismatch_and_integrity_failure(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    account(db, "Checking")
    manifest = create_backup(db, backup_type="manual", notes="valid")
    db.commit()
    backup_path = Path(manifest.backup_path)

    manifest_path = backup_path.with_suffix(".manifest.json")
    manifest_json = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_json["schema_version"] = "9999_future_schema"
    manifest_path.write_text(json.dumps(manifest_json), encoding="utf-8")
    with pytest.raises(HTTPException) as schema_exc:
        restore_backup(db, str(backup_path))
    assert schema_exc.value.detail["error_code"] == "BACKUP_SCHEMA_MISMATCH"

    manifest_json["schema_version"] = "unversioned"
    manifest_path.write_text(json.dumps(manifest_json), encoding="utf-8")
    backup_path.write_bytes(backup_path.read_bytes() + b"tamper")
    with pytest.raises(HTTPException) as hash_exc:
        restore_backup(db, str(backup_path))
    assert hash_exc.value.detail["error_code"] == "BACKUP_HASH_MISMATCH"

    corrupt = tmp_path / "corrupt.sqlite3"
    corrupt.write_bytes(b"not a sqlite database")
    corrupt_manifest = {
        "app_version": "1.0.0",
        "schema_version": "unversioned",
        "created_at": "2026-06-21T00:00:00Z",
        "backup_type": "manual",
        "database_sha256": sha256_file(corrupt),
    }
    corrupt.with_suffix(".manifest.json").write_text(json.dumps(corrupt_manifest), encoding="utf-8")
    with pytest.raises(HTTPException) as integrity_exc:
        restore_backup(db, str(corrupt))
    assert integrity_exc.value.detail["error_code"] == "BACKUP_VALIDATION_FAILED"
    assert db.scalar(select(AuditLog).where(AuditLog.entity_type == "backup_restore", AuditLog.action == "restore_validation_failed")) is not None


def test_restore_success_creates_pre_restore_backup_and_audit_entries(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    active_path = Path(db.get_bind().url.database)
    account(db, "Before Backup")
    db.commit()
    manifest = create_backup(db, backup_type="manual", notes="restore source")
    db.commit()
    account(db, "After Backup")
    db.commit()

    result = restore_backup(db, manifest.backup_path)

    assert result["restored"] is True
    assert result["restart_required"] is True
    assert result["pre_restore_backup_id"] is not None
    assert result["sqlite_sidecar_handling"] == "wal_checkpoint_truncate_and_remove_stale_sidecars"
    with sqlite3.connect(active_path) as conn:
        names = [row[0] for row in conn.execute("SELECT name FROM accounts ORDER BY name").fetchall()]
        actions = [row[0] for row in conn.execute("SELECT action FROM audit_log WHERE entity_type='backup_restore'").fetchall()]
    assert "Before Backup" in names
    assert "After Backup" not in names
    assert {"restore_request", "restore_validation", "pre_restore_backup", "restore_complete", "restart_required"}.issubset(set(actions))


def test_debt_payoff_uses_effective_terms_allocations_promo_apr_and_extra_payment(db):
    acct = account(db, "Debt", account_type="liability", valuation_method="liability_balance")
    pay_acct = account(db, "Checking")
    liability = Liability(account_id=acct.id, liability_type="credit_card", current_balance_cents=100000, minimum_payment_cents=5000)
    db.add(liability)
    db.flush()
    old = LiabilityTermsHistory(liability_id=liability.id, effective_date=date.today() - timedelta(days=400), apr_decimal="0.30", minimum_payment_cents=4000)
    current = LiabilityTermsHistory(
        liability_id=liability.id,
        effective_date=date.today() - timedelta(days=10),
        apr_decimal="0.20",
        minimum_payment_cents=6000,
        promo_apr_decimal="0.05",
        promo_end_date=date.today() + timedelta(days=30),
    )
    future = LiabilityTermsHistory(liability_id=liability.id, effective_date=date.today() + timedelta(days=10), apr_decimal="0.99", minimum_payment_cents=99999)
    payment = transaction(db, pay_acct.id, -6000, date.today(), "Debt Payment")
    db.add_all([old, current, future])
    db.flush()
    liability_routes.payment_allocation(
        DebtPaymentAllocationCreate(transaction_id=payment.id, liability_id=liability.id, principal_cents=5000, interest_cents=1000, fee_cents=0, is_estimated=False, confidence="high"),
        db=db,
    )

    plan = liability_routes.payoff_plan(strategy="avalanche", extra_payment_cents=1000, db=db)
    row = plan["rows"][0]
    assert plan["estimated"] is True
    assert row["effective_terms_id"] == current.id
    assert row["apr_decimal"] == "0.05"
    assert row["apr_source"] == "promo"
    assert row["minimum_payment_cents"] == 6000
    assert row["extra_payment_cents"] == 1000
    assert row["total_payment_cents"] == 7000
    assert row["allocation_summary"]["principal_cents"] == 5000
    assert row["allocation_summary"]["interest_cents"] == 1000


def test_debt_payoff_flags_non_amortizing_and_data_quality_missing_terms(db):
    acct = account(db, "Bad Debt", account_type="liability", valuation_method="liability_balance")
    liability = Liability(account_id=acct.id, liability_type="personal_loan", current_balance_cents=100000, minimum_payment_cents=100)
    db.add(liability)
    db.flush()
    db.add(LiabilityTermsHistory(liability_id=liability.id, effective_date=date.today() - timedelta(days=1), apr_decimal="0.50", minimum_payment_cents=100))
    db.flush()

    plan = liability_routes.payoff_plan(db=db)
    assert any("Payment does not amortize balance" in warning for warning in plan["rows"][0]["warnings"])

    missing_acct = account(db, "Missing Debt", account_type="liability", valuation_method="liability_balance")
    missing = Liability(account_id=missing_acct.id, liability_type="personal_loan", current_balance_cents=0, minimum_payment_cents=None)
    db.add(missing)
    db.flush()
    issues = recompute_data_quality(db)
    issue_titles = {issue.title for issue in issues if issue.entity_id == missing.id}
    assert "Liability is missing APR" in issue_titles
    assert "Liability is missing payment terms" in issue_titles
    assert "Liability is missing a positive balance" in issue_titles
    assert "Liability is missing payment allocation history" in issue_titles


def test_price_and_holding_confidence_warnings(db):
    brokerage = account(db, "Brokerage", account_type="brokerage", valuation_method="holdings_sum")
    stale_instrument = instrument(db, "STALE", "us_stock")
    missing_instrument = instrument(db, "MISSING", "us_stock")
    db.add(Price(instrument_id=stale_instrument.id, price_date=date.today() - timedelta(days=10), price_decimal="10", provider="manual", status="current"))
    holding = create_holding_snapshot(
        db,
        HoldingCreate(
            account_id=brokerage.id,
            instrument_id=stale_instrument.id,
            snapshot_date=date.today(),
            quantity_decimal="2",
            price_decimal="10",
            cost_basis_cents=1500,
            cost_basis_source="coinbase_api_inferred",
            cost_basis_quality="estimated",
        ),
    )
    missing_basis_holding = create_holding_snapshot(
        db,
        HoldingCreate(
            account_id=brokerage.id,
            instrument_id=missing_instrument.id,
            snapshot_date=date.today(),
            quantity_decimal="1",
            price_decimal=None,
            cost_basis_cents=None,
            cost_basis_quality="missing",
        ),
    )

    manual_result = price_routes.manual_price(
        ManualPriceCreate(instrument_id=stale_instrument.id, price_date=date.today(), price_decimal="12"), db=db
    )
    issues = recompute_data_quality(db)
    issue_titles = {issue.title for issue in issues}

    assert manual_result["affected_current_holding_count"] == 1
    assert "Existing holding snapshots were not mutated" in manual_result["holding_valuation_warning"]
    assert holding.confidence == "low"
    assert missing_basis_holding.confidence == "unknown"
    assert "MISSING is missing a price" in issue_titles


def test_monthly_review_source_changed_for_transaction_balance_holding_and_budget_edits(db):
    acct = account(db, "Checking")
    brokerage = account(db, "Brokerage", account_type="brokerage", valuation_method="holdings_sum")
    cat = category(db, "Groceries", "expense")
    txn = transaction(db, acct.id, -1000, date(2026, 6, 10), "Groceries", category_id=cat.id)
    balance = AccountBalanceSnapshot(account_id=acct.id, snapshot_date=date(2026, 6, 30), balance_cents=100000, balance_kind="manual", source_type="manual", confidence="medium", is_reconciled=False)
    period = BudgetPeriod(period_type="monthly", start_date=date(2026, 6, 1), end_date=date(2026, 6, 30), status="active")
    db.add_all([balance, period])
    db.flush()
    plan = BudgetCategoryPlan(budget_period_id=period.id, category_id=cat.id, planned_cents=50000)
    db.add(plan)
    vti = instrument(db, "VTI", "us_stock")
    holding = create_holding_snapshot(
        db,
        HoldingCreate(account_id=brokerage.id, instrument_id=vti.id, snapshot_date=date(2026, 6, 30), quantity_decimal="1", price_decimal="100", cost_basis_cents=9000),
    )
    db.commit()
    snapshot = finalize_review(db, "2026-06")
    finalized_hash = snapshot.source_data_hash
    assert build_review(db, "2026-06")["source_changed_since_finalization"] is False

    txn.amount_cents = -2000
    db.flush()
    assert build_review(db, "2026-06")["source_changed_since_finalization"] is True
    txn.amount_cents = -1000
    db.flush()
    snapshot.source_data_hash = build_review(db, "2026-06")["source_data_hash"]
    db.flush()

    balance.balance_cents = 110000
    db.flush()
    assert build_review(db, "2026-06")["source_changed_since_finalization"] is True
    balance.balance_cents = 100000
    db.flush()
    snapshot.source_data_hash = build_review(db, "2026-06")["source_data_hash"]
    db.flush()

    holding.market_value_cents = 12000
    db.flush()
    assert build_review(db, "2026-06")["source_changed_since_finalization"] is True
    holding.market_value_cents = 10000
    db.flush()
    snapshot.source_data_hash = build_review(db, "2026-06")["source_data_hash"]
    db.flush()

    plan.planned_cents = 70000
    db.flush()
    assert build_review(db, "2026-06")["source_changed_since_finalization"] is True
    assert finalized_hash != build_review(db, "2026-06")["source_data_hash"]
