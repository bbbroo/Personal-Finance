from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import DebtPaymentAllocation, Liability, LiabilityTermsHistory


MAX_PROJECTION_MONTHS = 600


def payoff_projection(balance_cents: int, apr: Decimal, payment_cents: int) -> tuple[int | None, int | None, str | None]:
    balance = Decimal(balance_cents)
    monthly_rate = apr / Decimal("12")
    interest_total = Decimal("0")
    months = 0
    payment = Decimal(payment_cents)
    while balance > 0 and months < MAX_PROJECTION_MONTHS:
        interest = (balance * monthly_rate).quantize(Decimal("1"))
        interest_total += interest
        principal = payment - interest
        if principal <= 0:
            return None, None, "Payment does not amortize balance"
        balance -= principal
        months += 1
    if balance > 0:
        return None, None, f"Projection exceeds {MAX_PROJECTION_MONTHS} months"
    return months, int(interest_total), None


def effective_terms(db: Session, liability_id: str, as_of: date) -> LiabilityTermsHistory | None:
    return db.scalars(
        select(LiabilityTermsHistory)
        .where(
            LiabilityTermsHistory.liability_id == liability_id,
            LiabilityTermsHistory.effective_date <= as_of,
        )
        .order_by(LiabilityTermsHistory.effective_date.desc())
    ).first()


def effective_apr(term: LiabilityTermsHistory | None, as_of: date) -> tuple[str | None, str]:
    if term is None:
        return None, "missing"
    if term.promo_apr_decimal is not None and term.promo_end_date is not None and term.promo_end_date >= as_of:
        return term.promo_apr_decimal, "promo"
    return term.apr_decimal, "standard"


def _allocation_summary(db: Session, liability_id: str) -> dict[str, Any]:
    allocations = list(db.scalars(select(DebtPaymentAllocation).where(DebtPaymentAllocation.liability_id == liability_id)))
    return {
        "principal_cents": sum(item.principal_cents or 0 for item in allocations),
        "interest_cents": sum(item.interest_cents or 0 for item in allocations),
        "fee_cents": sum(item.fee_cents or 0 for item in allocations),
        "allocation_count": len(allocations),
        "has_estimated_allocations": any(item.is_estimated for item in allocations),
    }


def _base_row(db: Session, liability: Liability, as_of: date) -> dict[str, Any]:
    term = effective_terms(db, liability.id, as_of)
    minimum_payment = (term.minimum_payment_cents if term and term.minimum_payment_cents is not None else None) or liability.minimum_payment_cents
    apr_raw, apr_source = effective_apr(term, as_of)
    apr = Decimal(apr_raw) if apr_raw else None
    row_warnings: list[str] = []
    if liability.current_balance_cents <= 0:
        row_warnings.append("Missing or non-positive balance")
    if apr is None:
        row_warnings.append("Missing APR")
    if minimum_payment is None or minimum_payment <= 0:
        row_warnings.append("Missing minimum payment")
    allocation_summary = _allocation_summary(db, liability.id)
    if allocation_summary["allocation_count"] == 0:
        row_warnings.append("Missing payment allocation history")
    elif allocation_summary["has_estimated_allocations"]:
        row_warnings.append("Payment allocation history includes estimates")

    projected_months = None
    estimated_interest_cents = None
    if apr is not None and minimum_payment and minimum_payment > 0 and liability.current_balance_cents > 0:
        projected_months, estimated_interest_cents, projection_warning = payoff_projection(
            liability.current_balance_cents, apr, minimum_payment
        )
        if projection_warning:
            row_warnings.append(projection_warning)

    return {
        "liability_id": liability.id,
        "balance_cents": liability.current_balance_cents,
        "minimum_payment_cents": minimum_payment,
        "extra_payment_cents": 0,
        "total_payment_cents": minimum_payment,
        "apr_decimal": apr_raw,
        "apr_source": apr_source,
        "effective_terms_id": term.id if term else None,
        "allocation_summary": allocation_summary,
        "projected_payoff_months": projected_months,
        "estimated_interest_cents": estimated_interest_cents,
        "projection_quality": "estimated" if row_warnings else "terms_verified",
        "warnings": row_warnings,
        "confidence": "low" if row_warnings else liability.confidence,
        "confidence_explanation": "Low confidence because payoff inputs are missing or estimated." if row_warnings else "Terms, payment, and allocation inputs are available.",
    }


