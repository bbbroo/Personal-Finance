from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.money import percent, quantity_times_price_to_cents
from app.models.domain import HoldingSnapshot
from app.schemas.common import HoldingCreate
from app.services.audit_service import record_audit
from app.services.serialization import as_dict


def _latest_existing_current(db: Session, account_id: str, instrument_id: str) -> HoldingSnapshot | None:
    return db.scalars(
        select(HoldingSnapshot)
        .where(
            HoldingSnapshot.account_id == account_id,
            HoldingSnapshot.instrument_id == instrument_id,
            HoldingSnapshot.is_current.is_(True),
        )
        .order_by(desc(HoldingSnapshot.snapshot_date), desc(HoldingSnapshot.created_at))
    ).first()


def latest_holdings_as_of(db: Session, account_id: str | None = None, as_of=None) -> list[HoldingSnapshot]:
    query = select(HoldingSnapshot)
    if account_id:
        query = query.where(HoldingSnapshot.account_id == account_id)
    if as_of:
        query = query.where(HoldingSnapshot.snapshot_date <= as_of)
    rows = list(
        db.scalars(
            query.order_by(
                HoldingSnapshot.account_id,
                HoldingSnapshot.instrument_id,
                desc(HoldingSnapshot.snapshot_date),
                desc(HoldingSnapshot.created_at),
            )
        )
    )
    latest: dict[tuple[str, str], HoldingSnapshot] = {}
    for row in rows:
        latest.setdefault((row.account_id, row.instrument_id), row)
    return list(latest.values())


def create_holding_snapshot(db: Session, payload: HoldingCreate) -> HoldingSnapshot:
    same_day = db.scalars(
        select(HoldingSnapshot).where(
            HoldingSnapshot.account_id == payload.account_id,
            HoldingSnapshot.instrument_id == payload.instrument_id,
            HoldingSnapshot.snapshot_date == payload.snapshot_date,
            HoldingSnapshot.is_current.is_(True),
        )
    ).first()
    if same_day and not payload.replace_existing:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "HOLDING_SAME_DATE_REPLACEMENT_REQUIRED",
                "message": "A current holding snapshot already exists for this account, instrument, and date.",
                "details": {
                    "existing_snapshot_id": same_day.id,
                    "account_id": payload.account_id,
                    "instrument_id": payload.instrument_id,
                    "snapshot_date": payload.snapshot_date.isoformat(),
                },
                "recommended_action": "Review the existing snapshot and set replace_existing=true if this row should replace it.",
            },
        )

    existing_current = _latest_existing_current(db, payload.account_id, payload.instrument_id)
    is_current = existing_current is None or payload.snapshot_date >= existing_current.snapshot_date

    market_value = payload.market_value_cents
    if market_value is None and payload.price_decimal is not None:
        market_value = quantity_times_price_to_cents(payload.quantity_decimal, payload.price_decimal)
    gain = None
    gain_pct = None
    if market_value is not None and payload.cost_basis_cents is not None:
        gain = market_value - payload.cost_basis_cents
        gain_pct = percent(gain, payload.cost_basis_cents)
    if payload.cost_basis_cents is None or payload.cost_basis_quality == "missing":
        confidence = "unknown"
    elif payload.cost_basis_quality in {"verified", "user_entered"} and payload.cost_basis_source != "coinbase_api_inferred":
        confidence = "verified"
    else:
        confidence = "low"

    if is_current:
        for previous in list(
            db.scalars(
                select(HoldingSnapshot).where(
                    HoldingSnapshot.account_id == payload.account_id,
                    HoldingSnapshot.instrument_id == payload.instrument_id,
                    HoldingSnapshot.is_current.is_(True),
                    HoldingSnapshot.snapshot_date <= payload.snapshot_date,
                )
            )
        ):
            before = as_dict(previous)
            previous.is_current = False
            record_audit(
                db,
                entity_type="holding",
                entity_id=previous.id,
                action="replace",
                before=before,
                after=previous,
                source="manual",
            )

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
        is_current=is_current,
        replaces_snapshot_id=same_day.id if same_day and payload.replace_existing else None,
        notes=payload.notes,
    )
    db.add(holding)
    db.flush()
    record_audit(db, entity_type="holding", entity_id=holding.id, action="create", after=holding, source="manual")
    return holding
