from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select

from app.core.security import normalized_hash
from sqlalchemy.orm import Session

from app.models.domain import (
    Account,
    AccountBalanceSnapshot,
    AccountStatement,
    DataQualityIssue,
    DebtPaymentAllocation,
    HoldingSnapshot,
    Instrument,
    Liability,
    LiabilityTermsHistory,
    Price,
)
from app.services.holding_service import latest_holdings_as_of


PRICE_STALE_DAYS = {
    "crypto": 2,
    "stock": 3,
    "etf": 3,
    "mutual_fund": 3,
}


def _issue_fingerprint(issue: DataQualityIssue | dict) -> str:
    getter = issue.get if isinstance(issue, dict) else lambda key: getattr(issue, key)
    return normalized_hash(
        [
            getter("issue_type"),
            getter("entity_type"),
            getter("entity_id"),
            getter("title"),
            getter("description"),
            getter("recommended_action"),
        ]
    )


def _issue(**kwargs) -> DataQualityIssue:
    fingerprint = _issue_fingerprint(kwargs)
    return DataQualityIssue(status="open", fingerprint=fingerprint, **kwargs)


def _persist_issues_preserving_ignored(db: Session, issues: list[DataQualityIssue]) -> list[DataQualityIssue]:
    ignored_fingerprints = set(
        db.scalars(select(DataQualityIssue.fingerprint).where(DataQualityIssue.status == "ignored"))
    )
    db.execute(delete(DataQualityIssue).where(DataQualityIssue.status == "open"))
    fresh_issues = [issue for issue in issues if issue.fingerprint not in ignored_fingerprints]
    db.add_all(fresh_issues)
    db.flush()
    return fresh_issues


def recompute_data_quality(db: Session) -> list[DataQualityIssue]:
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

    holdings = latest_holdings_as_of(db, as_of=today)
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

    for liability in db.scalars(select(Liability).where(Liability.status == "active")):
        if liability.current_balance_cents <= 0:
            issues.append(
                _issue(
                    severity="warning",
                    issue_type="missing_liability_terms",
                    entity_type="liability",
                    entity_id=liability.id,
                    title="Liability is missing a positive balance",
                    description="Debt payoff projections need a current positive balance.",
                    recommended_action="Update the liability balance before relying on payoff projections.",
                )
            )
        terms = db.scalars(
            select(LiabilityTermsHistory)
            .where(LiabilityTermsHistory.liability_id == liability.id)
            .order_by(LiabilityTermsHistory.effective_date.desc())
        ).first()
        if liability.minimum_payment_cents is None and (terms is None or terms.minimum_payment_cents is None):
            issues.append(
                _issue(
                    severity="warning",
                    issue_type="missing_liability_terms",
                    entity_type="liability",
                    entity_id=liability.id,
                    title="Liability is missing payment terms",
                    description="Debt payoff projections need a verified minimum payment.",
                    recommended_action="Add or verify the liability minimum payment.",
                )
            )
        if terms is None or terms.apr_decimal is None:
            issues.append(
                _issue(
                    severity="warning",
                    issue_type="missing_liability_terms",
                    entity_type="liability",
                    entity_id=liability.id,
                    title="Liability is missing APR",
                    description="Payoff projections are estimates until APR is entered and verified.",
                    recommended_action="Add current APR terms for this liability.",
                )
            )
        if not db.scalar(select(DebtPaymentAllocation.id).where(DebtPaymentAllocation.liability_id == liability.id).limit(1)):
            issues.append(
                _issue(
                    severity="info",
                    issue_type="missing_liability_terms",
                    entity_type="liability",
                    entity_id=liability.id,
                    title="Liability is missing payment allocation history",
                    description="Debt payoff projections are estimated until principal, interest, and fee allocations are entered or imported.",
                    recommended_action="Add payment allocations for recent debt payments.",
                )
            )

    for instrument in db.scalars(select(Instrument).where(Instrument.is_active.is_(True))):
        latest_price = db.scalars(
            select(Price).where(Price.instrument_id == instrument.id).order_by(Price.price_date.desc(), Price.created_at.desc())
        ).first()
        if latest_price is None:
            issues.append(
                _issue(
                    severity="warning",
                    issue_type="stale_price",
                    entity_type="instrument",
                    entity_id=instrument.id,
                    title=f"{instrument.symbol} is missing a price",
                    description="No price exists for this active instrument, so holding valuations may be missing or stale.",
                    recommended_action="Enter a manual price or import/refresh prices.",
                )
            )
        else:
            threshold = PRICE_STALE_DAYS.get(instrument.instrument_type, 7)
            if latest_price.price_date and (today - latest_price.price_date).days > threshold:
                issues.append(
                    _issue(
                        severity="warning",
                        issue_type="stale_price",
                        entity_type="instrument",
                        entity_id=instrument.id,
                        title=f"{instrument.symbol} price is stale",
                        description=f"Latest price is from {latest_price.price_date.isoformat()}.",
                        recommended_action="Refresh prices or enter a manual override.",
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

    return _persist_issues_preserving_ignored(db, issues)


def ignore_issue(db: Session, issue: DataQualityIssue) -> DataQualityIssue:
    if issue.fingerprint is None:
        issue.fingerprint = _issue_fingerprint(issue)
    issue.status = "ignored"
    return issue
