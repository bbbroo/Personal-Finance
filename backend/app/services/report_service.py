from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.core.enums import Confidence, ValuationMethod, weakest_confidence
from app.core.money import cents_to_dollars, percent, quantity_times_price_to_cents
from app.models.domain import (
    Account,
    AccountBalanceSnapshot,
    Category,
    HoldingSnapshot,
    Instrument,
    Liability,
    SymbolAllocationOverride,
    Transaction,
    TransactionSplit,
)
from app.services.holding_service import latest_holdings_as_of


def _latest_balance(
    db: Session, account_id: str, as_of: date, *, kinds: list[str] | None = None
) -> AccountBalanceSnapshot | None:
    query = select(AccountBalanceSnapshot).where(
        AccountBalanceSnapshot.account_id == account_id,
        AccountBalanceSnapshot.snapshot_date <= as_of,
    )
    if kinds:
        query = query.where(AccountBalanceSnapshot.balance_kind.in_(kinds))
    return db.scalars(query.order_by(desc(AccountBalanceSnapshot.snapshot_date))).first()


def _current_holdings(db: Session, account_id: str, as_of: date) -> list[HoldingSnapshot]:
    return latest_holdings_as_of(db, account_id=account_id, as_of=as_of)


def _normalize_balance_for_account(account: Account, balance_cents: int) -> int:
    if account.balance_sign_policy == "invert_imported":
        return -balance_cents
    if account.balance_sign_policy == "liability_positive":
        return abs(balance_cents)
    return balance_cents


def _holding_value(holding: HoldingSnapshot) -> tuple[int | None, list[str]]:
    warnings: list[str] = []
    value = holding.market_value_cents
    if value is None and holding.price_decimal is not None:
        value = quantity_times_price_to_cents(holding.quantity_decimal, holding.price_decimal)
    if value is None:
        warnings.append("Missing holding market value")
    if holding.cost_basis_quality in {"missing", "incomplete", "estimated"}:
        warnings.append(f"Cost basis is {holding.cost_basis_quality}")
    if holding.valuation_quality in {"stale", "missing", "estimated"}:
        warnings.append(f"Market value is {holding.valuation_quality}")
    return value, warnings


def calculate_net_worth(db: Session, as_of: date | None = None) -> dict[str, Any]:
    as_of = as_of or date.today()
    accounts = list(
        db.scalars(
            select(Account).where(Account.is_active.is_(True), Account.include_in_net_worth.is_(True)).order_by(Account.name)
        )
    )
    assets = 0
    liabilities = 0
    stale_count = 0
    missing_count = 0
    unreconciled_count = 0
    warnings: list[str] = []
    account_rows: list[dict[str, Any]] = []
    confidences: list[str] = []

    for account in accounts:
        if account.valuation_method == ValuationMethod.EXCLUDED:
            continue
        value: int | None = None
        account_warnings: list[str] = []
        confidence = Confidence.UNKNOWN
        is_liability = account.valuation_method == ValuationMethod.LIABILITY_BALANCE or account.account_type in {
            "credit_card",
            "liability",
        }

        if account.valuation_method in {ValuationMethod.BALANCE_SNAPSHOT, ValuationMethod.MANUAL}:
            balance = _latest_balance(db, account.id, as_of)
            if balance is None or balance.balance_cents is None:
                account_warnings.append("Missing balance snapshot")
                missing_count += 1
            else:
                value = _normalize_balance_for_account(account, balance.balance_cents)
                confidence = Confidence(balance.confidence)
                if (as_of - balance.snapshot_date).days > account.freshness_threshold_days:
                    account_warnings.append("Balance snapshot is stale")
                    stale_count += 1
                if not balance.is_reconciled:
                    unreconciled_count += 1
                    account_warnings.append("Latest balance is unreconciled")

        elif account.valuation_method == ValuationMethod.LIABILITY_BALANCE:
            liability = db.scalars(select(Liability).where(Liability.account_id == account.id)).first()
            if liability:
                value = abs(liability.current_balance_cents)
                confidence = Confidence(liability.confidence)
            else:
                balance = _latest_balance(db, account.id, as_of)
                if balance and balance.balance_cents is not None:
                    value = abs(_normalize_balance_for_account(account, balance.balance_cents))
                    confidence = Confidence(balance.confidence)
                else:
                    missing_count += 1
                    account_warnings.append("Missing liability balance")

        elif account.valuation_method in {ValuationMethod.HOLDINGS_SUM, ValuationMethod.HOLDINGS_PLUS_CASH}:
            holdings = _current_holdings(db, account.id, as_of)
            if holdings:
                total = 0
                for holding in holdings:
                    holding_value, holding_warnings = _holding_value(holding)
                    account_warnings.extend(holding_warnings)
                    confidences.append(holding.confidence)
                    if holding_value is None:
                        missing_count += 1
                    else:
                        total += holding_value
                value = total
                confidence = weakest_confidence([holding.confidence for holding in holdings])
                if account.valuation_method == ValuationMethod.HOLDINGS_PLUS_CASH:
                    cash = _latest_balance(db, account.id, as_of, kinds=["cash", "cash_position"])
                    if cash and cash.balance_cents is not None:
                        value += _normalize_balance_for_account(account, cash.balance_cents)
                        confidences.append(cash.confidence)
                    else:
                        full_balance = _latest_balance(db, account.id, as_of)
                        if full_balance and full_balance.balance_cents is not None:
                            account_warnings.append(
                                "Full account balance ignored to prevent double-counting holdings; add a cash-position balance if needed"
                            )
            else:
                fallback = _latest_balance(db, account.id, as_of)
                if fallback and fallback.balance_cents is not None:
                    value = _normalize_balance_for_account(account, fallback.balance_cents)
                    confidence = Confidence(fallback.confidence)
                    account_warnings.append("Using account balance fallback because holdings are missing")
                else:
                    missing_count += 1
                    account_warnings.append("Missing holdings valuation")

        if value is not None:
            if is_liability:
                liabilities += abs(value)
            else:
                assets += value
        if account_warnings:
            warnings.extend([f"{account.name}: {warning}" for warning in account_warnings])
        confidences.append(str(confidence))
        account_rows.append(
            {
                "account_id": account.id,
                "name": account.name,
                "account_type": account.account_type,
                "valuation_method": account.valuation_method,
                "value_cents": value,
                "is_liability": is_liability,
                "confidence": str(confidence),
                "warnings": account_warnings,
            }
        )

    overall_confidence = weakest_confidence(confidences + ([Confidence.LOW] if warnings else []))
    return {
        "as_of": as_of.isoformat(),
        "assets_cents": assets,
        "liabilities_cents": liabilities,
        "net_worth_cents": assets - liabilities,
        "confidence": overall_confidence,
        "metadata": {
            "included_account_count": len(account_rows),
            "stale_account_count": stale_count,
            "missing_account_valuation_count": missing_count,
            "unreconciled_account_count": unreconciled_count,
            "warnings": warnings,
        },
        "accounts": account_rows,
    }


