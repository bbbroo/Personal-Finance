from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.domain import (
    Account,
    AccountBalanceSnapshot,
    AccountStatement,
    DataQualityIssue,
    HoldingSnapshot,
    Price,
)


def _issue(**kwargs) -> DataQualityIssue:
    return DataQualityIssue(status="open", **kwargs)


def recompute_data_quality(db: Session) -> list[DataQualityIssue]:
    db.execute(delete(DataQualityIssue).where(DataQualityIssue.status == "open"))
    today = date.today()
    issues: list[DataQualityIssue] = []

    accounts = list(db.scalars(select(Account).where(Account.is_active.is_(True), Account.include_in_net_worth.is_(True))))
    for account in accounts:
        balances = list(
            db.scalars(
                select(AccountBalanceSnapshot)
                .where(AccountBalanceSnapshot.account_id == account.id)
                .order_by(AccountBalanceSnapshot.snapshot_date.desc())
            )
        )
        has_holdings = db.scalar(select(HoldingSnapshot.id).where(HoldingSnapshot.account_id == account.id).limit(1))
        if account.valuation_method in {"balance_snapshot", "manual", "liability_balance"} and not balances and not has_holdings:
            issues.append(
                _issue(
                    severity="warning",
                    issue_type="missing_data",
                    entity_type="account",
                    entity_id=account.id,
                    title=f"{account.name} is missing valuation data",
                    description="This account has no balance snapshot or holding value, so reports cannot fully value it.",
                    recommended_action="Add a manual balance, import balances, or import holdings.",
                )
            )
        if balances:
            latest = balances[0]
            if (today - latest.snapshot_date).days > account.freshness_threshold_days:
                issues.append(
                    _issue(
                        severity="warning",
                        issue_type="stale_data",
                        entity_type="account",
                        entity_id=account.id,
                        title=f"{account.name} balance is stale",
                        description=f"Latest balance is from {latest.snapshot_date.isoformat()}.",
                        recommended_action="Refresh the balance or import a newer statement.",
                    )
                )
            if not latest.is_reconciled:
                issues.append(
                    _issue(
                        severity="info",
                        issue_type="unreconciled",
                        entity_type="account",
                        entity_id=account.id,
                        title=f"{account.name} is not reconciled",
                        description="Latest balance is not tied to a reconciled statement.",
                        recommended_action="Run reconciliation for the latest statement period.",
                    )
                )
        if account.valuation_method in {"holdings_sum", "holdings_plus_cash"} and balances and has_holdings:
            issues.append(
                _issue(
                    severity="info",
                    issue_type="double_count_risk",
                    entity_type="account",
                    entity_id=account.id,
                    title=f"{account.name} has balances and holdings",
                    description="Net worth uses holdings and only cash-position balances to avoid double-counting.",
                    recommended_action="Use cash-position balance snapshots for brokerage cash.",
                )
            )

    holdings = list(db.scalars(select(HoldingSnapshot).where(HoldingSnapshot.is_current.is_(True))))
    for holding in holdings:
        if holding.cost_basis_quality in {"missing", "incomplete"}:
            issues.append(
                _issue(
                    severity="warning",
                    issue_type="missing_cost_basis",
                    entity_type="holding",
                    entity_id=holding.id,
                    title="Holding cost basis is incomplete",
                    description="Gain/loss is unknown or low-confidence until basis is verified/imported.",
                    recommended_action="Import a verified broker/tax export or manually verify cost basis.",
                )
            )
        if holding.market_value_cents is None:
            issues.append(
                _issue(
                    severity="warning",
                    issue_type="missing_data",
                    entity_type="holding",
                    entity_id=holding.id,
                    title="Holding is missing market value",
                    description="The holding cannot contribute confidently to allocation or net worth.",
                    recommended_action="Add a manual price or import a holding value.",
                )
            )

    for statement in db.scalars(select(AccountStatement).where(AccountStatement.status.in_(["draft", "mismatch"]))):
        issues.append(
            _issue(
                severity="error" if statement.status == "mismatch" else "info",
                issue_type="unreconciled",
                entity_type="account_statement",
                entity_id=statement.id,
                title="Statement needs reconciliation",
                description=f"Statement ending {statement.period_end.isoformat()} is {statement.status}.",
                recommended_action="Run reconciliation or accept an explicit difference.",
            )
        )

    for price in db.scalars(select(Price).where(Price.status.in_(["stale", "missing", "failed"]))):
        issues.append(
            _issue(
                severity="warning",
                issue_type="stale_price",
                entity_type="price",
                entity_id=price.id,
                title="Price is stale or unavailable",
                description=f"Price status is {price.status}.",
                recommended_action="Refresh prices or enter a manual override.",
            )
        )

    db.add_all(issues)
    db.flush()
    return issues


def ignore_issue(db: Session, issue: DataQualityIssue) -> DataQualityIssue:
    issue.status = "ignored"
    return issue
