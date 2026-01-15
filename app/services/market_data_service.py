"""Market data service for fetching real-time stock quotes via Finnhub."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Position

logger = logging.getLogger(__name__)

# Quote data structure: (current_price, previous_close)
QuoteData = tuple[Decimal, Decimal | None]

# Simple in-memory cache for quotes
_quote_cache: dict[str, tuple[QuoteData, datetime]] = {}
CACHE_TTL_MINUTES = 5

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def get_quote(symbol: str) -> QuoteData | None:
    """
    Fetch current price and previous close for a symbol from Finnhub.

    Returns (current_price, previous_close) tuple.
    Returns cached value if available and fresh.
    """
    settings = get_settings()
    if not settings.market_data_api_key:
        logger.warning("Market data API key not configured")
        return None

    # Check cache
    if symbol in _quote_cache:
        quote_data, cached_at = _quote_cache[symbol]
        if datetime.now() - cached_at < timedelta(minutes=CACHE_TTL_MINUTES):
            return quote_data

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
            prev_close = None
            if data.get("pc") and data["pc"] > 0:
                prev_close = Decimal(str(data["pc"]))
            quote_data = (price, prev_close)
            _quote_cache[symbol] = (quote_data, datetime.now())
            return quote_data

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
    Refresh current prices and previous close for all positions in an account.

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

        # Skip option positions (they have their own pricing)
        if position.is_option:
            skipped += 1
            continue

        quote_data = get_quote(symbol)
        if quote_data is not None:
            current_price, prev_close = quote_data
            position.current_price = current_price
            position.previous_close = prev_close
            updated += 1
            logger.info("Updated %s: $%s (prev: $%s)", symbol, current_price, prev_close)
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
