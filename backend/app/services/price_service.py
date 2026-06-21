from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.domain import Instrument, Price


DEFAULT_STALE_DAYS = {
    "crypto": 2,
    "stock": 3,
    "etf": 3,
    "mutual_fund": 3,
}


@dataclass
class PriceRefreshReport:
    status: str
    updated_count: int = 0
    stale_marked_count: int = 0
    missing_count: int = 0
    provider: str = "manual_fallback"
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "provider": self.provider,
            "updated_count": self.updated_count,
            "stale_marked_count": self.stale_marked_count,
            "missing_count": self.missing_count,
            "warnings": self.warnings,
        }


class PriceProvider(Protocol):
    name: str

    def refresh(self, db: Session, as_of: date) -> PriceRefreshReport:
        ...


class ManualFallbackPriceProvider:
    name = "manual_fallback"

    def refresh(self, db: Session, as_of: date) -> PriceRefreshReport:
        report = mark_stale_prices(db, as_of=as_of)
        report.warnings.append(
            "No external price provider is configured; enter manual prices or import a price CSV to refresh values."
        )
        return report


def _latest_price(db: Session, instrument_id: str) -> Price | None:
    return db.scalars(
        select(Price)
        .where(Price.instrument_id == instrument_id)
        .order_by(desc(Price.price_date), desc(Price.created_at))
    ).first()


def mark_stale_prices(db: Session, *, as_of: date | None = None) -> PriceRefreshReport:
    as_of = as_of or date.today()
    report = PriceRefreshReport(status="manual_fallback_required")
    instruments = list(db.scalars(select(Instrument).where(Instrument.is_active.is_(True)).order_by(Instrument.symbol)))
    for instrument in instruments:
        price = _latest_price(db, instrument.id)
        if price is None:
            report.missing_count += 1
            report.warnings.append(f"{instrument.symbol}: missing price.")
            continue
        threshold = DEFAULT_STALE_DAYS.get(instrument.instrument_type, 7)
        if price.price_date and (as_of - price.price_date).days > threshold and price.status not in {"failed", "missing"}:
            price.status = "stale"
            price.confidence = "low"
            report.stale_marked_count += 1
            report.warnings.append(f"{instrument.symbol}: latest price from {price.price_date.isoformat()} is stale.")
    return report


def refresh_prices(db: Session, *, provider_name: str | None = None, as_of: date | None = None) -> PriceRefreshReport:
    as_of = as_of or date.today()
    provider = ManualFallbackPriceProvider()
    if provider_name and provider_name != provider.name:
        report = mark_stale_prices(db, as_of=as_of)
        report.provider = provider_name
        report.warnings.append(
            f"Provider '{provider_name}' is not implemented in this local build; prices were not fetched externally."
        )
        return report
    return provider.refresh(db, as_of)
