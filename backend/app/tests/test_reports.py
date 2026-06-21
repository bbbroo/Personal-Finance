from __future__ import annotations

from datetime import date, timedelta

from app.models.domain import AccountBalanceSnapshot, HoldingSnapshot
from app.services.data_quality_service import recompute_data_quality
from app.services.report_service import asset_allocation, calculate_net_worth, cash_flow
from app.tests.factories import account, category, instrument, transaction


def test_net_worth_prevents_holding_account_double_count(db):
    brokerage = account(db, "Brokerage", account_type="brokerage", valuation_method="holdings_plus_cash")
    vti = instrument(db)
    db.add_all(
        [
            AccountBalanceSnapshot(
                account_id=brokerage.id,
                snapshot_date=date.today(),
                balance_cents=999999,
                balance_kind="current",
                source_type="manual",
                confidence="high",
            ),
            AccountBalanceSnapshot(
                account_id=brokerage.id,
                snapshot_date=date.today(),
                balance_cents=20000,
                balance_kind="cash_position",
                source_type="manual",
                confidence="high",
            ),
            HoldingSnapshot(
                account_id=brokerage.id,
                instrument_id=vti.id,
                snapshot_date=date.today(),
                quantity_decimal="10",
                price_decimal="50",
                market_value_cents=50000,
                cost_basis_cents=40000,
                cost_basis_source="brokerage_import",
                cost_basis_quality="verified",
                market_value_source="calculated_from_price",
                valuation_quality="current",
                confidence="high",
            ),
        ]
    )
    db.flush()
    report = calculate_net_worth(db)
    assert report["net_worth_cents"] == 70000
    assert all("999999" not in warning for warning in report["metadata"]["warnings"])


def test_cash_flow_excludes_confirmed_transfers(db):
    checking = account(db)
    income = category(db, "Paycheck", "income")
    expense = category(db, "Groceries", "expense")
    today = date.today()
    transaction(db, checking.id, 100000, today, "Paycheck", category_id=income.id, transaction_type="income")
    transaction(db, checking.id, -2500, today, "Groceries", category_id=expense.id, transaction_type="expense")
    transaction(
        db,
        checking.id,
        -40000,
        today,
        "Card Payment",
        transfer_status="confirmed_transfer",
        transaction_type="transfer",
    )
    flow = cash_flow(db, today - timedelta(days=1), today + timedelta(days=1))
    assert flow["income_cents"] == 100000
    assert flow["expenses_cents"] == 2500


def test_allocation_warns_on_missing_classification_and_basis(db):
    acct = account(db, "Wallet", account_type="crypto_wallet", valuation_method="holdings_sum")
    asset = instrument(db, "MYST", "other")
    db.add(
        HoldingSnapshot(
            account_id=acct.id,
            instrument_id=asset.id,
            snapshot_date=date.today(),
            quantity_decimal="2",
            price_decimal="10",
            market_value_cents=2000,
            cost_basis_cents=None,
            cost_basis_source="unknown",
            cost_basis_quality="missing",
            market_value_source="manual",
            valuation_quality="current",
            confidence="low",
        )
    )
    db.flush()
    allocation = asset_allocation(db)
    assert allocation["slices"][0]["asset_class"] == "other"
    assert allocation["warnings"]


def test_data_quality_generates_missing_cost_basis_issue(db):
    acct = account(db, "Coinbase", account_type="crypto_exchange", valuation_method="holdings_sum")
    btc = instrument(db, "BTC", "crypto")
    db.add(
        HoldingSnapshot(
            account_id=acct.id,
            instrument_id=btc.id,
            snapshot_date=date.today(),
            quantity_decimal="0.1",
            price_decimal="60000",
            market_value_cents=600000,
            cost_basis_cents=None,
            cost_basis_source="coinbase_api_inferred",
            cost_basis_quality="incomplete",
            market_value_source="calculated_from_price",
            valuation_quality="current",
            confidence="low",
        )
    )
    db.flush()
    issues = recompute_data_quality(db)
    assert any(issue.issue_type == "missing_cost_basis" for issue in issues)