def net_worth_history(db: Session) -> list[dict[str, Any]]:
    dates = set(db.scalars(select(AccountBalanceSnapshot.snapshot_date)))
    dates.update(db.scalars(select(HoldingSnapshot.snapshot_date)))
    if not dates:
        return []
    points = []
    for point_date in sorted(dates):
        report = calculate_net_worth(db, point_date)
        points.append(
            {
                "date": point_date.isoformat(),
                "net_worth_cents": report["net_worth_cents"],
                "assets_cents": report["assets_cents"],
                "liabilities_cents": report["liabilities_cents"],
                "confidence": report["confidence"],
                "warnings": report["metadata"]["warnings"],
            }
        )
    return points


def cash_flow(db: Session, start_date: date, end_date: date) -> dict[str, Any]:
    transactions = list(
        db.scalars(
            select(Transaction).where(
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date,
                Transaction.is_hidden.is_(False),
                Transaction.transfer_status != "confirmed_transfer",
            )
        )
    )
    income = 0
    expenses = 0
    warnings: list[str] = []
    for txn in transactions:
        if txn.is_split and txn.splits:
            lines = txn.splits
        else:
            lines = [txn]
        for line in lines:
            amount = line.amount_cents
            category = db.get(Category, line.category_id) if getattr(line, "category_id", None) else None
            category_type = category.category_type if category else txn.transaction_type
            if category_type == "income" or (txn.transaction_type == "income" and amount > 0):
                income += max(amount, 0)
            elif category_type in {"expense", "liability_payment"} or amount < 0:
                expenses += abs(min(amount, 0))
            elif category is None and txn.transaction_type == "unknown":
                warnings.append(f"Uncategorized transaction {txn.id} excluded from categorized confidence")
    savings = None if income == 0 else percent(income - expenses, income)
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "income_cents": income,
        "expenses_cents": expenses,
        "savings_rate_decimal": savings,
        "confidence": Confidence.MEDIUM if warnings else Confidence.HIGH,
        "warnings": warnings,
    }


