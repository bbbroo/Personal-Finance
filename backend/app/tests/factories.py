from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.domain import Account, Category, CategoryGroup, Instrument, Transaction
from app.services.transaction_service import transaction_fingerprint


def account(db: Session, name: str = "Checking", **kwargs) -> Account:
    row = Account(
        name=name,
        institution=kwargs.pop("institution", "Test Bank"),
        account_type=kwargs.pop("account_type", "cash"),
        valuation_method=kwargs.pop("valuation_method", "balance_snapshot"),
        balance_sign_policy=kwargs.pop("balance_sign_policy", "asset_positive"),
        **kwargs,
    )
    db.add(row)
    db.flush()
    return row


def category(db: Session, name: str = "Groceries", category_type: str = "expense") -> Category:
    group = CategoryGroup(name=f"{name} Group", group_type=category_type, sort_order=1)
    db.add(group)
    db.flush()
    row = Category(group_id=group.id, name=name, category_type=category_type, budget_behavior="budgeted")
    db.add(row)
    db.flush()
    return row


def instrument(db: Session, symbol: str = "VTI", asset_class: str = "us_stock") -> Instrument:
    row = Instrument(symbol=symbol, name=symbol, instrument_type="etf", default_asset_class=asset_class)
    db.add(row)
    db.flush()
    return row


def transaction(
    db: Session,
    account_id: str,
    amount_cents: int,
    transaction_date: date,
    description: str = "Test",
    **kwargs,
) -> Transaction:
    row = Transaction(
        account_id=account_id,
        transaction_date=transaction_date,
        original_description=description,
        merchant_name=description,
        amount_cents=amount_cents,
        transaction_type=kwargs.pop("transaction_type", "expense" if amount_cents < 0 else "income"),
        transfer_status=kwargs.pop("transfer_status", "not_transfer"),
        fingerprint=transaction_fingerprint(account_id, transaction_date, amount_cents, description),
        source_type=kwargs.pop("source_type", "manual"),
        **kwargs,
    )
    db.add(row)
    db.flush()
    return row
