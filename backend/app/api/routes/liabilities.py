from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import DebtPaymentAllocation, Liability, LiabilityTermsHistory
from app.repositories.common import get_or_404
from app.schemas.common import DebtPaymentAllocationCreate, LiabilityCreate, LiabilityTermsCreate
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/liabilities", tags=["liabilities"])


def _payoff_projection(balance_cents: int, apr: Decimal, payment_cents: int) -> tuple[int | None, int | None, str | None]:
    balance = Decimal(balance_cents)
    monthly_rate = apr / Decimal("12")
    interest_total = Decimal("0")
    months = 0
    payment = Decimal(payment_cents)
    while balance > 0 and months < 600:
        interest = (balance * monthly_rate).quantize(Decimal("1"))
        interest_total += interest
        principal = payment - interest
        if principal <= 0:
            return None, None, "Payment does not amortize balance"
        balance -= principal
        months += 1
    if balance > 0:
        return None, None, "Projection exceeds 600 months"
    return months, int(interest_total), None


@router.get("")
def liabilities(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(Liability)))


@router.post("")
def create_liability(payload: LiabilityCreate, db: Session = Depends(get_db)):
    row = Liability(**payload.model_dump())
    db.add(row)
    db.commit()
    return as_dict(row)


@router.patch("/{liability_id}")
def update_liability(liability_id: str, payload: dict, db: Session = Depends(get_db)):
    row = get_or_404(db, Liability, liability_id)
    for key, value in payload.items():
        if hasattr(row, key):
            setattr(row, key, value)
    db.commit()
    return as_dict(row)


@router.get("/{liability_id}/terms")
def terms(liability_id: str, db: Session = Depends(get_db)):
    get_or_404(db, Liability, liability_id)
    return as_dict_list(db.scalars(select(LiabilityTermsHistory).where(LiabilityTermsHistory.liability_id == liability_id).order_by(LiabilityTermsHistory.effective_date.desc())))


@router.post("/{liability_id}/terms")
def create_terms(liability_id: str, payload: LiabilityTermsCreate, db: Session = Depends(get_db)):
    get_or_404(db, Liability, liability_id)
    row = LiabilityTermsHistory(liability_id=liability_id, **payload.model_dump())
    db.add(row)
    db.commit()
    return as_dict(row)


@router.get("/payoff-plan")
def payoff_plan(strategy: str = "avalanche", extra_payment_cents: int = 0, db: Session = Depends(get_db)):
    liabilities = list(db.scalars(select(Liability).where(Liability.status == "active")))
    rows = []
    warnings = []
    for liability in liabilities:
        term = db.scalars(
            select(LiabilityTermsHistory).where(LiabilityTermsHistory.liability_id == liability.id).order_by(LiabilityTermsHistory.effective_date.desc())
        ).first()
        minimum_payment = liability.minimum_payment_cents or (term.minimum_payment_cents if term else None)
        apr = Decimal(term.apr_decimal) if term and term.apr_decimal else None
        row_warnings = []
        if apr is None:
            row_warnings.append("Missing APR")
        if minimum_payment is None or minimum_payment <= 0:
            row_warnings.append("Missing minimum payment")
        if row_warnings:
            warnings.append(f"Liability {liability.id}: {', '.join(row_warnings)}; projection confidence is low.")
        projected_months = None
        estimated_interest_cents = None
        if apr is not None and minimum_payment and minimum_payment > 0:
            projected_months, estimated_interest_cents, projection_warning = _payoff_projection(
                liability.current_balance_cents, apr, minimum_payment
            )
            if projection_warning:
                row_warnings.append(projection_warning)
        rows.append(
            {
                "liability_id": liability.id,
                "balance_cents": liability.current_balance_cents,
                "minimum_payment_cents": minimum_payment,
                "apr_decimal": term.apr_decimal if term else None,
                "projected_payoff_months": projected_months,
                "estimated_interest_cents": estimated_interest_cents,
                "projection_quality": "estimated" if row_warnings else "terms_verified",
                "warnings": row_warnings,
                "confidence": "low" if row_warnings else liability.confidence,
            }
        )
    if strategy == "avalanche":
        rows.sort(key=lambda row: row["apr_decimal"] or "0", reverse=True)
    else:
        rows.sort(key=lambda row: row["balance_cents"])
    if extra_payment_cents > 0 and rows:
        target = rows[0]
        if target["apr_decimal"] and target["minimum_payment_cents"]:
            months, interest, projection_warning = _payoff_projection(
                int(target["balance_cents"]),
                Decimal(str(target["apr_decimal"])),
                int(target["minimum_payment_cents"]) + extra_payment_cents,
            )
            target["extra_payment_cents"] = extra_payment_cents
            target["projected_payoff_months_with_extra"] = months
            target["estimated_interest_cents_with_extra"] = interest
            if projection_warning:
                target["warnings"] = list(target["warnings"]) + [projection_warning]
    return {"strategy": strategy, "extra_payment_cents": extra_payment_cents, "rows": rows, "warnings": warnings}


@router.post("/payment-allocation")
def payment_allocation(payload: DebtPaymentAllocationCreate, db: Session = Depends(get_db)):
    row = DebtPaymentAllocation(**payload.model_dump())
    db.add(row)
    db.commit()
    return as_dict(row)
