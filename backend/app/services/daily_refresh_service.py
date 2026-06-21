from __future__ import annotations

import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import sha256_bytes
from app.models.domain import DailyAppSnapshot, DailyRefreshRun, utc_now
from app.services.backup_service import create_backup
from app.services.data_quality_service import recompute_data_quality
from app.services.price_service import refresh_prices
from app.services.report_service import calculate_net_worth


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
        price_report = refresh_prices(db, as_of=today)
        warnings.extend(price_report.warnings)
        warnings.append("Coinbase sync is not implemented/configured in this local build; no Coinbase data was refreshed.")

        create_backup(db, backup_type="daily", notes="Daily rolling backup on app open")
        net_worth = calculate_net_worth(db, today)
        snapshot_payload = {
            "date": today.isoformat(),
            "net_worth_cents": net_worth["net_worth_cents"],
            "assets_cents": net_worth["assets_cents"],
            "liabilities_cents": net_worth["liabilities_cents"],
            "confidence": net_worth["confidence"],
            "warnings": net_worth["metadata"]["warnings"] + warnings,
        }
        snapshot_hash = sha256_bytes(json.dumps(snapshot_payload, sort_keys=True).encode("utf-8"))
        snapshot = db.scalars(select(DailyAppSnapshot).where(DailyAppSnapshot.snapshot_date == today)).first()
        if snapshot is None:
            snapshot = DailyAppSnapshot(snapshot_date=today, source_hash=snapshot_hash)
            db.add(snapshot)
        snapshot.net_worth_cents = net_worth["net_worth_cents"]
        snapshot.assets_cents = net_worth["assets_cents"]
        snapshot.liabilities_cents = net_worth["liabilities_cents"]
        snapshot.confidence = net_worth["confidence"]
        snapshot.warnings_json = snapshot_payload["warnings"]
        snapshot.source_hash = snapshot_hash

        recompute_data_quality(db)
        run.refreshed_prices = price_report.updated_count > 0
        run.refreshed_coinbase = False
        run.created_snapshot = True
        run.status = "partial" if warnings else "completed"
        run.warnings_json = warnings or None
        run.completed_at = utc_now()
    except Exception as exc:
        run.status = "failed"
        run.errors_json = [str(exc)]
        run.completed_at = utc_now()
    db.flush()
    return run
