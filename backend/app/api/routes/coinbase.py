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
    return {
        "implemented": False,
        "configured": False,
        "stored_local_preferences": bool(row),
        "read_only_required": True,
        "sync_available": False,
        "message": "Coinbase credentialed sync is not implemented in V1. Do not enter private keys, seed phrases, or write-enabled credentials.",
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
    result = status(db)
    result["warnings"] = [
        "Preference saved, but Coinbase sync remains not implemented; no external Coinbase data will be fetched."
    ]
    return result


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
        "status": "not_implemented",
        "synced": False,
        "warnings": [
            "Coinbase sync is not implemented in this V1 build. Use CSV/manual imports; cost basis remains incomplete until verified."
        ],
    }


@router.get("/sync-runs")
def sync_runs(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(DailyRefreshRun).where(DailyRefreshRun.refreshed_coinbase.is_(True))))
