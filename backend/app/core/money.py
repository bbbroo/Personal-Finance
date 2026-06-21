from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, getcontext

getcontext().prec = 28

CENTS = Decimal("100")


class MoneyError(ValueError):
    pass


def parse_decimal(value: str | int | Decimal | None, *, allow_none: bool = False) -> Decimal | None:
    if value is None or value == "":
        if allow_none:
            return None
        raise MoneyError("Missing decimal value cannot be treated as zero.")
    if isinstance(value, Decimal):
        return value
    try:
        cleaned = str(value).strip().replace("$", "").replace(",", "")
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = f"-{cleaned[1:-1]}"
        return Decimal(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise MoneyError(f"Invalid decimal value: {value}") from exc


def dollars_to_cents(value: str | int | Decimal | None, *, allow_none: bool = False) -> int | None:
    decimal_value = parse_decimal(value, allow_none=allow_none)
    if decimal_value is None:
        return None
    return int((decimal_value * CENTS).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def cents_to_dollars(cents: int | None) -> str | None:
    if cents is None:
        return None
    return str((Decimal(cents) / CENTS).quantize(Decimal("0.01")))


def decimal_to_string(value: Decimal | str | int | None, *, allow_none: bool = False) -> str | None:
    decimal_value = parse_decimal(value, allow_none=allow_none)
    if decimal_value is None:
        return None
    return format(decimal_value.normalize(), "f")


def quantity_times_price_to_cents(quantity: str, price: str) -> int:
    quantity_decimal = parse_decimal(quantity)
    price_decimal = parse_decimal(price)
    assert quantity_decimal is not None
    assert price_decimal is not None
    return int((quantity_decimal * price_decimal * CENTS).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def percent(numerator: int | None, denominator: int | None) -> str | None:
    if numerator is None or denominator in (None, 0):
        return None
    return decimal_to_string((Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001")))


def sum_known(values: list[int | None]) -> int | None:
    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)
