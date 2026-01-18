"""Pure calculation functions for position metrics."""

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Position


def market_value(position: "Position") -> Decimal | None:
    """Calculate market value (quantity * current_price)."""
    if position.current_price is None:
        return None
    return position.quantity * position.current_price


def cost_basis(position: "Position") -> Decimal | None:
    """Calculate total cost basis (quantity * average_cost)."""
    if position.average_cost is None:
        return None
    return position.quantity * position.average_cost


def gain_loss(position: "Position") -> Decimal | None:
    """Calculate unrealized gain/loss (market_value - cost_basis)."""
    mv = market_value(position)
    cb = cost_basis(position)
    if mv is None or cb is None:
        return None
    return mv - cb


def gain_loss_percent(position: "Position") -> Decimal | None:
    """Calculate unrealized gain/loss as percentage."""
    gl = gain_loss(position)
    cb = cost_basis(position)
    if gl is None or cb is None or cb == 0:
        return None
    return (gl / cb) * 100


def daily_change(position: "Position") -> Decimal | None:
    """Calculate daily change in dollars."""
    if position.current_price is None or position.previous_close is None:
        return None
    return (position.current_price - position.previous_close) * position.quantity


def daily_change_percent(position: "Position") -> Decimal | None:
    """Calculate daily change as percentage."""
    if position.current_price is None or position.previous_close is None:
        return None
    if position.previous_close == 0:
        return None
    return (
        (position.current_price - position.previous_close) / position.previous_close
    ) * 100
