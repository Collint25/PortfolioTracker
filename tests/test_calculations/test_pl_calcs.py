"""Tests for P/L calculation functions."""

from decimal import Decimal
from unittest.mock import MagicMock

from app.calculations import pl_calcs


def make_leg(allocated_qty: str, txn_qty: str, txn_amount: str) -> MagicMock:
    """Create a mock LinkedTradeLeg."""
    leg = MagicMock()
    leg.allocated_quantity = Decimal(allocated_qty)
    leg.transaction = MagicMock()
    leg.transaction.quantity = Decimal(txn_qty)
    leg.transaction.amount = Decimal(txn_amount)
    return leg


class TestLinkedTradePl:
    def test_sums_proportioned_amounts(self):
        """P/L sums transaction amounts proportioned by allocated quantity."""
        linked_trade = MagicMock()
        # Leg 1: allocated 10 of 10, amount = -500 (paid $500)
        # Leg 2: allocated 10 of 10, amount = +650 (received $650)
        # Total P/L = -500 + 650 = 150
        linked_trade.legs = [
            make_leg("10", "10", "-500"),
            make_leg("10", "10", "650"),
        ]

        result = pl_calcs.linked_trade_pl(linked_trade)
        assert result == Decimal("150")

    def test_handles_partial_allocation(self):
        """Correctly proportions when leg uses partial transaction quantity."""
        linked_trade = MagicMock()
        # Leg uses 5 of 10 contracts from a -1000 transaction
        # Proportioned amount = -1000 * (5/10) = -500
        linked_trade.legs = [make_leg("5", "10", "-1000")]

        result = pl_calcs.linked_trade_pl(linked_trade)
        assert result == Decimal("-500")

    def test_handles_missing_amount(self):
        """Skips legs where transaction has no amount."""
        linked_trade = MagicMock()
        leg = make_leg("10", "10", "100")
        leg.transaction.amount = None
        linked_trade.legs = [leg]

        result = pl_calcs.linked_trade_pl(linked_trade)
        assert result == Decimal("0")

    def test_empty_legs_returns_zero(self):
        """Returns zero for trade with no legs."""
        linked_trade = MagicMock()
        linked_trade.legs = []

        result = pl_calcs.linked_trade_pl(linked_trade)
        assert result == Decimal("0")
