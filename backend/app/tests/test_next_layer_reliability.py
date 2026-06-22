from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.models.domain import (
    AccountBalanceSnapshot,
    AuditLog,
    DataQualityIssue,
    DebtPaymentAllocation,
    Liability,
    LiabilityTermsHistory,
    Price,
)
from app.services.debt_payoff_service import build_payoff_plan
from app.services.recurring_service import detect_recurring_transactions
from app.services.trust_service import build_trust_checklist
from app.tests.factories import account, instrument, transaction


def _liability_with_terms(db, name: str, balance: int, apr: str, minimum: int):
    acct = account(db, name, account_type="liability", valuation_method="liability_balance")
    liability = Liability(account_id=acct.id, liability_type="credit_card", current_balance_cents=balance, minimum_payment_cents=minimum)
    db.add(liability)
    db.flush()
    db.add(
        LiabilityTermsHistory(
            liability_id=liability.id,
            effective_date=date.today() - timedelta(days=30),
            apr_decimal=apr,
            minimum_payment_cents=minimum,
        )
    )
    payment_acct = account(db, f"{name} payment account")
    payment = transaction(db, payment_acct.id, -minimum, date.today(), f"{name} payment")
    db.add(
        DebtPaymentAllocation(
            transaction_id=payment.id,
            liability_id=liability.id,
            principal_cents=minimum - 100,
            interest_cents=100,
            fee_cents=0,
            is_estimated=False,
            confidence="high",
        )
    )
    db.flush()
    return liability


def test_debt_payoff_service_returns_comparison_order_summary_and_confidence(db):
    high_apr = _liability_with_terms(db, "High APR", 200000, "0.29", 20000)
    small_balance = _liability_with_terms(db, "Small Balance", 50000, "0.05", 5000)

    plan = build_payoff_plan(db, strategy="avalanche", extra_payment_cents=2500)

    assert plan["estimated"] is True
    assert set(plan["comparison"]) == {"avalanche", "snowball"}
    assert plan["comparison"]["avalanche"]["payoff_order"][0] == high_apr.id
    assert plan["comparison"]["snowball"]["payoff_order"][0] == small_balance.id
    assert plan["summary"]["total_estimated_interest_cents"] is not None
    assert plan["summary"]["total_projected_months"] is not None
    assert plan["rows"][0]["extra_payment_cents"] == 2500
    assert plan["rows"][0]["confidence_explanation"]


def test_recurring_detection_service_creates_audited_system_rows(db):
    checking = account(db, "Checking")
    transaction(db, checking.id, -1500, date(2026, 5, 1), "Netflix")
    transaction(db, checking.id, -1500, date(2026, 6, 1), "Netflix")

    created = detect_recurring_transactions(db)

    assert created == 1
    audit = db.scalar(select(AuditLog).where(AuditLog.entity_type == "recurring_transaction", AuditLog.action == "detect_create"))
    assert audit is not None
    assert audit.source == "system"


def test_trust_checklist_surfaces_backup_quality_price_reconciliation_and_confidence_statuses(db):
    checking = account(db, "Checking")
    db.add(
        AccountBalanceSnapshot(
            account_id=checking.id,
            snapshot_date=date.today(),
            balance_cents=100000,
            balance_kind="manual",
            source_type="manual",
            confidence="medium",
            is_reconciled=False,
        )
    )
    db.add(
        DataQualityIssue(
            severity="warning",
            issue_type="missing_cost_basis",
            entity_type="holding",
            entity_id="h1",
            title="Missing cost basis",
            description="Cost basis is missing.",
            recommended_action="Add cost basis.",
        )
    )
    vti = instrument(db, "VTI")
    db.add(Price(instrument_id=vti.id, price_date=date.today() - timedelta(days=10), price_decimal="100", provider="manual", status="stale"))
    liability_acct = account(db, "Loan", account_type="liability", valuation_method="liability_balance")
    db.add(Liability(account_id=liability_acct.id, liability_type="loan", current_balance_cents=50000, minimum_payment_cents=None))
    db.flush()

    checklist = build_trust_checklist(db)

    assert checklist["overall_status"] == "warning"
    assert checklist["checks"]["last_successful_backup"]["status"] == "missing"
    assert checklist["checks"]["data_quality"]["open_issue_count"] == 1
    assert checklist["checks"]["prices"]["stale_price_count"] == 1
    assert checklist["checks"]["reconciliation"]["unreconciled_account_count"] == 1
    assert checklist["checks"]["debt_payoff"]["confidence"] == "low"
