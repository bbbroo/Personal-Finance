from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.inspection import inspect


def as_dict(model) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in inspect(model).mapper.column_attrs:
        value = getattr(model, column.key)
        if isinstance(value, (datetime, date)):
            data[column.key] = value.isoformat()
        elif isinstance(value, Decimal):
            data[column.key] = str(value)
        else:
            data[column.key] = value
    return data


def as_dict_list(models) -> list[dict[str, Any]]:
    return [as_dict(model) for model in models]
