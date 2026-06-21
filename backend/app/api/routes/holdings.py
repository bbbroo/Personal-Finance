from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import HoldingSnapshot
from app.schemas.common import HoldingCreate
from app.services.holding_service import create_holding_snapshot
from app.services.report_service import asset_allocation
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(tags=["holdings"])


@router.get("/holdings")
def holdings(db: Session = Depends(get_db)):
    return as_dict_list(
        db.scalars(select(HoldingSnapshot).where(HoldingSnapshot.is_current.is_(True)).order_by(HoldingSnapshot.snapshot_date.desc()))
    )


@router.post("/holdings/manual-snapshot")
def manual_snapshot(payload: HoldingCreate, db: Session = Depends(get_db)):
    holding = create_holding_snapshot(db, payload)
    db.commit()
    return as_dict(holding)


@router.get("/holdings/history")
def history(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(HoldingSnapshot).order_by(HoldingSnapshot.snapshot_date.desc())))


@router.get("/allocation")
def allocation(db: Session = Depends(get_db)):
    return asset_allocation(db)


@router.post("/allocation/overrides")
def create_override(payload: dict, db: Session = Depends(get_db)):
    from app.models.domain import SymbolAllocationOverride

    row = SymbolAllocationOverride(**payload)
    db.add(row)
    db.commit()
    return as_dict(row)


@router.patch("/allocation/overrides/{override_id}")
def update_override(override_id: str, payload: dict, db: Session = Depends(get_db)):
    from app.models.domain import SymbolAllocationOverride
    from app.repositories.common import get_or_404

    row = get_or_404(db, SymbolAllocationOverride, override_id)
    for key, value in payload.items():
        if hasattr(row, key):
            setattr(row, key, value)
    db.commit()
    return as_dict(row)
