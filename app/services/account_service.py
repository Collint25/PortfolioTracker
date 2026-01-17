from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models import Account, Position
from app.services import base


def get_all_accounts(db: Session) -> list[Account]:
    """Get all accounts ordered by name."""
    return base.get_all(db, Account, order_by=Account.name)


def get_account_by_id(db: Session, account_id: int) -> Account | None:
    """Get a single account by ID."""
    return base.get_by_id(db, Account, account_id)


def get_account_by_snaptrade_id(db: Session, snaptrade_id: str) -> Account | None:
    """Get a single account by SnapTrade ID."""
    return db.query(Account).filter(Account.snaptrade_id == snaptrade_id).first()


def get_all_accounts_with_totals(db: Session) -> list[dict]:
    """
    Get all accounts with their position totals.

    Uses eager loading to avoid N+1 queries.
    Returns list of dicts with account and totals.
    """
    # Eager load positions with accounts in a single query
    accounts = (
        db.query(Account)
        .options(joinedload(Account.positions))
        .order_by(Account.name)
        .all()
    )

    result = []
    for account in accounts:
        totals = _calculate_account_totals(account.positions)
        result.append({
            "account": account,
            "totals": totals,
        })

    return result


def _calculate_account_totals(positions: list[Position]) -> dict:
    """Calculate totals from a list of positions."""
    total_market_value = Decimal("0")
    total_cost_basis = Decimal("0")
    total_daily_change = Decimal("0")
    total_previous_value = Decimal("0")
    has_daily_data = False

    for position in positions:
        # Market value
        if position.current_price is not None:
            market_value = position.quantity * position.current_price
            total_market_value += market_value

        # Cost basis
        if position.average_cost is not None:
            cost_basis = position.quantity * position.average_cost
            total_cost_basis += cost_basis

        # Daily change
        if position.current_price is not None and position.previous_close is not None:
            daily_change = (position.current_price - position.previous_close) * position.quantity
            total_daily_change += daily_change
            total_previous_value += position.previous_close * position.quantity
            has_daily_data = True

    total_gain_loss = total_market_value - total_cost_basis
    total_gain_loss_percent = (
        (total_gain_loss / total_cost_basis) * 100
        if total_cost_basis != 0
        else None
    )

    total_daily_change_percent = (
        (total_daily_change / total_previous_value) * 100
        if has_daily_data and total_previous_value != 0
        else None
    )

    return {
        "market_value": total_market_value,
        "cost_basis": total_cost_basis,
        "gain_loss": total_gain_loss,
        "gain_loss_percent": total_gain_loss_percent,
        "daily_change": total_daily_change if has_daily_data else None,
        "daily_change_percent": total_daily_change_percent,
    }
