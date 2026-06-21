from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.report_service import (
    asset_allocation,
    cash_flow,
    dashboard,
    net_worth_history,
    spending_by_category,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard")
def dashboard_report(db: Session = Depends(get_db)):
    return dashboard(db)


@router.get("/net-worth")
def net_worth(as_of: date | None = None, db: Session = Depends(get_db)):
    from app.services.report_service import calculate_net_worth

    return {"current": calculate_net_worth(db, as_of), "history": net_worth_history(db)}


@router.get("/cash-flow")
def cash_flow_report(start_date: date, end_date: date, db: Session = Depends(get_db)):
    return cash_flow(db, start_date, end_date)


@router.get("/spending-by-category")
def spending(start_date: date, end_date: date, db: Session = Depends(get_db)):
    return spending_by_category(db, start_date, end_date)


@router.get("/account-balances")
def account_balances(db: Session = Depends(get_db)):
    from app.models.domain import AccountBalanceSnapshot
    from app.services.serialization import as_dict_list
    from sqlalchemy import select

    return as_dict_list(db.scalars(select(AccountBalanceSnapshot).order_by(AccountBalanceSnapshot.snapshot_date)))


@router.get("/investment-value")
def investment_value(db: Session = Depends(get_db)):
    report = dashboard(db)
    return {
        "history": report["history"],
        "current_investments_cents": report["cards"]["investments_total_cents"],
        "confidence": report["net_worth"]["confidence"],
    }


@router.get("/allocation")
def allocation_report(mode: str = "investment_only", as_of: date | None = None, db: Session = Depends(get_db)):
    return asset_allocation(db, as_of=as_of, mode=mode)
