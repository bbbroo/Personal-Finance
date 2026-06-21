from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import DataQualityIssue
from app.repositories.common import get_or_404
from app.services.data_quality_service import ignore_issue, recompute_data_quality
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


@router.get("/issues")
def issues(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(DataQualityIssue).order_by(DataQualityIssue.created_at.desc())))


@router.post("/issues/{issue_id}/ignore")
def ignore(issue_id: str, db: Session = Depends(get_db)):
    issue = ignore_issue(db, get_or_404(db, DataQualityIssue, issue_id))
    db.commit()
    return as_dict(issue)


@router.post("/recompute")
def recompute(db: Session = Depends(get_db)):
    rows = recompute_data_quality(db)
    db.commit()
    return as_dict_list(rows)
