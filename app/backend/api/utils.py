from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect


def to_dict(instance: Any) -> dict[str, Any]:
    data = {}
    for column in inspect(instance).mapper.column_attrs:
        value = getattr(instance, column.key)
        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        data[column.key] = value
    return data


def list_rows(rows: list[Any]) -> list[dict[str, Any]]:
    return [to_dict(row) for row in rows]
