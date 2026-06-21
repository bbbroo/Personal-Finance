from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import Instrument
from app.repositories.common import get_or_404
from app.schemas.common import InstrumentCreate
from app.services.audit_service import record_audit
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("")
def list_instruments(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(Instrument).order_by(Instrument.symbol)))


@router.post("")
def create_instrument(payload: InstrumentCreate, db: Session = Depends(get_db)):
    row = Instrument(**payload.model_dump())
    db.add(row)
    db.flush()
    record_audit(db, entity_type="instrument", entity_id=row.id, action="create", after=row)
    db.commit()
    return as_dict(row)


@router.patch("/{instrument_id}")
def update_instrument(instrument_id: str, payload: dict, db: Session = Depends(get_db)):
    row = get_or_404(db, Instrument, instrument_id)
    before = as_dict(row)
    for key, value in payload.items():
        if hasattr(row, key):
            setattr(row, key, value)
    record_audit(db, entity_type="instrument", entity_id=row.id, action="update", before=before, after=row)
    db.commit()
    return as_dict(row)
