from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import TradeGroup, Transaction
from app.services import base

# Strategy type constants
STRATEGY_TYPES = [
    ("vertical_spread", "Vertical Spread"),
    ("iron_condor", "Iron Condor"),
    ("iron_butterfly", "Iron Butterfly"),
    ("straddle", "Straddle"),
    ("strangle", "Strangle"),
    ("calendar_spread", "Calendar Spread"),
    ("diagonal_spread", "Diagonal Spread"),
    ("covered_call", "Covered Call"),
    ("protective_put", "Protective Put"),
    ("collar", "Collar"),
    ("custom", "Custom"),
]


def get_all_trade_groups(db: Session) -> list[TradeGroup]:
    """Get all trade groups ordered by creation date (newest first)."""
    return base.get_all(db, TradeGroup, order_by=TradeGroup.created_at.desc())


def get_trade_group_by_id(db: Session, group_id: int) -> TradeGroup | None:
    """Get a single trade group by ID."""
    return base.get_by_id(db, TradeGroup, group_id)


def create_trade_group(
    db: Session,
    name: str,
    strategy_type: str | None = None,
    description: str | None = None,
) -> TradeGroup:
    """Create a new trade group."""
    return base.create(
        db, TradeGroup, name=name, strategy_type=strategy_type, description=description
    )


def update_trade_group(
    db: Session,
    group_id: int,
    name: str | None = None,
    strategy_type: str | None = None,
    description: str | None = None,
) -> TradeGroup | None:
    """Update an existing trade group."""
    group = get_trade_group_by_id(db, group_id)
    if not group:
        return None
    if name is not None:
        group.name = name
    if strategy_type is not None:
        group.strategy_type = strategy_type if strategy_type else None
    if description is not None:
        group.description = description if description else None
    db.commit()
    db.refresh(group)
    return group


def delete_trade_group(db: Session, group_id: int) -> bool:
    """Delete a trade group. Returns True if deleted, False if not found."""
    return base.delete(db, TradeGroup, group_id)


def add_transaction_to_group(db: Session, group_id: int, transaction_id: int) -> bool:
    """Add a transaction to a trade group. Returns True if successful."""
    group = get_trade_group_by_id(db, group_id)
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not group or not transaction:
        return False
    if transaction not in group.transactions:
        group.transactions.append(transaction)
        db.commit()
    return True


def remove_transaction_from_group(
    db: Session, group_id: int, transaction_id: int
) -> bool:
    """Remove a transaction from a trade group. Returns True if successful."""
    group = get_trade_group_by_id(db, group_id)
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not group or not transaction:
        return False
    if transaction in group.transactions:
        group.transactions.remove(transaction)
        db.commit()
    return True


def get_group_transactions(db: Session, group_id: int) -> list[Transaction]:
    """Get all transactions in a trade group."""
    group = get_trade_group_by_id(db, group_id)
    if not group:
        return []
    return list(group.transactions)


def get_transaction_groups(db: Session, transaction_id: int) -> list[TradeGroup]:
    """Get all trade groups that contain a transaction."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        return []
    return list(transaction.trade_groups)


def calculate_group_pl(db: Session, group_id: int) -> Decimal:
    """Calculate the combined P/L for all transactions in a trade group."""
    group = get_trade_group_by_id(db, group_id)
    if not group or not group.transactions:
        return Decimal("0")
    return sum((t.amount for t in group.transactions), start=Decimal("0"))


def get_ungrouped_multileg_candidates(db: Session) -> dict[str, list[Transaction]]:
    """
    Find transactions with the same external_reference_id that aren't
    already in a trade group together. Returns dict of ext_ref_id -> transactions.
    """
    # Get all external_reference_ids with multiple transactions
    multi_leg_refs = (
        db.query(Transaction.external_reference_id)
        .filter(Transaction.external_reference_id.isnot(None))
        .group_by(Transaction.external_reference_id)
        .having(func.count(Transaction.id) > 1)
        .all()
    )

    result = {}
    for (ext_ref_id,) in multi_leg_refs:
        transactions = (
            db.query(Transaction)
            .filter(Transaction.external_reference_id == ext_ref_id)
            .order_by(Transaction.trade_date, Transaction.symbol)
            .all()
        )

        # Check if these transactions are already fully grouped together
        if transactions:
            first_groups = set(g.id for g in transactions[0].trade_groups)
            all_same_group = (
                all(
                    any(g.id in first_groups for g in t.trade_groups)
                    for t in transactions[1:]
                )
                if first_groups
                else False
            )

            if not all_same_group:
                result[ext_ref_id] = transactions

    return result


def create_group_from_external_reference(
    db: Session,
    external_reference_id: str,
    name: str | None = None,
    strategy_type: str | None = None,
) -> TradeGroup | None:
    """
    Create a trade group from all transactions with the given external_reference_id.
    Returns the created group, or None if no transactions found.
    """
    transactions = (
        db.query(Transaction)
        .filter(Transaction.external_reference_id == external_reference_id)
        .all()
    )
    if not transactions:
        return None

    # Generate a name if not provided
    if not name:
        symbols = set(t.symbol for t in transactions if t.symbol)
        date_str = transactions[0].trade_date.strftime("%Y-%m-%d")
        name = f"{', '.join(sorted(symbols))} - {date_str}"

    group = create_trade_group(db, name, strategy_type)
    for txn in transactions:
        group.transactions.append(txn)
    db.commit()
    db.refresh(group)
    return group
