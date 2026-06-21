from __future__ import annotations

import pytest

from app.core.money import MoneyError, dollars_to_cents, quantity_times_price_to_cents


def test_money_uses_cents_and_decimal_math():
    assert dollars_to_cents("0.10") + dollars_to_cents("0.20") == 30
    assert dollars_to_cents("($1,234.565)") == -123457
    assert quantity_times_price_to_cents("0.175", "65000") == 1137500


def test_missing_money_is_not_zero():
    with pytest.raises(MoneyError):
        dollars_to_cents(None)
    assert dollars_to_cents(None, allow_none=True) is None
