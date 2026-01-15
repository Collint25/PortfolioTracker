from sqlalchemy.orm import Session

from app.models import Account
from app.services import position_service


def get_all_accounts(db: Session) -> list[Account]:
    """Get all accounts ordered by name."""
    return db.query(Account).order_by(Account.name).all()


def get_account_by_id(db: Session, account_id: int) -> Account | None:
    """Get a single account by ID."""
    return db.query(Account).filter(Account.id == account_id).first()


def get_account_by_snaptrade_id(db: Session, snaptrade_id: str) -> Account | None:
    """Get a single account by SnapTrade ID."""
    return db.query(Account).filter(Account.snaptrade_id == snaptrade_id).first()


def get_all_accounts_with_totals(db: Session) -> list[dict]:
    """
    Get all accounts with their position totals.

    Returns list of dicts with account and totals.
    """
    accounts = get_all_accounts(db)
    result = []

    for account in accounts:
        _, totals = position_service.get_account_positions_summary(db, account.id)
        result.append({
            "account": account,
            "totals": totals,
        })

    return result