def spending_by_category(db: Session, start_date: date, end_date: date) -> list[dict[str, Any]]:
    totals: dict[str, int] = defaultdict(int)
    names: dict[str, str] = {}
    txns = db.scalars(
        select(Transaction).where(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Transaction.is_hidden.is_(False),
            Transaction.transfer_status != "confirmed_transfer",
        )
    )
    for txn in txns:
        if txn.is_split and txn.splits:
            for split in txn.splits:
                category = db.get(Category, split.category_id)
                if category and category.category_type == "expense":
                    totals[category.id] += abs(min(split.amount_cents, 0))
                    names[category.id] = category.name
        elif txn.category_id:
            category = db.get(Category, txn.category_id)
            if category and category.category_type == "expense":
                totals[category.id] += abs(min(txn.amount_cents, 0))
                names[category.id] = category.name
    return [
        {"category_id": category_id, "category_name": names[category_id], "amount_cents": amount}
        for category_id, amount in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def asset_allocation(db: Session, as_of: date | None = None, *, mode: str = "investment_only") -> dict[str, Any]:
    as_of = as_of or date.today()
    if mode not in {"investment_only", "full_net_worth"}:
        raise ValueError("mode must be investment_only or full_net_worth")
    holdings = latest_holdings_as_of(db, as_of=as_of)
    totals: dict[str, int] = defaultdict(int)
    warnings: list[str] = []
    total = 0
    holding_account_ids: set[str] = set()
    for holding in holdings:
        account = db.get(Account, holding.account_id)
        if not account or not account.include_in_net_worth or not account.is_active:
            continue
        if mode == "investment_only" and account.account_type not in {"brokerage", "retirement", "hsa", "crypto_exchange", "crypto_wallet"}:
            continue
        holding_account_ids.add(account.id)
        instrument = db.get(Instrument, holding.instrument_id)
        override = db.scalars(
            select(SymbolAllocationOverride).where(SymbolAllocationOverride.instrument_id == holding.instrument_id)
        ).first()
        asset_class = override.asset_class if override else (instrument.default_asset_class if instrument else "other")
        value, holding_warnings = _holding_value(holding)
        if value is None:
            warnings.append(f"{instrument.symbol if instrument else holding.id}: missing market value")
            continue
        totals[asset_class] += value
        total += value
        if asset_class == "other":
            warnings.append(f"{instrument.symbol if instrument else holding.id}: needs asset class classification")
        warnings.extend([f"{instrument.symbol if instrument else holding.id}: {warning}" for warning in holding_warnings])
    if mode == "full_net_worth":
        accounts = db.scalars(
            select(Account).where(Account.is_active.is_(True), Account.include_in_net_worth.is_(True)).order_by(Account.name)
        )
        for account in accounts:
            if account.valuation_method == ValuationMethod.EXCLUDED:
                continue
            is_liability = account.valuation_method == ValuationMethod.LIABILITY_BALANCE or account.account_type in {
                "credit_card",
                "liability",
            }
            if account.valuation_method == ValuationMethod.HOLDINGS_PLUS_CASH:
                cash = _latest_balance(db, account.id, as_of, kinds=["cash", "cash_position"])
                if cash and cash.balance_cents is not None:
                    value = _normalize_balance_for_account(account, cash.balance_cents)
                    totals["cash"] += value
                    total += value
                continue
            if account.valuation_method == ValuationMethod.HOLDINGS_SUM and account.id in holding_account_ids:
                continue
            balance = _latest_balance(db, account.id, as_of)
            value: int | None = None
            if is_liability:
                liability = db.scalars(select(Liability).where(Liability.account_id == account.id)).first()
                if liability:
                    value = -abs(liability.current_balance_cents)
                elif balance and balance.balance_cents is not None:
                    value = -abs(_normalize_balance_for_account(account, balance.balance_cents))
            elif account.valuation_method in {ValuationMethod.BALANCE_SNAPSHOT, ValuationMethod.MANUAL}:
                if balance and balance.balance_cents is not None:
                    value = _normalize_balance_for_account(account, balance.balance_cents)
            if value is None:
                warnings.append(f"{account.name}: missing allocation value")
                continue
            asset_class = "liability" if is_liability else ("cash" if account.account_type == "cash" else account.account_type)
            totals[asset_class] += value
            total += value
    slices = [
        {
            "asset_class": asset_class,
            "value_cents": value,
            "percent_decimal": str((Decimal(value) / Decimal(total)).quantize(Decimal("0.0001"))) if total else None,
        }
        for asset_class, value in sorted(totals.items())
    ]
    return {
        "as_of": as_of.isoformat(),
        "mode": mode,
        "total_cents": total,
        "slices": slices,
        "confidence": Confidence.LOW if warnings else Confidence.HIGH,
        "warnings": warnings,
    }


def dashboard(db: Session) -> dict[str, Any]:
    today = date.today()
    start = today.replace(day=1)
    net_worth = calculate_net_worth(db, today)
    flow = cash_flow(db, start, today)
    allocation = asset_allocation(db, today)
    accounts = net_worth["accounts"]
    cash = sum(row["value_cents"] or 0 for row in accounts if row["account_type"] == "cash")
    investments = sum(
        row["value_cents"] or 0
        for row in accounts
        if row["account_type"] in {"brokerage", "retirement", "hsa"}
    )
    crypto = sum(
        row["value_cents"] or 0
        for row in accounts
        if row["account_type"] in {"crypto_exchange", "crypto_wallet"}
    )
    return {
        "net_worth": net_worth,
        "cash_flow": flow,
        "allocation": allocation,
        "cards": {
            "cash_balance_cents": cash,
            "investments_total_cents": investments,
            "crypto_total_cents": crypto,
            "liabilities_total_cents": net_worth["liabilities_cents"],
            "monthly_income_cents": flow["income_cents"],
            "monthly_expenses_cents": flow["expenses_cents"],
            "savings_rate_decimal": flow["savings_rate_decimal"],
        },
        "history": net_worth_history(db),
    }
