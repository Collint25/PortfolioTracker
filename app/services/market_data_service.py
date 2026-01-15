"""Market data service for fetching real-time stock quotes via Finnhub."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Position

logger = logging.getLogger(__name__)

# Simple in-memory cache for quotes
_quote_cache: dict[str, tuple[Decimal, datetime]] = {}
CACHE_TTL_MINUTES = 5

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def get_quote(symbol: str) -> Decimal | None:
    """
    Fetch current price for a symbol from Finnhub.

    Returns cached value if available and fresh.
    """
    settings = get_settings()
    if not settings.market_data_api_key:
        logger.warning("Market data API key not configured")
        return None

    # Check cache
    if symbol in _quote_cache:
        price, cached_at = _quote_cache[symbol]
        if datetime.now() - cached_at < timedelta(minutes=CACHE_TTL_MINUTES):
            return price

    try:
        response = httpx.get(
            f"{FINNHUB_BASE_URL}/quote",
            params={"symbol": symbol, "token": settings.market_data_api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

        # Finnhub returns: c=current, h=high, l=low, o=open, pc=previous close
        current_price = data.get("c")
        if current_price and current_price > 0:
            price = Decimal(str(current_price))
            _quote_cache[symbol] = (price, datetime.now())
            return price

        logger.warning("No price data for %s: %s", symbol, data)
        return None

    except httpx.HTTPError as e:
        logger.error("Finnhub API error for %s: %s", symbol, e)
        return None
    except Exception as e:
        logger.error("Error fetching quote for %s: %s", symbol, e)
        return None


def refresh_position_prices(db: Session, account_id: int) -> dict[str, any]:
    """
    Refresh current prices for all positions in an account.

    Returns summary of updated positions.
    """
    positions = (
        db.query(Position)
        .filter(Position.account_id == account_id)
        .all()
    )

    updated = 0
    failed = 0
    skipped = 0

    for position in positions:
        symbol = position.symbol

        # Skip money market funds (SPAXX, etc.) - always $1
        if symbol in ("SPAXX", "FDRXX", "SPRXX", "FZFXX"):
            skipped += 1
            continue

        # Skip options (contain spaces or special chars)
        if " " in symbol or len(symbol) > 10:
            skipped += 1
            continue

        price = get_quote(symbol)
        if price is not None:
            position.current_price = price
            updated += 1
            logger.info("Updated %s: $%s", symbol, price)
        else:
            failed += 1

    db.commit()

    return {
        "updated": updated,
        "failed": failed,
        "skipped": skipped,
        "total": len(positions),
    }


def clear_cache() -> None:
    """Clear the quote cache."""
    _quote_cache.clear()
