from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.monthly_review_service import build_review, finalize_review, regenerate_review
from app.services.serialization import as_dict

router = APIRouter(prefix="/monthly-review", tags=["monthly-review"])


@router.get("/{yyyy_mm}")
def get_review(yyyy_mm: str, db: Session = Depends(get_db)):
    return build_review(db, yyyy_mm)


@router.post("/{yyyy_mm}/finalize")
def finalize(yyyy_mm: str, db: Session = Depends(get_db)):
    row = finalize_review(db, yyyy_mm)
    db.commit()
    return as_dict(row)


@router.post("/{yyyy_mm}/regenerate")
def regenerate(yyyy_mm: str, db: Session = Depends(get_db)):
    row = regenerate_review(db, yyyy_mm)
    db.commit()
    return as_dict(row)
