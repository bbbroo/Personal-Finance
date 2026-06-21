from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import DebtPaymentAllocation, Liability, LiabilityTermsHistory
from app.repositories.common import get_or_404
from app.schemas.common import DebtPaymentAllocationCreate, LiabilityCreate, LiabilityTermsCreate
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/liabilities", tags=["liabilities"])


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
        if term is None or term.apr_decimal is None:
            warnings.append(f"Liability {liability.id} is missing APR; projection confidence is low.")
        rows.append(
            {
                "liability_id": liability.id,
                "balance_cents": liability.current_balance_cents,
                "minimum_payment_cents": liability.minimum_payment_cents,
                "apr_decimal": term.apr_decimal if term else None,
                "confidence": "low" if term is None or term.apr_decimal is None else liability.confidence,
            }
        )
    if strategy == "avalanche":
        rows.sort(key=lambda row: row["apr_decimal"] or "0", reverse=True)
    else:
        rows.sort(key=lambda row: row["balance_cents"])
    return {"strategy": strategy, "extra_payment_cents": extra_payment_cents, "rows": rows, "warnings": warnings}


@router.post("/payment-allocation")
def payment_allocation(payload: DebtPaymentAllocationCreate, db: Session = Depends(get_db)):
    row = DebtPaymentAllocation(**payload.model_dump())
    db.add(row)
    db.commit()
    return as_dict(row)
