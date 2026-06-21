from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import AppSetting, DailyRefreshRun
from app.schemas.common import CoinbaseConfigure
from app.services.serialization import as_dict_list

router = APIRouter(prefix="/coinbase", tags=["coinbase"])


@router.get("/status")
def status(db: Session = Depends(get_db)):
    row = db.get(AppSetting, "coinbase")
    configured = bool(row and row.value_json.get("api_key_configured"))
    return {
        "configured": configured,
        "read_only_required": True,
        "cost_basis_policy": "Coinbase API cost basis is incomplete unless a tax/report export is imported or manually verified.",
    }


@router.post("/configure")
def configure(payload: CoinbaseConfigure, db: Session = Depends(get_db)):
    if not payload.read_only_confirmed:
        raise HTTPException(status_code=422, detail="Only read-only Coinbase API permissions are allowed.")
    row = db.get(AppSetting, "coinbase")
    if row is None:
        row = AppSetting(key="coinbase", value_json=payload.model_dump())
        db.add(row)
    else:
        row.value_json = payload.model_dump()
    db.commit()
    return status(db)


@router.delete("/configure")
def delete_config(db: Session = Depends(get_db)):
    row = db.get(AppSetting, "coinbase")
    if row:
        db.delete(row)
        db.commit()
    return {"configured": False}


@router.post("/sync")
def sync(db: Session = Depends(get_db)):
    return {
        "status": "not_configured_or_manual_only",
        "synced": False,
        "warnings": ["Coinbase sync is read-only and disabled until local API credentials are configured."],
    }


@router.get("/sync-runs")
def sync_runs(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(DailyRefreshRun).where(DailyRefreshRun.refreshed_coinbase.is_(True))))
