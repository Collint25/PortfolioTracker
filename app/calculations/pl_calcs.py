"""Pure calculation functions for trade P/L metrics."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import TradeLot


def linked_trade_pl(linked_trade: "TradeLot") -> Decimal:
    """
    Calculate realized P/L for a linked trade.

    P/L = sum of all transaction amounts, proportioned by allocated quantity.
    Positive amount = credit (received money), negative = debit (paid money).
    """
    total_pl = Decimal("0")

    for leg in linked_trade.legs:
        txn = leg.transaction
        if txn and txn.amount:
            txn_qty = abs(txn.quantity) if txn.quantity else Decimal("1")
            if txn_qty > 0:
                proportion = leg.allocated_quantity / txn_qty
                total_pl += txn.amount * proportion

    return total_pl


def pl_summary(linked_trades: list["TradeLot"]) -> dict:
    """
    Calculate P/L summary statistics from a list of linked trades.

    Returns dict with: total_pl, winners, losers, win_rate, open_count, closed_count
    """
    total_pl = Decimal("0")
    winners = 0
    losers = 0
    open_count = 0
    closed_count = 0

    for lt in linked_trades:
        if lt.is_closed:
            closed_count += 1
            total_pl += lt.realized_pl
            if lt.realized_pl > 0:
                winners += 1
            elif lt.realized_pl < 0:
                losers += 1
        else:
            open_count += 1

    win_rate = (winners / closed_count * 100) if closed_count > 0 else 0

    return {
        "total_pl": total_pl,
        "winners": winners,
        "losers": losers,
        "win_rate": win_rate,
        "open_count": open_count,
        "closed_count": closed_count,
    }


def pl_over_time(lots: list["TradeLot"]) -> list[dict]:
    """
    Calculate cumulative P/L over time from closed lots.

    Returns list of dicts with 'date' and 'cumulative_pl' keys,
    sorted chronologically. Same-day closes are aggregated.
    """
    # Group P/L by close date
    daily_pl: dict[date, Decimal] = defaultdict(Decimal)

    for lot in lots:
        if not lot.is_closed:
            continue
        # Get close date from last leg
        if lot.legs:
            close_date = lot.legs[-1].trade_date
            daily_pl[close_date] += lot.realized_pl

    # Sort by date and compute cumulative
    sorted_dates = sorted(daily_pl.keys())
    result = []
    cumulative = Decimal("0")

    for d in sorted_dates:
        cumulative += daily_pl[d]
        result.append({"date": d, "cumulative_pl": cumulative})

    return result
