"""Position service for querying and calculating position data."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Position


def get_positions_by_account(db: Session, account_id: int) -> list[Position]:
    """Get all positions for an account, ordered by symbol."""
    return (
        db.query(Position)
        .filter(Position.account_id == account_id)
        .order_by(Position.symbol)
        .all()
    )


def calculate_market_value(position: Position) -> Decimal | None:
    """Calculate market value (quantity * current_price)."""
    if position.current_price is None:
        return None
    return position.quantity * position.current_price


def calculate_cost_basis(position: Position) -> Decimal | None:
    """Calculate total cost basis (quantity * average_cost)."""
    if position.average_cost is None:
        return None
    return position.quantity * position.average_cost


def calculate_gain_loss(position: Position) -> Decimal | None:
    """Calculate unrealized gain/loss (market_value - cost_basis)."""
    market_value = calculate_market_value(position)
    cost_basis = calculate_cost_basis(position)
    if market_value is None or cost_basis is None:
        return None
    return market_value - cost_basis


def calculate_gain_loss_percent(position: Position) -> Decimal | None:
    """Calculate unrealized gain/loss as percentage."""
    gain_loss = calculate_gain_loss(position)
    cost_basis = calculate_cost_basis(position)
    if gain_loss is None or cost_basis is None or cost_basis == 0:
        return None
    return (gain_loss / cost_basis) * 100


def get_position_summary(position: Position) -> dict:
    """Get position with calculated fields."""
    return {
        "position": position,
        "market_value": calculate_market_value(position),
        "cost_basis": calculate_cost_basis(position),
        "gain_loss": calculate_gain_loss(position),
        "gain_loss_percent": calculate_gain_loss_percent(position),
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

    for s in summaries:
        if s["market_value"] is not None:
            total_market_value += s["market_value"]
        if s["cost_basis"] is not None:
            total_cost_basis += s["cost_basis"]

    total_gain_loss = total_market_value - total_cost_basis
    total_gain_loss_percent = (
        (total_gain_loss / total_cost_basis) * 100
        if total_cost_basis != 0
        else None
    )

    totals = {
        "market_value": total_market_value,
        "cost_basis": total_cost_basis,
        "gain_loss": total_gain_loss,
        "gain_loss_percent": total_gain_loss_percent,
    }

    return summaries, totals
