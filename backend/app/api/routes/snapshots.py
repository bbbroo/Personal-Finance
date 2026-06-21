from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import AccountBalanceSnapshot, HoldingSnapshot
from app.services.serialization import as_dict_list

router = APIRouter(prefix="/snapshots", tags=["snapshots"])


@router.get("/balances")
def balance_snapshots(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(AccountBalanceSnapshot).order_by(AccountBalanceSnapshot.snapshot_date.desc())))


@router.get("/holdings")
def holding_snapshots(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(HoldingSnapshot).order_by(HoldingSnapshot.snapshot_date.desc())))
