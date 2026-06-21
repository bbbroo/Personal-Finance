from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import DailyRefreshRun, Price, utc_now
from app.services.backup_service import create_backup
from app.services.data_quality_service import recompute_data_quality


def run_daily_refresh(db: Session, *, force: bool = False) -> DailyRefreshRun:
    today = date.today()
    existing = db.scalars(select(DailyRefreshRun).where(DailyRefreshRun.run_date == today)).first()
    if existing and not force:
        return existing
    run = existing or DailyRefreshRun(run_date=today)
    db.add(run)
    run.status = "running"
    run.started_at = utc_now()
    warnings: list[str] = []
    try:
        if not db.scalars(select(Price).where(Price.price_date == today)).first():
            warnings.append("No automatic market data provider configured; manual prices remain unchanged.")
        create_backup(db, backup_type="daily", notes="Daily rolling backup on app open")
        recompute_data_quality(db)
        run.refreshed_prices = False
        run.refreshed_coinbase = False
        run.created_snapshot = False
        run.status = "partial" if warnings else "completed"
        run.warnings_json = warnings or None
        run.completed_at = utc_now()
    except Exception as exc:
        run.status = "failed"
        run.errors_json = [str(exc)]
        run.completed_at = utc_now()
    db.flush()
    return run
