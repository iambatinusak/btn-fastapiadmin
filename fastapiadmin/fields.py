"""SQLAlchemy column type → HTML field mapping."""
from __future__ import annotations

import sqlalchemy as sa
from datetime import datetime, date


_TYPE_MAP = {
    sa.String: ("text", False),
    sa.VARCHAR: ("text", False),
    sa.Text: ("textarea", False),
    sa.UnicodeText: ("textarea", False),
    sa.Integer: ("number", False),
    sa.BigInteger: ("number", False),
    sa.SmallInteger: ("number", False),
    sa.Float: ("number_float", False),
    sa.Numeric: ("number_float", False),
    sa.Boolean: ("checkbox", False),
    sa.DateTime: ("datetime-local", False),
    sa.Date: ("date", False),
    sa.Time: ("time", False),
    sa.JSON: ("json", False),
    sa.Enum: ("select", False),
}


def get_field_info(column: sa.Column) -> dict:
    """Return HTML rendering info for a SQLAlchemy column."""
    col_type = type(column.type)
    input_type = "text"
    is_textarea = False
    is_checkbox = False
    is_select = False
    select_choices: list[str] = []
    step = None

    for sa_type, (html_type, _) in _TYPE_MAP.items():
        if issubclass(col_type, sa_type):
            input_type = html_type
            break

    if input_type == "textarea":
        is_textarea = True
        input_type = "text"
    elif input_type == "checkbox":
        is_checkbox = True
    elif input_type == "number_float":
        input_type = "number"
        step = "any"
    elif input_type == "json":
        is_textarea = True
        input_type = "text"
    elif input_type == "select":
        is_select = True
        if hasattr(column.type, "enums"):
            select_choices = list(column.type.enums)

    nullable = column.nullable if column.nullable is not None else True

    return {
        "name": column.name,
        "input_type": input_type,
        "is_textarea": is_textarea,
        "is_checkbox": is_checkbox,
        "is_select": is_select,
        "select_choices": select_choices,
        "required": not nullable and not column.default and not column.server_default,
        "step": step,
    }


def coerce_value(value: str | None, column: sa.Column):
    """Coerce a form string value to the appropriate Python type."""
    if value is None or value == "":
        return None

    col_type = type(column.type)

    for sa_type in (sa.Integer, sa.BigInteger, sa.SmallInteger):
        if issubclass(col_type, sa_type):
            return int(value)

    for sa_type in (sa.Float, sa.Numeric):
        if issubclass(col_type, sa_type):
            return float(value)

    if issubclass(col_type, sa.Boolean):
        return value.lower() in ("1", "true", "on", "yes")

    if issubclass(col_type, sa.DateTime):
        value = value.replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    if issubclass(col_type, sa.Date):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    return value


def format_cell(value) -> str:
    """Format a value for display in a table cell."""
    if value is None:
        return '<span style="color:var(--text-muted)">—</span>'
    if isinstance(value, bool):
        if value:
            return '<span class="badge badge-green">Yes</span>'
        return '<span class="badge badge-red">No</span>'
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    text = str(value)
    if len(text) > 60:
        return text[:57] + "…"
    return text
