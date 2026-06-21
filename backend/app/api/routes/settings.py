from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.domain import AppSetting
from app.schemas.common import SettingsPatch
from app.services.serialization import as_dict_list

router = APIRouter(tags=["settings"])


@router.get("/settings")
def settings(db: Session = Depends(get_db)):
    rows = {row.key: row.value_json for row in db.scalars(select(AppSetting))}
    return {
        "app": {
            "version": get_settings().app_version,
            "local_only": True,
            "external_api_use": "disabled_by_default",
            "telemetry": False,
        },
        "settings": rows,
    }


@router.patch("/settings")
def patch_settings(payload: SettingsPatch, db: Session = Depends(get_db)):
    for key, value in payload.settings.items():
        row = db.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, value_json=value if isinstance(value, dict) else {"value": value})
            db.add(row)
        else:
            row.value_json = value if isinstance(value, dict) else {"value": value}
    db.commit()
    return settings(db)


@router.post("/maintenance/vacuum")
def vacuum(db: Session = Depends(get_db)):
    db.execute(text("VACUUM"))
    return {"vacuumed": True}
