from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import AccountStatement, ReconciliationRun
from app.repositories.common import get_or_404
from app.schemas.common import StatementCreate
from app.services.reconciliation_service import accept_difference, run_reconciliation
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(tags=["reconciliation"])


@router.get("/account-statements")
def list_statements(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(AccountStatement).order_by(AccountStatement.period_end.desc())))


@router.post("/account-statements")
def create_statement(payload: StatementCreate, db: Session = Depends(get_db)):
    statement = AccountStatement(**payload.model_dump())
    db.add(statement)
    db.commit()
    return as_dict(statement)


@router.get("/account-statements/{statement_id}")
def get_statement(statement_id: str, db: Session = Depends(get_db)):
    return as_dict(get_or_404(db, AccountStatement, statement_id))


@router.patch("/account-statements/{statement_id}")
def update_statement(statement_id: str, payload: dict, db: Session = Depends(get_db)):
    statement = get_or_404(db, AccountStatement, statement_id)
    for key, value in payload.items():
        if hasattr(statement, key):
            setattr(statement, key, value)
    db.commit()
    return as_dict(statement)


@router.post("/reconciliation/run")
def run(payload: dict, db: Session = Depends(get_db)):
    statement_id = payload.get("statement_id") or payload.get("account_statement_id")
    tolerance = int(payload.get("tolerance_cents", 0))
    run = run_reconciliation(db, get_or_404(db, AccountStatement, statement_id), tolerance)
    db.commit()
    return as_dict(run)


@router.get("/reconciliation/{reconciliation_run_id}")
def get_run(reconciliation_run_id: str, db: Session = Depends(get_db)):
    return as_dict(get_or_404(db, ReconciliationRun, reconciliation_run_id))


@router.post("/reconciliation/{reconciliation_run_id}/accept-difference")
def accept(reconciliation_run_id: str, db: Session = Depends(get_db)):
    run = accept_difference(db, get_or_404(db, ReconciliationRun, reconciliation_run_id))
    db.commit()
    return as_dict(run)
