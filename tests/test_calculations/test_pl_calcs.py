"""Tests for P/L calculation functions."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.calculations import pl_calcs


def make_leg(allocated_qty: str, txn_qty: str, txn_amount: str) -> MagicMock:
    """Create a mock LotTransaction."""
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


def make_lot(realized_pl: str, is_closed: bool) -> MagicMock:
    """Create a mock TradeLot for summary tests."""
    lt = MagicMock()
    lt.realized_pl = Decimal(realized_pl)
    lt.is_closed = is_closed
    lt.legs = []  # Not needed for summary
    return lt


class TestPlSummary:
    def test_calculates_total_pl(self):
        """Sums realized P/L from closed trades."""
        trades = [
            make_lot("100", is_closed=True),
            make_lot("-50", is_closed=True),
        ]

        result = pl_calcs.pl_summary(trades)
        assert result["total_pl"] == Decimal("50")

    def test_counts_winners_and_losers(self):
        """Categorizes closed trades by P/L sign."""
        trades = [
            make_lot("100", is_closed=True),  # winner
            make_lot("-50", is_closed=True),  # loser
            make_lot("200", is_closed=True),  # winner
        ]

        result = pl_calcs.pl_summary(trades)
        assert result["winners"] == 2
        assert result["losers"] == 1

    def test_calculates_win_rate(self):
        """Win rate = winners / closed_count * 100."""
        trades = [
            make_lot("100", is_closed=True),
            make_lot("-50", is_closed=True),
        ]

        result = pl_calcs.pl_summary(trades)
        assert result["win_rate"] == 50.0

    def test_counts_open_and_closed(self):
        """Separately counts open and closed trades."""
        trades = [
            make_lot("0", is_closed=False),  # open
            make_lot("100", is_closed=True),  # closed
        ]

        result = pl_calcs.pl_summary(trades)
        assert result["open_count"] == 1
        assert result["closed_count"] == 1

    def test_excludes_open_trades_from_pl(self):
        """Open trades don't contribute to total P/L."""
        trades = [
            make_lot("999", is_closed=False),  # open - ignored
            make_lot("100", is_closed=True),
        ]

        result = pl_calcs.pl_summary(trades)
        assert result["total_pl"] == Decimal("100")

    def test_empty_list_returns_zeros(self):
        """Handles empty trade list gracefully."""
        result = pl_calcs.pl_summary([])

        assert result["total_pl"] == Decimal("0")
        assert result["winners"] == 0
        assert result["losers"] == 0
        assert result["win_rate"] == 0
        assert result["open_count"] == 0
        assert result["closed_count"] == 0


def make_lot_with_date(
    realized_pl: str, is_closed: bool, close_date: date | None
) -> MagicMock:
    """Create a mock TradeLot with close date for time series tests."""
    lt = MagicMock()
    lt.realized_pl = Decimal(realized_pl)
    lt.is_closed = is_closed
    # Simulate getting close date from last leg
    if close_date:
        leg = MagicMock()
        leg.trade_date = close_date
        lt.legs = [leg]
    else:
        lt.legs = []
    return lt


class TestPlOverTime:
    def test_returns_cumulative_pl_by_date(self):
        """Returns list of dicts with date and cumulative P/L."""
        lots = [
            make_lot_with_date("100", is_closed=True, close_date=date(2025, 1, 10)),
            make_lot_with_date("50", is_closed=True, close_date=date(2025, 1, 15)),
        ]

        result = pl_calcs.pl_over_time(lots)

        assert len(result) == 2
        assert result[0] == {"date": date(2025, 1, 10), "cumulative_pl": Decimal("100")}
        assert result[1] == {"date": date(2025, 1, 15), "cumulative_pl": Decimal("150")}

    def test_sorts_by_date(self):
        """Results are sorted chronologically even if input is not."""
        lots = [
            make_lot_with_date("50", is_closed=True, close_date=date(2025, 1, 20)),
            make_lot_with_date("100", is_closed=True, close_date=date(2025, 1, 5)),
        ]

        result = pl_calcs.pl_over_time(lots)

        assert result[0]["date"] == date(2025, 1, 5)
        assert result[1]["date"] == date(2025, 1, 20)

    def test_aggregates_same_day(self):
        """Multiple closes on same day are aggregated into one data point."""
        lots = [
            make_lot_with_date("100", is_closed=True, close_date=date(2025, 1, 10)),
            make_lot_with_date("50", is_closed=True, close_date=date(2025, 1, 10)),
        ]

        result = pl_calcs.pl_over_time(lots)

        assert len(result) == 1
        assert result[0]["cumulative_pl"] == Decimal("150")

    def test_excludes_open_lots(self):
        """Open lots are excluded from time series."""
        lots = [
            make_lot_with_date("100", is_closed=True, close_date=date(2025, 1, 10)),
            make_lot_with_date("999", is_closed=False, close_date=None),
        ]

        result = pl_calcs.pl_over_time(lots)

        assert len(result) == 1
        assert result[0]["cumulative_pl"] == Decimal("100")

    def test_empty_list_returns_empty(self):
        """Empty input returns empty list."""
        result = pl_calcs.pl_over_time([])
        assert result == []
