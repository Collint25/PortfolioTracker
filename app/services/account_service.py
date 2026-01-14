from sqlalchemy.orm import Session

from app.models import Account


def get_all_accounts(db: Session) -> list[Account]:
    """Get all accounts ordered by name."""
    return db.query(Account).order_by(Account.name).all()


def get_account_by_id(db: Session, account_id: int) -> Account | None:
    """Get a single account by ID."""
    return db.query(Account).filter(Account.id == account_id).first()


def get_account_by_snaptrade_id(db: Session, snaptrade_id: str) -> Account | None:
    """Get a single account by SnapTrade ID."""
    return db.query(Account).filter(Account.snaptrade_id == snaptrade_id).first()
