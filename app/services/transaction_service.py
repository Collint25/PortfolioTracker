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
    is_option: bool | None = None,
    option_type: str | None = None,
    option_action: str | None = None,
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
        # Search in both symbol and underlying_symbol for options
        query = query.filter(
            or_(
                Transaction.symbol == symbol,
                Transaction.underlying_symbol == symbol,
            )
        )
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
                Transaction.underlying_symbol.ilike(search_pattern),
                Transaction.description.ilike(search_pattern),
            )
        )
    if tag_id:
        query = query.join(transaction_tags).filter(transaction_tags.c.tag_id == tag_id)
    # Option filters
    if is_option is not None:
        query = query.filter(Transaction.is_option == is_option)
    if option_type:
        query = query.filter(Transaction.option_type == option_type)
    if option_action:
        query = query.filter(Transaction.option_action == option_action)

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


def get_related_transactions(
    db: Session, transaction: Transaction
) -> list[Transaction]:
    """Get related transactions (same external_reference_id for multi-leg trades)."""
    if not transaction.external_reference_id:
        return []
    return (
        db.query(Transaction)
        .filter(
            Transaction.external_reference_id == transaction.external_reference_id,
            Transaction.id != transaction.id,
        )
        .all()
    )


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


def get_unique_option_types(db: Session) -> list[str]:
    """Get all unique option types (CALL, PUT)."""
    results = (
        db.query(Transaction.option_type)
        .filter(Transaction.option_type.isnot(None))
        .distinct()
        .order_by(Transaction.option_type)
        .all()
    )
    return [r[0] for r in results if r[0]]


def get_unique_option_actions(db: Session) -> list[str]:
    """Get all unique option actions (BUY_TO_OPEN, SELL_TO_CLOSE, etc.)."""
    results = (
        db.query(Transaction.option_action)
        .filter(Transaction.option_action.isnot(None))
        .distinct()
        .order_by(Transaction.option_action)
        .all()
    )
    return [r[0] for r in results if r[0]]
