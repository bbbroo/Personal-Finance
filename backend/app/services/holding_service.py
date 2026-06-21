from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.money import percent, quantity_times_price_to_cents
from app.models.domain import HoldingSnapshot
from app.schemas.common import HoldingCreate
from app.services.audit_service import record_audit


def create_holding_snapshot(db: Session, payload: HoldingCreate) -> HoldingSnapshot:
    market_value = payload.market_value_cents
    if market_value is None and payload.price_decimal is not None:
        market_value = quantity_times_price_to_cents(payload.quantity_decimal, payload.price_decimal)
    gain = None
    gain_pct = None
    if market_value is not None and payload.cost_basis_cents is not None:
        gain = market_value - payload.cost_basis_cents
        gain_pct = percent(gain, payload.cost_basis_cents)
    confidence = "verified" if payload.cost_basis_quality in {"verified", "user_entered"} else "low"
    holding = HoldingSnapshot(
        account_id=payload.account_id,
        instrument_id=payload.instrument_id,
        snapshot_date=payload.snapshot_date,
        quantity_decimal=payload.quantity_decimal,
        price_decimal=payload.price_decimal,
        market_value_cents=market_value,
        cost_basis_cents=payload.cost_basis_cents,
        unrealized_gain_loss_cents=gain,
        unrealized_gain_loss_pct=gain_pct,
        cost_basis_source=payload.cost_basis_source,
        cost_basis_quality=payload.cost_basis_quality,
        market_value_source="calculated_from_price" if payload.market_value_cents is None else "manual",
        valuation_quality="current" if market_value is not None else "missing",
        confidence=confidence,
        source_type="manual",
        notes=payload.notes,
    )
    db.add(holding)
    db.flush()
    record_audit(db, entity_type="holding", entity_id=holding.id, action="create", after=holding, source="manual")
    return holding
