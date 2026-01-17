"""Position synchronization from SnapTrade."""

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account, Position
from app.services.snaptrade_client import fetch_holdings, fetch_option_holdings
from app.services.sync.snaptrade_parser import (
    extract_currency,
    extract_holding_option_data,
    to_decimal,
)

logger = logging.getLogger(__name__)


def sync_positions(db: Session, client, user_id: str, user_secret: str) -> int:
    """Sync positions for all accounts (stock and option holdings)."""
    accounts = db.query(Account).all()
    count = 0

    for account in accounts:
        count += _sync_stock_positions(db, client, user_id, user_secret, account)
        count += _sync_option_positions(db, client, user_id, user_secret, account)

    db.commit()
    return count


def _sync_stock_positions(
    db: Session, client, user_id: str, user_secret: str, account: Account
) -> int:
    """Sync stock holdings for an account."""
    holdings_data = fetch_holdings(client, user_id, user_secret, account.snaptrade_id)
    count = 0

    for data in holdings_data:
        snaptrade_id = _get_holding_snaptrade_id(data, account.snaptrade_id)
        if not snaptrade_id:
            continue

        symbol_str = _extract_holding_symbol(data)
        position = _get_or_create_position(db, snaptrade_id, account.id)

        _update_position_fields(position, data, symbol_str, is_option=False)
        count += 1

    return count


def _sync_option_positions(
    db: Session, client, user_id: str, user_secret: str, account: Account
) -> int:
    """Sync option holdings for an account."""
    try:
        option_holdings = fetch_option_holdings(
            client, user_id, user_secret, account.snaptrade_id
        )
    except Exception as e:
        logger.warning(f"Failed to fetch option holdings for account {account.id}: {e}")
        return 0

    count = 0
    for data in option_holdings:
        snaptrade_id = _get_option_holding_snaptrade_id(data, account.snaptrade_id)
        if not snaptrade_id:
            continue

        option_data = extract_holding_option_data(data)
        symbol_str = (
            option_data["underlying_symbol"] or option_data["option_ticker"] or ""
        )

        position = _get_or_create_position(db, snaptrade_id, account.id)
        _update_position_fields(position, data, symbol_str, is_option=True)
        _update_option_fields(position, option_data)
        count += 1

    return count


def _get_holding_snaptrade_id(data: dict, account_snaptrade_id: str) -> str | None:
    """Generate compound ID for stock holding: account_id:symbol_id."""
    symbol_outer = data.get("symbol", {})
    symbol_id = symbol_outer.get("id") if isinstance(symbol_outer, dict) else None
    if not symbol_id:
        return None
    return f"{account_snaptrade_id}:{symbol_id}"


def _get_option_holding_snaptrade_id(
    data: dict, account_snaptrade_id: str
) -> str | None:
    """Generate compound ID for option holding: account_id:opt:option_id."""
    symbol_data = data.get("symbol", {})
    option_symbol = (
        symbol_data.get("option_symbol", {}) if isinstance(symbol_data, dict) else {}
    )
    option_id = option_symbol.get("id") if option_symbol else None
    if not option_id:
        return None
    return f"{account_snaptrade_id}:opt:{option_id}"


def _extract_holding_symbol(data: dict) -> str:
    """Extract symbol string from holding data (deeply nested)."""
    symbol_outer = data.get("symbol", {})
    symbol_inner = (
        symbol_outer.get("symbol", {}) if isinstance(symbol_outer, dict) else {}
    )
    if isinstance(symbol_inner, dict):
        result = symbol_inner.get("symbol", "")
        return str(result) if result else ""
    if isinstance(symbol_inner, str):
        return symbol_inner
    return ""


def _get_or_create_position(
    db: Session, snaptrade_id: str, account_id: int
) -> Position:
    """Get existing position or create new one."""
    position = db.query(Position).filter(Position.snaptrade_id == snaptrade_id).first()
    if not position:
        position = Position(snaptrade_id=snaptrade_id, account_id=account_id)
        db.add(position)
    return position


def _update_position_fields(
    position: Position, data: dict, symbol: str, is_option: bool
) -> None:
    """Update common position fields from API data."""
    position.symbol = symbol
    position.quantity = Decimal(str(data.get("units", 0)))
    position.average_cost = to_decimal(data.get("average_purchase_price"))
    position.current_price = to_decimal(data.get("price"))
    position.currency = extract_currency(data)
    position._raw_json = data
    position.is_option = is_option

    if not is_option:
        # Clear option fields for stock positions
        position.option_type = None
        position.strike_price = None
        position.expiration_date = None
        position.option_ticker = None
        position.underlying_symbol = None


def _update_option_fields(position: Position, option_data: dict) -> None:
    """Update option-specific fields from parsed option data."""
    position.option_type = option_data["option_type"]
    position.strike_price = option_data["strike_price"]
    position.expiration_date = option_data["expiration_date"]
    position.option_ticker = option_data["option_ticker"]
    position.underlying_symbol = option_data["underlying_symbol"]
