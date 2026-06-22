from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.domain import BackupManifest, DataQualityIssue, ImportBatch, MonthlyReviewSnapshot, Price
from app.services.debt_payoff_service import build_payoff_plan
from app.services.monthly_review_service import build_review
from app.services.report_service import calculate_net_worth, cash_flow


def build_trust_checklist(db: Session, *, as_of: date | None = None) -> dict[str, Any]:
    as_of = as_of or date.today()
    month_start = as_of.replace(day=1)
    yyyy_mm = f"{as_of.year:04d}-{as_of.month:02d}"

    latest_backup = db.scalars(select(BackupManifest).order_by(desc(BackupManifest.created_at))).first()
    latest_import = db.scalars(select(ImportBatch).order_by(desc(ImportBatch.created_at))).first()
    open_issue_count = db.scalar(select(func.count()).select_from(DataQualityIssue).where(DataQualityIssue.status == "open"))
    ignored_issue_count = db.scalar(select(func.count()).select_from(DataQualityIssue).where(DataQualityIssue.status == "ignored"))
    stale_price_count = db.scalar(select(func.count()).select_from(Price).where(Price.status.in_(["stale", "missing", "failed"])))

    net_worth = calculate_net_worth(db, as_of)
    flow = cash_flow(db, month_start, as_of)
    debt = build_payoff_plan(db)
    monthly_review = build_review(db, yyyy_mm)
    latest_review = db.scalars(select(MonthlyReviewSnapshot).order_by(desc(MonthlyReviewSnapshot.created_at))).first()

    checks = {
        "last_successful_backup": {
            "status": "ok" if latest_backup else "missing",
            "created_at": latest_backup.created_at.isoformat() if latest_backup else None,
            "backup_type": latest_backup.backup_type if latest_backup else None,
            "backup_path": latest_backup.backup_path if latest_backup else None,
        },
        "last_import_commit": {
            "status": latest_import.status if latest_import else "none",
            "created_at": latest_import.created_at.isoformat() if latest_import else None,
            "committed_at": latest_import.committed_at.isoformat() if latest_import and latest_import.committed_at else None,
            "filename": latest_import.original_filename if latest_import else None,
        },
        "data_quality": {
            "status": "warning" if open_issue_count else "ok",
            "open_issue_count": open_issue_count or 0,
            "ignored_issue_count": ignored_issue_count or 0,
        },
        "prices": {
            "status": "warning" if stale_price_count else "ok",
            "stale_price_count": stale_price_count or 0,
        },
        "reconciliation": {
            "status": "warning" if net_worth["metadata"]["unreconciled_account_count"] else "ok",
            "unreconciled_account_count": net_worth["metadata"]["unreconciled_account_count"],
        },
        "monthly_review": {
            "status": "warning" if monthly_review["source_changed_since_finalization"] else "ok",
            "review_month": yyyy_mm,
            "latest_review_month": latest_review.review_month if latest_review else None,
            "source_changed_since_finalization": monthly_review["source_changed_since_finalization"],
        },
        "debt_payoff": {
            "status": "warning" if debt["summary"]["confidence"] == "low" else "ok",
            "confidence": debt["summary"]["confidence"],
            "confidence_explanation": debt["summary"]["confidence_explanation"],
            "low_confidence_liability_count": debt["summary"]["low_confidence_liability_count"],
        },
        "net_worth": {
            "status": "warning" if net_worth["confidence"] in {"low", "unknown"} else "ok",
            "confidence": net_worth["confidence"],
            "warning_count": len(net_worth["metadata"]["warnings"]),
        },
        "cash_flow": {
            "status": "warning" if flow["confidence"] in {"low", "unknown"} else "ok",
            "confidence": flow["confidence"],
            "warning_count": len(flow["warnings"]),
        },
    }
    warning_count = sum(1 for check in checks.values() if check["status"] not in {"ok", "committed"})
    return {
        "as_of": as_of.isoformat(),
        "overall_status": "warning" if warning_count else "ok",
        "warning_count": warning_count,
        "checks": checks,
    }
