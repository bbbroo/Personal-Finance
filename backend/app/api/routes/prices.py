from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import Price, utc_now
from app.schemas.common import ManualPriceCreate
from app.services.audit_service import record_audit
from app.services.price_service import refresh_prices as refresh_prices_service
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("")
def prices(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(Price).order_by(Price.price_date.desc())))


@router.post("/refresh")
def refresh_prices(provider: str | None = None, db: Session = Depends(get_db)):
    report = refresh_prices_service(db, provider_name=provider)
    db.commit()
    return report.as_dict()


@router.post("/manual")
def manual_price(payload: ManualPriceCreate, db: Session = Depends(get_db)):
    price = Price(
        instrument_id=payload.instrument_id,
        price_date=payload.price_date,
        price_decimal=payload.price_decimal,
        provider=payload.provider,
        provider_symbol=payload.provider_symbol,
        status=payload.status,
        confidence=payload.confidence,
        source_type="manual",
        market_session=payload.market_session,
        fetched_at=utc_now(),
    )
    db.add(price)
    db.flush()
    record_audit(db, entity_type="price", entity_id=price.id, action="create", after=price)
    db.commit()
    return as_dict(price)
