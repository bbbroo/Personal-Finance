from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    Account,
    AccountBalanceSnapshot,
    AccountStatement,
    BudgetCategoryPlan,
    BudgetPeriod,
    Category,
    CategoryGroup,
    Goal,
    HoldingSnapshot,
    Instrument,
    Liability,
    LiabilityTermsHistory,
    Price,
    RecurringTransaction,
    RolloverLedger,
    SinkingFund,
    Transaction,
    TransferLink,
    utc_now,
)
from app.services.transaction_service import transaction_fingerprint


def _get_category(db: Session, name: str) -> Category:
    category = db.scalars(select(Category).where(Category.name == name)).first()
    assert category is not None
    return category


def ensure_seed_data(db: Session) -> None:
    if db.scalar(select(Account.id).limit(1)):
        return
    today = date.today()
    month_start = today.replace(day=1)
    prior = today - timedelta(days=30)

    groups = [
        CategoryGroup(name="Income", group_type="income", sort_order=1, is_system=True),
        CategoryGroup(name="Fixed", group_type="fixed_expense", sort_order=2, is_system=True),
        CategoryGroup(name="Flexible", group_type="flexible_expense", sort_order=3, is_system=True),
        CategoryGroup(name="Transfers", group_type="transfer", sort_order=4, is_system=True),
        CategoryGroup(name="Investing", group_type="investment", sort_order=5, is_system=True),
        CategoryGroup(name="Liabilities", group_type="liability", sort_order=6, is_system=True),
    ]
    db.add_all(groups)
    db.flush()
    group_by_name = {group.name: group for group in groups}
    categories = [
        Category(group_id=group_by_name["Income"].id, name="Paycheck", category_type="income", budget_behavior="income", is_system=True),
        Category(group_id=group_by_name["Fixed"].id, name="Rent", category_type="expense", budget_behavior="budgeted", is_system=True),
        Category(group_id=group_by_name["Flexible"].id, name="Groceries", category_type="expense", budget_behavior="budgeted", is_system=True),
        Category(group_id=group_by_name["Flexible"].id, name="Dining", category_type="expense", budget_behavior="budgeted", is_system=True),
        Category(group_id=group_by_name["Transfers"].id, name="Credit Card Payment", category_type="transfer", budget_behavior="transfer", is_system=True),
        Category(group_id=group_by_name["Investing"].id, name="Brokerage Contribution", category_type="investment", budget_behavior="ignored", is_system=True),
        Category(group_id=group_by_name["Liabilities"].id, name="Interest", category_type="expense", budget_behavior="budgeted", is_system=True),
    ]
    db.add_all(categories)
    db.flush()
    paycheck = _get_category(db, "Paycheck")
    rent = _get_category(db, "Rent")
    groceries = _get_category(db, "Groceries")
    dining = _get_category(db, "Dining")
    cc_payment = _get_category(db, "Credit Card Payment")
    contribution = _get_category(db, "Brokerage Contribution")

    checking = Account(
        name="Everyday Checking",
        institution="Chase",
        account_type="cash",
        account_subtype="checking",
        valuation_method="balance_snapshot",
        balance_sign_policy="asset_positive",
        data_source="mixed",
        freshness_threshold_days=7,
    )
    credit = Account(
        name="Rewards Credit Card",
        institution="Chase",
        account_type="credit_card",
        account_subtype="visa",
        valuation_method="liability_balance",
        balance_sign_policy="liability_positive",
        data_source="mixed",
        freshness_threshold_days=7,
    )
    brokerage = Account(
        name="Taxable Brokerage",
        institution="Schwab",
        account_type="brokerage",
        account_subtype="taxable",
        valuation_method="holdings_plus_cash",
        balance_sign_policy="asset_positive",
        data_source="csv",
        include_in_budget=False,
        freshness_threshold_days=7,
    )
    coinbase = Account(
        name="Coinbase",
        institution="Coinbase",
        account_type="crypto_exchange",
        valuation_method="holdings_sum",
        balance_sign_policy="asset_positive",
        include_in_budget=False,
        data_source="api",
        freshness_threshold_days=2,
    )
    ledger = Account(
        name="Ledger Wallet",
        institution="Ledger",
        account_type="crypto_wallet",
        valuation_method="holdings_sum",
        balance_sign_policy="asset_positive",
        include_in_budget=False,
        data_source="manual",
        freshness_threshold_days=14,
    )
    student_loan_account = Account(
        name="Student Loan",
        institution="Manual",
        account_type="liability",
        account_subtype="student_loan",
        valuation_method="liability_balance",
        balance_sign_policy="liability_positive",
        include_in_budget=False,
        data_source="manual",
        freshness_threshold_days=14,
    )
    db.add_all([checking, credit, brokerage, coinbase, ledger, student_loan_account])
    db.flush()

    db.add_all(
        [
            AccountBalanceSnapshot(
                account_id=checking.id,
                snapshot_date=prior,
                balance_cents=920000,
                balance_kind="statement",
                source_type="manual",
                confidence="verified",
                is_reconciled=True,
            ),
            AccountBalanceSnapshot(
                account_id=checking.id,
                snapshot_date=today,
                balance_cents=1084500,
                balance_kind="current",
                source_type="manual",
                confidence="high",
                is_reconciled=False,
            ),
            AccountBalanceSnapshot(
                account_id=brokerage.id,
                snapshot_date=today,
                balance_cents=125000,
                balance_kind="cash_position",
                source_type="manual",
                confidence="high",
                is_reconciled=False,
            ),
        ]
    )

    transfer_link = TransferLink(
        confidence_score="0.99",
        match_basis="exact_amount_date_owned_accounts",
        status="confirmed",
        created_by="system",
        confirmed_at=utc_now(),
    )
    db.add(transfer_link)
    db.flush()
    transactions = [
        Transaction(
            account_id=checking.id,
            transaction_date=month_start + timedelta(days=1),
            original_description="ACME PAYROLL DIRECT DEP",
            merchant_name="Acme Payroll",
            amount_cents=520000,
            category_id=paycheck.id,
            transaction_type="income",
            review_status="reviewed",
            fingerprint=transaction_fingerprint(checking.id, month_start + timedelta(days=1), 520000, "Acme Payroll"),
            source_type="manual",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=month_start + timedelta(days=2),
            original_description="RENT PORTAL",
            merchant_name="Rent Portal",
            amount_cents=-185000,
            category_id=rent.id,
            transaction_type="expense",
            review_status="reviewed",
            fingerprint=transaction_fingerprint(checking.id, month_start + timedelta(days=2), -185000, "Rent Portal"),
            source_type="manual",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=month_start + timedelta(days=5),
            original_description="WHOLE FOODS MARKET",
            merchant_name="Whole Foods",
            amount_cents=-8734,
            category_id=groceries.id,
            transaction_type="expense",
            review_status="reviewed",
            fingerprint=transaction_fingerprint(credit.id, month_start + timedelta(days=5), -8734, "Whole Foods"),
            source_type="manual",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=month_start + timedelta(days=8),
            original_description="LOCAL CAFE",
            merchant_name="Local Cafe",
            amount_cents=-2812,
            category_id=dining.id,
            transaction_type="expense",
            review_status="reviewed",
            fingerprint=transaction_fingerprint(credit.id, month_start + timedelta(days=8), -2812, "Local Cafe"),
            source_type="manual",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=month_start + timedelta(days=10),
            original_description="CHASE CREDIT CARD PAYMENT",
            merchant_name="Chase Credit Card Payment",
            amount_cents=-50000,
            category_id=cc_payment.id,
            transaction_type="transfer",
            transfer_status="confirmed_transfer",
            transfer_link_id=transfer_link.id,
            review_status="reviewed",
            fingerprint=transaction_fingerprint(checking.id, month_start + timedelta(days=10), -50000, "Chase Credit Card Payment"),
            source_type="manual",
        ),
        Transaction(
            account_id=credit.id,
            transaction_date=month_start + timedelta(days=11),
            original_description="PAYMENT THANK YOU",
            merchant_name="Payment Thank You",
            amount_cents=50000,
            category_id=cc_payment.id,
            transaction_type="transfer",
            transfer_status="confirmed_transfer",
            transfer_link_id=transfer_link.id,
            review_status="reviewed",
            fingerprint=transaction_fingerprint(credit.id, month_start + timedelta(days=11), 50000, "Payment Thank You"),
            source_type="manual",
        ),
        Transaction(
            account_id=checking.id,
            transaction_date=month_start + timedelta(days=13),
            original_description="SCHWAB ACH",
            merchant_name="Schwab Contribution",
            amount_cents=-30000,
            category_id=contribution.id,
            transaction_type="investment",
            review_status="reviewed",
            fingerprint=transaction_fingerprint(checking.id, month_start + timedelta(days=13), -30000, "Schwab Contribution"),
            source_type="manual",
        ),
    ]
    db.add_all(transactions)

    instruments = [
        Instrument(symbol="VTI", provider_symbol="VTI", name="Vanguard Total Stock Market ETF", instrument_type="etf", default_asset_class="us_stock", price_provider="manual"),
        Instrument(symbol="VXUS", provider_symbol="VXUS", name="Vanguard Total International Stock ETF", instrument_type="etf", default_asset_class="international_stock", price_provider="manual"),
        Instrument(symbol="BTC", provider_symbol="bitcoin", name="Bitcoin", instrument_type="crypto", default_asset_class="crypto", price_provider="manual"),
        Instrument(symbol="ETH", provider_symbol="ethereum", name="Ethereum", instrument_type="crypto", default_asset_class="crypto", price_provider="manual"),
    ]
    db.add_all(instruments)
    db.flush()
    by_symbol = {instrument.symbol: instrument for instrument in instruments}
    db.add_all(
        [
            Price(instrument_id=by_symbol["VTI"].id, price_date=today, price_decimal="275.12", provider="manual", status="current", confidence="medium"),
            Price(instrument_id=by_symbol["VXUS"].id, price_date=today, price_decimal="67.45", provider="manual", status="current", confidence="medium"),
            Price(instrument_id=by_symbol["BTC"].id, price_date=today - timedelta(days=3), price_decimal="65000", provider="manual", status="stale", confidence="low"),
            Price(instrument_id=by_symbol["ETH"].id, price_date=today - timedelta(days=10), price_decimal="3400", provider="manual", status="stale", confidence="low"),
            HoldingSnapshot(
                account_id=brokerage.id,
                instrument_id=by_symbol["VTI"].id,
                snapshot_date=today,
                quantity_decimal="82.5",
                price_decimal="275.12",
                market_value_cents=2269740,
                cost_basis_cents=1875000,
                unrealized_gain_loss_cents=394740,
                unrealized_gain_loss_pct="0.2105",
                cost_basis_source="brokerage_import",
                cost_basis_quality="verified",
                market_value_source="calculated_from_price",
                valuation_quality="current",
                confidence="high",
                source_type="csv_import",
            ),
            HoldingSnapshot(
                account_id=brokerage.id,
                instrument_id=by_symbol["VXUS"].id,
                snapshot_date=today,
                quantity_decimal="45",
                price_decimal="67.45",
                market_value_cents=303525,
                cost_basis_cents=285000,
                unrealized_gain_loss_cents=18525,
                unrealized_gain_loss_pct="0.065",
                cost_basis_source="brokerage_import",
                cost_basis_quality="verified",
                market_value_source="calculated_from_price",
                valuation_quality="current",
                confidence="high",
                source_type="csv_import",
            ),
            HoldingSnapshot(
                account_id=coinbase.id,
                instrument_id=by_symbol["BTC"].id,
                snapshot_date=today,
                quantity_decimal="0.175",
                price_decimal="65000",
                market_value_cents=1137500,
                cost_basis_cents=None,
                unrealized_gain_loss_cents=None,
                unrealized_gain_loss_pct=None,
                cost_basis_source="coinbase_api_inferred",
                cost_basis_quality="incomplete",
                market_value_source="calculated_from_price",
                valuation_quality="stale",
                confidence="low",
                source_type="api",
            ),
            HoldingSnapshot(
                account_id=ledger.id,
                instrument_id=by_symbol["ETH"].id,
                snapshot_date=today - timedelta(days=16),
                quantity_decimal="2.2",
                price_decimal="3400",
                market_value_cents=748000,
                cost_basis_cents=None,
                unrealized_gain_loss_cents=None,
                unrealized_gain_loss_pct=None,
                cost_basis_source="unknown",
                cost_basis_quality="missing",
                market_value_source="manual",
                valuation_quality="stale",
                confidence="low",
                source_type="manual",
                notes="Manual Ledger holding only; no seed phrase or wallet scanning.",
            ),
        ]
    )

    liability = Liability(
        account_id=student_loan_account.id,
        liability_type="student_loan",
        current_balance_cents=1450000,
        minimum_payment_cents=22500,
        due_day=15,
        confidence="medium",
    )
    db.add(liability)
    db.flush()
    db.add(LiabilityTermsHistory(liability_id=liability.id, effective_date=prior, apr_decimal="0.0525", minimum_payment_cents=22500))

    budget_period = BudgetPeriod(period_type="monthly", start_date=month_start, end_date=today.replace(day=28), status="active")
    db.add(budget_period)
    db.flush()
    db.add_all(
        [
            BudgetCategoryPlan(budget_period_id=budget_period.id, category_id=rent.id, planned_cents=185000, plan_type="fixed"),
            BudgetCategoryPlan(budget_period_id=budget_period.id, category_id=groceries.id, planned_cents=65000, rollover_enabled=True, plan_type="flexible"),
            BudgetCategoryPlan(budget_period_id=budget_period.id, category_id=dining.id, planned_cents=25000, plan_type="flexible"),
            RolloverLedger(category_id=groceries.id, budget_period_id=budget_period.id, starting_rollover_cents=12000, budgeted_cents=65000, actual_cents=8734, adjustment_cents=0, ending_rollover_cents=68266),
            SinkingFund(name="Annual Insurance", linked_category_id=rent.id, target_cents=120000, monthly_set_aside_cents=10000, current_balance_cents=45000, status="active"),
            RecurringTransaction(
                merchant_name="Rent Portal",
                account_id=checking.id,
                category_id=rent.id,
                expected_amount_cents=185000,
                cadence="monthly",
                next_expected_date=(month_start + timedelta(days=32)).replace(day=2),
                last_seen_date=month_start + timedelta(days=2),
                confidence="verified",
                detection_source="system_detected",
            ),
            Goal(name="Emergency Fund", goal_type="savings", target_cents=2000000, current_manual_cents=1084500, target_date=today + timedelta(days=365), progress_method="manual"),
            AccountStatement(
                account_id=checking.id,
                period_start=prior,
                period_end=today,
                opening_balance_cents=920000,
                ending_balance_cents=1084500,
                source="manual",
                status="draft",
                notes="Demo statement intentionally available for reconciliation.",
            ),
        ]
    )
    db.commit()
