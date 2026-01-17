"""Parsing utilities for SnapTrade API responses."""

from datetime import date, datetime
from decimal import Decimal


def to_decimal(value) -> Decimal | None:
    """Convert value to Decimal, handling None."""
    if value is None:
        return None
    return Decimal(str(value))


def parse_date(value) -> date | None:
    """Parse date string to date object."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    # Try ISO format
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


def extract_symbol(data: dict) -> str:
    """
    Extract symbol string from various SnapTrade response formats.

    Handles:
    - Holdings: data.symbol.symbol.symbol (deeply nested)
    - Transactions: data.symbol (string or dict with .symbol)
    """
    symbol = data.get("symbol", {})

    # If symbol is a string, return it directly
    if isinstance(symbol, str):
        return symbol if symbol else ""

    # If symbol is a dict, look for nested symbol
    if isinstance(symbol, dict):
        inner = symbol.get("symbol", {})
        if isinstance(inner, dict):
            return inner.get("symbol", "")
        if isinstance(inner, str):
            return inner
        return ""

    return ""


def extract_option_data(data: dict) -> dict:
    """
    Extract option-related fields from raw transaction data.

    Returns dict with keys:
    - is_option: bool
    - option_type: str | None (CALL/PUT)
    - strike_price: Decimal | None
    - expiration_date: date | None
    - option_ticker: str | None
    - underlying_symbol: str | None
    - option_action: str | None (BUY_TO_OPEN, etc.)
    """
    option_symbol = data.get("option_symbol")
    option_action = data.get("option_type")  # BUY_TO_OPEN, SELL_TO_CLOSE, etc.

    if not option_symbol:
        return {
            "is_option": False,
            "option_type": None,
            "strike_price": None,
            "expiration_date": None,
            "option_ticker": None,
            "underlying_symbol": None,
            "option_action": None,
        }

    # Extract fields from option_symbol object
    option_type = option_symbol.get("option_type")  # CALL or PUT
    strike_price = to_decimal(option_symbol.get("strike_price"))
    expiration_date = parse_date(option_symbol.get("expiration_date"))
    option_ticker = option_symbol.get("ticker")

    # Get underlying symbol
    underlying = option_symbol.get("underlying_symbol", {})
    underlying_symbol = underlying.get("symbol") if isinstance(underlying, dict) else None

    return {
        "is_option": True,
        "option_type": option_type,
        "strike_price": strike_price,
        "expiration_date": expiration_date,
        "option_ticker": option_ticker,
        "underlying_symbol": underlying_symbol,
        "option_action": option_action if option_action else None,
    }


def extract_holding_option_data(data: dict) -> dict:
    """
    Extract option data from holdings response format.

    Holdings have a different structure: data.symbol.option_symbol

    Returns dict with keys:
    - is_option: bool
    - option_type: str | None
    - strike_price: Decimal | None
    - expiration_date: date | None
    - option_ticker: str | None
    - underlying_symbol: str | None
    """
    symbol_data = data.get("symbol", {})
    option_symbol = symbol_data.get("option_symbol", {}) if isinstance(symbol_data, dict) else {}

    if not option_symbol:
        return {
            "is_option": False,
            "option_type": None,
            "strike_price": None,
            "expiration_date": None,
            "option_ticker": None,
            "underlying_symbol": None,
        }

    option_ticker = option_symbol.get("ticker", "")
    option_type = option_symbol.get("option_type")
    strike_price = to_decimal(option_symbol.get("strike_price"))
    expiration_date = parse_date(option_symbol.get("expiration_date"))

    underlying = option_symbol.get("underlying_symbol", {})
    underlying_symbol = underlying.get("symbol") if isinstance(underlying, dict) else None

    return {
        "is_option": True,
        "option_type": option_type,
        "strike_price": strike_price,
        "expiration_date": expiration_date,
        "option_ticker": option_ticker,
        "underlying_symbol": underlying_symbol,
    }


def extract_currency(data: dict) -> str:
    """Extract currency code from response, defaulting to USD."""
    currency_data = data.get("currency")
    if isinstance(currency_data, dict):
        return currency_data.get("code", "USD")
    return "USD"
