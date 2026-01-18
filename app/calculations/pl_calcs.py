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
