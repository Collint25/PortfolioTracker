"""Position service for querying and aggregating position data."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.calculations import position_calcs
from app.models import Position


def get_positions_by_account(db: Session, account_id: int) -> list[Position]:
    """Get all positions for an account, ordered by symbol."""
    return (
        db.query(Position)
        .filter(Position.account_id == account_id)
        .order_by(Position.symbol)
        .all()
    )


def get_position_summary(position: Position) -> dict:
    """Get position with calculated fields."""
    return {
        "position": position,
        "market_value": position_calcs.market_value(position),
        "cost_basis": position_calcs.cost_basis(position),
        "gain_loss": position_calcs.gain_loss(position),
        "gain_loss_percent": position_calcs.gain_loss_percent(position),
        "daily_change": position_calcs.daily_change(position),
        "daily_change_percent": position_calcs.daily_change_percent(position),
    }


def get_account_positions_summary(
    db: Session, account_id: int
) -> tuple[list[dict], dict]:
    """
    Get all positions for an account with calculated fields.

    Returns:
        Tuple of (positions list, totals dict)
    """
    positions = get_positions_by_account(db, account_id)
    summaries = [get_position_summary(p) for p in positions]

    # Calculate totals
    total_market_value = Decimal("0")
    total_cost_basis = Decimal("0")
    total_daily_change = Decimal("0")
    total_previous_value = Decimal("0")
    has_daily_data = False

    for s in summaries:
        if s["market_value"] is not None:
            total_market_value += s["market_value"]
        if s["cost_basis"] is not None:
            total_cost_basis += s["cost_basis"]
        if s["daily_change"] is not None:
            total_daily_change += s["daily_change"]
            has_daily_data = True
        # Track previous value for accurate percent calculation
        if s["position"].previous_close is not None and s["position"].quantity:
            total_previous_value += (
                s["position"].previous_close * s["position"].quantity
            )

    total_gain_loss = total_market_value - total_cost_basis
    total_gain_loss_percent = (
        (total_gain_loss / total_cost_basis) * 100 if total_cost_basis != 0 else None
    )

    # Daily change percent based on previous value
    total_daily_change_percent = (
        (total_daily_change / total_previous_value) * 100
        if has_daily_data and total_previous_value != 0
        else None
    )

    totals = {
        "market_value": total_market_value,
        "cost_basis": total_cost_basis,
        "gain_loss": total_gain_loss,
        "gain_loss_percent": total_gain_loss_percent,
        "daily_change": total_daily_change if has_daily_data else None,
        "daily_change_percent": total_daily_change_percent,
    }

    return summaries, totals
