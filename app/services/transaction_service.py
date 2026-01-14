from datetime import date

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models import Transaction, Account
from app.models.tag import transaction_tags


def get_transactions(
    db: Session,
    *,
    account_id: int | None = None,
    symbol: str | None = None,
    transaction_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    tag_id: int | None = None,
    sort_by: str = "trade_date",
    sort_dir: str = "desc",
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[Transaction], int]:
    """
    Get filtered, sorted, paginated transactions.

    Returns (transactions, total_count).
    """
    query = db.query(Transaction)

    # Apply filters
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if symbol:
        query = query.filter(Transaction.symbol == symbol)
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type)
    if start_date:
        query = query.filter(Transaction.trade_date >= start_date)
    if end_date:
        query = query.filter(Transaction.trade_date <= end_date)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.symbol.ilike(search_pattern),
                Transaction.description.ilike(search_pattern),
            )
        )
    if tag_id:
        query = query.join(transaction_tags).filter(transaction_tags.c.tag_id == tag_id)

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    sort_column = getattr(Transaction, sort_by, Transaction.trade_date)
    if sort_dir == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * per_page
    transactions = query.offset(offset).limit(per_page).all()

    return transactions, total


def get_transaction_by_id(db: Session, transaction_id: int) -> Transaction | None:
    """Get a single transaction by ID."""
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()


def get_unique_symbols(db: Session) -> list[str]:
    """Get all unique symbols from transactions."""
    results = (
        db.query(Transaction.symbol)
        .filter(Transaction.symbol.isnot(None))
        .distinct()
        .order_by(Transaction.symbol)
        .all()
    )
    return [r[0] for r in results if r[0]]


def get_unique_types(db: Session) -> list[str]:
    """Get all unique transaction types."""
    results = (
        db.query(Transaction.type)
        .distinct()
        .order_by(Transaction.type)
        .all()
    )
    return [r[0] for r in results if r[0]]
