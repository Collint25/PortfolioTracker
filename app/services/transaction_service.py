from sqlalchemy.orm import Session

from app.models import Transaction
from app.services.filters import (
    PaginationParams,
    TransactionFilter,
    apply_pagination,
    apply_transaction_filters,
    apply_transaction_sorting,
)


def get_transactions(
    db: Session,
    filters: TransactionFilter,
    pagination: PaginationParams = PaginationParams(),
) -> tuple[list[Transaction], int]:
    """
    Get filtered, sorted, paginated transactions.

    Returns (transactions, total_count).
    """
    query = db.query(Transaction)

    # Apply filters
    query = apply_transaction_filters(query, filters)

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    query = apply_transaction_sorting(query, filters)

    # Apply pagination
    query = apply_pagination(query, pagination)

    transactions = query.all()
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
    results = db.query(Transaction.type).distinct().order_by(Transaction.type).all()
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
