#!/usr/bin/env python
"""Backfill option data from raw JSON for existing transactions."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from decimal import Decimal

from app.database import SessionLocal
from app.models import Transaction


def _to_decimal(value) -> Decimal | None:
    """Convert value to Decimal, handling None."""
    if value is None:
        return None
    return Decimal(str(value))


def _parse_date(value):
    """Parse date string to date object."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


def backfill_option_data():
    """Backfill option fields from raw JSON for all transactions."""
    db = SessionLocal()
    try:
        transactions = db.query(Transaction).filter(
            Transaction._raw_json.isnot(None)
        ).all()

        updated = 0
        option_count = 0

        for txn in transactions:
            raw = txn._raw_json or {}
            option_symbol = raw.get("option_symbol")
            option_action = raw.get("option_type")  # BUY_TO_OPEN, etc.

            if option_symbol:
                txn.is_option = True
                txn.option_type = option_symbol.get("option_type")
                txn.strike_price = _to_decimal(option_symbol.get("strike_price"))
                txn.expiration_date = _parse_date(option_symbol.get("expiration_date"))
                txn.option_ticker = option_symbol.get("ticker")

                underlying = option_symbol.get("underlying_symbol", {})
                txn.underlying_symbol = (
                    underlying.get("symbol") if isinstance(underlying, dict) else None
                )
                txn.option_action = option_action if option_action else None
                option_count += 1
            else:
                txn.is_option = False
                txn.option_type = None
                txn.strike_price = None
                txn.expiration_date = None
                txn.option_ticker = None
                txn.underlying_symbol = None
                txn.option_action = None

            updated += 1

        db.commit()
        print(f"Updated {updated} transactions ({option_count} options)")

    finally:
        db.close()


if __name__ == "__main__":
    backfill_option_data()