def _sort_rows(rows: list[dict[str, Any]], strategy: str) -> list[dict[str, Any]]:
    sorted_rows = list(rows)
    if strategy == "avalanche":
        sorted_rows.sort(key=lambda row: Decimal(str(row["apr_decimal"] or "0")), reverse=True)
    else:
        sorted_rows.sort(key=lambda row: row["balance_cents"])
    for index, row in enumerate(sorted_rows, start=1):
        row["payoff_order"] = index
    return sorted_rows


def _apply_extra_payment(row: dict[str, Any], extra_payment_cents: int) -> None:
    if extra_payment_cents <= 0:
        return
    if not row.get("apr_decimal") or not row.get("minimum_payment_cents"):
        return
    payment_with_extra = int(row["minimum_payment_cents"]) + extra_payment_cents
    months, interest, projection_warning = payoff_projection(
        int(row["balance_cents"]),
        Decimal(str(row["apr_decimal"])),
        payment_with_extra,
    )
    row["extra_payment_cents"] = extra_payment_cents
    row["total_payment_cents"] = payment_with_extra
    row["projected_payoff_months_with_extra"] = months
    row["estimated_interest_cents_with_extra"] = interest
    if projection_warning:
        row["warnings"] = list(row["warnings"]) + [projection_warning]
        row["confidence"] = "low"


def _summarize_rows(strategy: str, rows: list[dict[str, Any]], extra_payment_cents: int) -> dict[str, Any]:
    months_values = [row.get("projected_payoff_months_with_extra") or row.get("projected_payoff_months") for row in rows]
    interest_values = [row.get("estimated_interest_cents_with_extra") or row.get("estimated_interest_cents") for row in rows]
    known_months = [value for value in months_values if value is not None]
    known_interest = [value for value in interest_values if value is not None]
    low_confidence_count = sum(1 for row in rows if row.get("confidence") == "low")
    return {
        "strategy": strategy,
        "extra_payment_cents": extra_payment_cents,
        "payoff_order": [row["liability_id"] for row in rows],
        "total_projected_months": max(known_months) if known_months else None,
        "total_estimated_interest_cents": sum(known_interest) if known_interest else None,
        "low_confidence_liability_count": low_confidence_count,
        "confidence": "low" if low_confidence_count else "medium",
        "confidence_explanation": "One or more liabilities have missing or estimated payoff inputs." if low_confidence_count else "All liabilities have usable payoff inputs.",
    }


def build_payoff_plan(
    db: Session,
    *,
    strategy: str = "avalanche",
    extra_payment_cents: int = 0,
    as_of: date | None = None,
) -> dict[str, Any]:
    as_of = as_of or date.today()
    liabilities = list(db.scalars(select(Liability).where(Liability.status == "active")))
    base_rows = [_base_row(db, liability, as_of) for liability in liabilities]
    requested_rows = _sort_rows(base_rows, strategy)
    if requested_rows:
        _apply_extra_payment(requested_rows[0], extra_payment_cents)
    warnings = [
        f"Liability {row['liability_id']}: {', '.join(row['warnings'])}; projection confidence is low."
        for row in requested_rows
        if row["warnings"]
    ]

    comparison: dict[str, Any] = {}
    for comparison_strategy in ["avalanche", "snowball"]:
        comparison_rows = _sort_rows([dict(row, warnings=list(row["warnings"])) for row in base_rows], comparison_strategy)
        if comparison_rows:
            _apply_extra_payment(comparison_rows[0], extra_payment_cents)
        comparison[comparison_strategy] = _summarize_rows(comparison_strategy, comparison_rows, extra_payment_cents)

    summary = _summarize_rows(strategy, requested_rows, extra_payment_cents)
    return {
        "strategy": strategy,
        "extra_payment_cents": extra_payment_cents,
        "rows": requested_rows,
        "warnings": warnings,
        "summary": summary,
        "comparison": comparison,
        "estimated": True,
    }
