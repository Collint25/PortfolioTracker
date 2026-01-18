"""Tests for position calculation functions."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.calculations import position_calcs


@pytest.fixture
def position():
    """Create a mock position with typical values."""
    pos = MagicMock()
    pos.quantity = Decimal("100")
    pos.current_price = Decimal("50.00")
    pos.average_cost = Decimal("45.00")
    pos.previous_close = Decimal("48.00")
    return pos


class TestMarketValue:
    def test_calculates_quantity_times_price(self, position):
        result = position_calcs.market_value(position)
        assert result == Decimal("5000.00")

    def test_returns_none_when_price_missing(self, position):
        position.current_price = None
        assert position_calcs.market_value(position) is None


class TestCostBasis:
    def test_calculates_quantity_times_average_cost(self, position):
        result = position_calcs.cost_basis(position)
        assert result == Decimal("4500.00")

    def test_returns_none_when_average_cost_missing(self, position):
        position.average_cost = None
        assert position_calcs.cost_basis(position) is None


class TestGainLoss:
    def test_calculates_market_value_minus_cost_basis(self, position):
        result = position_calcs.gain_loss(position)
        assert result == Decimal("500.00")

    def test_returns_none_when_price_missing(self, position):
        position.current_price = None
        assert position_calcs.gain_loss(position) is None

    def test_returns_none_when_average_cost_missing(self, position):
        position.average_cost = None
        assert position_calcs.gain_loss(position) is None


class TestGainLossPercent:
    def test_calculates_percentage(self, position):
        # gain_loss = 500, cost_basis = 4500
        # 500 / 4500 * 100 = 11.111...
        result = position_calcs.gain_loss_percent(position)
        assert result is not None
        assert abs(result - Decimal("11.111")) < Decimal("0.001")

    def test_returns_none_when_cost_basis_zero(self, position):
        position.average_cost = Decimal("0")
        assert position_calcs.gain_loss_percent(position) is None

    def test_returns_none_when_values_missing(self, position):
        position.current_price = None
        assert position_calcs.gain_loss_percent(position) is None


class TestDailyChange:
    def test_calculates_price_diff_times_quantity(self, position):
        # (50 - 48) * 100 = 200
        result = position_calcs.daily_change(position)
        assert result == Decimal("200.00")

    def test_returns_none_when_current_price_missing(self, position):
        position.current_price = None
        assert position_calcs.daily_change(position) is None

    def test_returns_none_when_previous_close_missing(self, position):
        position.previous_close = None
        assert position_calcs.daily_change(position) is None


class TestDailyChangePercent:
    def test_calculates_percentage(self, position):
        # (50 - 48) / 48 * 100 = 4.166...
        result = position_calcs.daily_change_percent(position)
        assert result is not None
        assert abs(result - Decimal("4.166")) < Decimal("0.001")

    def test_returns_none_when_previous_close_zero(self, position):
        position.previous_close = Decimal("0")
        assert position_calcs.daily_change_percent(position) is None

    def test_returns_none_when_values_missing(self, position):
        position.previous_close = None
        assert position_calcs.daily_change_percent(position) is None
