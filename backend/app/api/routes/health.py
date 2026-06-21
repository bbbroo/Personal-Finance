from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.services.daily_refresh_service import run_daily_refresh
from app.services.serialization import as_dict

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "app": get_settings().app_name, "version": get_settings().app_version}


@router.get("/app/status")
def app_status():
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "local_only": True,
        "cloud_backend": False,
        "auth_required": False,
        "background_scheduler": False,
    }


@router.post("/daily-refresh")
def daily_refresh(force: bool = False, db: Session = Depends(get_db)):
    run = run_daily_refresh(db, force=force)
    db.commit()
    return as_dict(run)
