"""Query parameter parsing utilities."""

from datetime import date, datetime


def parse_int_param(value: str | None) -> int | None:
    """Parse string to int, returning None for empty/invalid values."""
    if not value:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def parse_bool_param(value: str | None) -> bool | None:
    """
    Parse string to bool, returning None for empty values.

    Accepts: "true"/"false", "1"/"0", "yes"/"no"
    """
    if not value:
        return None
    lower = value.lower()
    if lower in ("true", "1", "yes"):
        return True
    if lower in ("false", "0", "no"):
        return False
    return None


def parse_date_param(value: str | None) -> date | None:
    """Parse ISO date string (YYYY-MM-DD) to date, returning None for invalid."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
