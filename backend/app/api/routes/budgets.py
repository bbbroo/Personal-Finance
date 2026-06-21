from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import BudgetCategoryPlan, BudgetPeriod, RolloverLedger, SinkingFund
from app.repositories.common import get_or_404
from app.schemas.common import BudgetPeriodCreate, BudgetPlanCreate, RolloverAdjust, SinkingFundCreate
from app.services.budget_service import budget_summary, close_period, sinking_fund_summary
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(tags=["budgets"])


@router.get("/budget-periods")
def periods(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(BudgetPeriod).order_by(BudgetPeriod.start_date.desc())))


@router.post("/budget-periods")
def create_period(payload: BudgetPeriodCreate, db: Session = Depends(get_db)):
    period = BudgetPeriod(**payload.model_dump())
    db.add(period)
    db.commit()
    return as_dict(period)


@router.patch("/budget-periods/{period_id}")
def update_period(period_id: str, payload: dict, db: Session = Depends(get_db)):
    period = get_or_404(db, BudgetPeriod, period_id)
    for key, value in payload.items():
        if hasattr(period, key):
            setattr(period, key, value)
    db.commit()
    return as_dict(period)


@router.post("/budget-periods/{period_id}/close")
def close(period_id: str, db: Session = Depends(get_db)):
    period = close_period(db, get_or_404(db, BudgetPeriod, period_id))
    db.commit()
    return as_dict(period)


@router.get("/budgets")
def budgets(db: Session = Depends(get_db)):
    return budget_summary(db)


@router.post("/budgets")
def create_budget(payload: BudgetPlanCreate, db: Session = Depends(get_db)):
    plan = BudgetCategoryPlan(**payload.model_dump())
    db.add(plan)
    db.commit()
    return as_dict(plan)


@router.patch("/budgets/{budget_plan_id}")
def update_budget(budget_plan_id: str, payload: dict, db: Session = Depends(get_db)):
    plan = get_or_404(db, BudgetCategoryPlan, budget_plan_id)
    for key, value in payload.items():
        if hasattr(plan, key):
            setattr(plan, key, value)
    db.commit()
    return as_dict(plan)


@router.get("/rollovers")
def rollovers(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(RolloverLedger)))


@router.post("/rollovers/adjust")
def adjust_rollover(payload: RolloverAdjust, db: Session = Depends(get_db)):
    ledger = db.scalars(
        select(RolloverLedger).where(
            RolloverLedger.category_id == payload.category_id,
            RolloverLedger.budget_period_id == payload.budget_period_id,
        )
    ).first()
    if ledger is None:
        ledger = RolloverLedger(category_id=payload.category_id, budget_period_id=payload.budget_period_id)
        db.add(ledger)
    ledger.adjustment_cents += payload.adjustment_cents
    db.commit()
    return as_dict(ledger)


@router.get("/sinking-funds")
def sinking_funds(db: Session = Depends(get_db)):
    return [sinking_fund_summary(fund) for fund in db.scalars(select(SinkingFund))]


@router.post("/sinking-funds")
def create_sinking_fund(payload: SinkingFundCreate, db: Session = Depends(get_db)):
    fund = SinkingFund(**payload.model_dump())
    db.add(fund)
    db.commit()
    return as_dict(fund)


@router.patch("/sinking-funds/{fund_id}")
def update_sinking_fund(fund_id: str, payload: dict, db: Session = Depends(get_db)):
    fund = get_or_404(db, SinkingFund, fund_id)
    for key, value in payload.items():
        if hasattr(fund, key):
            setattr(fund, key, value)
    db.commit()
    return as_dict(fund)
