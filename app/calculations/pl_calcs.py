"""Pure calculation functions for trade P/L metrics."""

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import LinkedTrade


def linked_trade_pl(linked_trade: "LinkedTrade") -> Decimal:
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


def pl_summary(linked_trades: list["LinkedTrade"]) -> dict:
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
