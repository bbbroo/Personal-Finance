from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session


def get_or_404(db: Session, model, record_id: str):
    item = db.get(model, record_id)
    if item is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return item


def list_ordered(db: Session, model, order_by):
    return db.scalars(select(model).order_by(order_by)).all()
