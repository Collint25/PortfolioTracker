"""Service for linking opening and closing trades using FIFO matching.

Supports both options and stocks with the following key behaviors:
- Options: BUY_TO_OPEN/SELL_TO_OPEN opens, opposite action closes
- Stocks: BUY opens, SELL closes (long positions only for now)
- Lots are only created when there's something to link:
  - 2+ opens for the same position, OR
  - Any close exists for the position
- Single open with no other transactions = no lot created
"""

from datetime import date
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.calculations import pl_calcs
from app.models import LotTransaction, TradeLot, Transaction
from app.services.filters import (
    LotFilter,
    PaginationParams,
    apply_lot_filters,
    apply_pagination,
)


class StockKey(NamedTuple):
    """Position key for stocks."""

    account_id: int
    symbol: str


class OptionKey(NamedTuple):
    """Unique identifier for an option contract."""

    account_id: int
    underlying_symbol: str
    option_type: str  # CALL or PUT
    strike_price: Decimal
    expiration_date: date


# Type alias for position keys
PositionKey = StockKey | OptionKey


# --- Query Functions ---


def get_all_lots(
    db: Session,
    filters: LotFilter | None = None,
    pagination: PaginationParams | None = None,
) -> tuple[list[TradeLot], int]:
    """Get filtered, paginated lots."""
    query = db.query(TradeLot)

    # Apply filters
    if filters:
        query = apply_lot_filters(query, filters)

    # Get total
    total = query.count()

    # Sort - options by expiration, stocks by id
    query = query.order_by(
        TradeLot.expiration_date.desc().nullslast(), TradeLot.id.desc()
    )

    # Paginate
    if pagination:
        query = apply_pagination(query, pagination)

    lots = query.all()
    return lots, total


def get_lot_by_id(db: Session, lot_id: int) -> TradeLot | None:
    """Get a single lot with all legs."""
    return db.query(TradeLot).filter(TradeLot.id == lot_id).first()


def get_unique_symbols(db: Session) -> list[str]:
    """Get all unique symbols from lots."""
    results = db.query(TradeLot.symbol).distinct().order_by(TradeLot.symbol).all()
    return [r[0] for r in results if r[0]]


def delete_lot(db: Session, lot_id: int) -> bool:
    """Delete a lot (unlink transactions). Returns True if deleted."""
    lot = get_lot_by_id(db, lot_id)
    if not lot:
        return False
    db.delete(lot)
    db.commit()
    return True


def get_lots_for_transaction(db: Session, transaction_id: int) -> list[TradeLot]:
    """Get all lots that include a specific transaction."""
    return (
        db.query(TradeLot)
        .join(LotTransaction)
        .filter(LotTransaction.transaction_id == transaction_id)
        .all()
    )


def get_unlinked_option_transactions(
    db: Session, account_id: int | None = None
) -> list[Transaction]:
    """Find option transactions not yet in any lot."""
    # Subquery to find transaction IDs that are already linked
    linked_txn_ids = db.query(LotTransaction.transaction_id).scalar_subquery()

    query = db.query(Transaction).filter(
        Transaction.is_option,
        Transaction.option_action.isnot(None),
        ~Transaction.id.in_(linked_txn_ids),
    )

    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)

    return query.order_by(Transaction.trade_date).all()


def get_unlinked_stock_transactions(
    db: Session, account_id: int | None = None
) -> list[Transaction]:
    """Find stock transactions not yet in any lot."""
    linked_txn_ids = db.query(LotTransaction.transaction_id).scalar_subquery()

    query = db.query(Transaction).filter(
        Transaction.is_option.is_(False),
        Transaction.type.in_(["BUY", "SELL"]),
        ~Transaction.id.in_(linked_txn_ids),
    )

    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)

    return query.order_by(Transaction.trade_date).all()


def get_open_positions(db: Session, account_id: int | None = None) -> list[TradeLot]:
    """Get all lots that are not fully closed."""
    query = db.query(TradeLot).filter(TradeLot.is_closed.is_(False))

    if account_id is not None:
        query = query.filter(TradeLot.account_id == account_id)

    return query.order_by(TradeLot.expiration_date.nullslast()).all()


# --- Position Discovery ---


def find_unique_option_contracts(
    db: Session, account_id: int | None = None
) -> list[OptionKey]:
    """Find all unique option contracts in the database."""
    query = db.query(
        Transaction.account_id,
        Transaction.underlying_symbol,
        Transaction.option_type,
        Transaction.strike_price,
        Transaction.expiration_date,
    ).filter(
        Transaction.is_option,
        Transaction.option_action.isnot(None),
        Transaction.underlying_symbol.isnot(None),
        Transaction.option_type.isnot(None),
        Transaction.strike_price.isnot(None),
        Transaction.expiration_date.isnot(None),
    )

    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)

    query = query.distinct()

    contracts = []
    for row in query.all():
        contracts.append(
            OptionKey(
                account_id=row.account_id,
                underlying_symbol=row.underlying_symbol,
                option_type=row.option_type,
                strike_price=row.strike_price,
                expiration_date=row.expiration_date,
            )
        )

    return contracts


def find_unique_stock_positions(
    db: Session, account_id: int | None = None
) -> list[StockKey]:
    """Find all unique stock positions (account_id + symbol) in the database."""
    query = db.query(
        Transaction.account_id,
        Transaction.symbol,
    ).filter(
        Transaction.is_option.is_(False),
        Transaction.type.in_(["BUY", "SELL"]),
        Transaction.symbol.isnot(None),
    )

    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)

    query = query.distinct()

    positions = []
    for row in query.all():
        positions.append(
            StockKey(
                account_id=row.account_id,
                symbol=row.symbol,
            )
        )

    return positions


# --- FIFO Matching Helpers ---


def _find_option_transactions_for_contract(
    db: Session, contract_key: OptionKey, actions: list[str]
) -> list[Transaction]:
    """Find option transactions for a contract with specified actions, ordered by date."""
    return (
        db.query(Transaction)
        .filter(
            Transaction.account_id == contract_key.account_id,
            Transaction.underlying_symbol == contract_key.underlying_symbol,
            Transaction.option_type == contract_key.option_type,
            Transaction.strike_price == contract_key.strike_price,
            Transaction.expiration_date == contract_key.expiration_date,
            Transaction.option_action.in_(actions),
        )
        .order_by(Transaction.trade_date, Transaction.id)
        .all()
    )


def _find_stock_transactions_for_position(
    db: Session, position_key: StockKey, txn_types: list[str]
) -> list[Transaction]:
    """Find stock transactions for a position with specified types, ordered by date."""
    return (
        db.query(Transaction)
        .filter(
            Transaction.account_id == position_key.account_id,
            Transaction.symbol == position_key.symbol,
            Transaction.is_option.is_(False),
            Transaction.type.in_(txn_types),
        )
        .order_by(Transaction.trade_date, Transaction.id)
        .all()
    )


def _get_already_linked_ids(db: Session, transaction_ids: list[int]) -> set[int]:
    """Get set of transaction IDs that are already in lots."""
    if not transaction_ids:
        return set()
    return set(
        row[0]
        for row in db.query(LotTransaction.transaction_id)
        .filter(LotTransaction.transaction_id.in_(transaction_ids))
        .all()
    )


def _determine_option_direction(open_action: str) -> tuple[str, str]:
    """
    Determine trade direction and closing action from open action.

    Returns: (direction, close_action)
    """
    if open_action == "BUY_TO_OPEN":
        return "LONG", "SELL_TO_CLOSE"
    return "SHORT", "BUY_TO_CLOSE"


def _init_open_remaining(opens: list[Transaction]) -> dict[int, Decimal]:
    """Initialize tracking dict for remaining quantity per opening transaction."""
    return {t.id: abs(t.quantity) if t.quantity else Decimal("0") for t in opens}


def _get_next_open_with_remaining(
    opens: list[Transaction], open_remaining: dict[int, Decimal]
) -> Transaction | None:
    """Find first open transaction with remaining quantity (FIFO)."""
    for t in opens:
        if open_remaining.get(t.id, Decimal("0")) > 0:
            return t
    return None


def _allocate_close_to_opens(
    close_txn: Transaction,
    opens: list[Transaction],
    open_remaining: dict[int, Decimal],
) -> list[tuple[Transaction, Decimal]]:
    """
    Allocate a closing transaction to opening transactions using FIFO.

    Returns list of (open_txn, allocated_qty) tuples.
    """
    close_qty_remaining = (
        abs(close_txn.quantity) if close_txn.quantity else Decimal("0")
    )
    allocations: list[tuple[Transaction, Decimal]] = []

    while close_qty_remaining > 0:
        open_txn = _get_next_open_with_remaining(opens, open_remaining)
        if not open_txn:
            break

        open_qty = open_remaining[open_txn.id]
        alloc_qty = min(close_qty_remaining, open_qty)

        allocations.append((open_txn, alloc_qty))
        open_remaining[open_txn.id] -= alloc_qty
        close_qty_remaining -= alloc_qty

    return allocations


def _create_lot(
    db: Session, key: PositionKey, direction: str, instrument_type: str
) -> TradeLot:
    """Create a new TradeLot for the position."""
    if isinstance(key, StockKey):
        lot = TradeLot(
            account_id=key.account_id,
            symbol=key.symbol,
            instrument_type=instrument_type,
            direction=direction,
            total_opened_quantity=Decimal("0"),
            total_closed_quantity=Decimal("0"),
            is_auto_matched=True,
        )
    else:
        # OptionKey
        lot = TradeLot(
            account_id=key.account_id,
            symbol=key.underlying_symbol,
            instrument_type=instrument_type,
            option_type=key.option_type,
            strike_price=key.strike_price,
            expiration_date=key.expiration_date,
            direction=direction,
            total_opened_quantity=Decimal("0"),
            total_closed_quantity=Decimal("0"),
            is_auto_matched=True,
        )
    db.add(lot)
    db.flush()  # Get ID
    return lot


def _add_open_leg(
    db: Session,
    lot: TradeLot,
    open_txn: Transaction,
    quantity: Decimal,
) -> None:
    """Add an opening leg to a lot."""
    leg = LotTransaction(
        lot_id=lot.id,
        transaction_id=open_txn.id,
        allocated_quantity=quantity,
        leg_type="OPEN",
        trade_date=open_txn.trade_date,
        price_per_contract=open_txn.price or Decimal("0"),
    )
    db.add(leg)
    lot.total_opened_quantity += quantity


def _add_close_leg(
    db: Session,
    lot: TradeLot,
    close_txn: Transaction,
    quantity: Decimal,
) -> None:
    """Add a closing leg to a lot."""
    leg = LotTransaction(
        lot_id=lot.id,
        transaction_id=close_txn.id,
        allocated_quantity=quantity,
        leg_type="CLOSE",
        trade_date=close_txn.trade_date,
        price_per_contract=close_txn.price or Decimal("0"),
    )
    db.add(leg)
    lot.total_closed_quantity += quantity


# --- FIFO Matching ---


def auto_match_contract(db: Session, contract_key: OptionKey) -> list[TradeLot]:
    """
    Run FIFO matching for a single option contract.

    Returns list of TradeLots created/updated.
    """
    # Get opening transactions
    opens = _find_option_transactions_for_contract(
        db, contract_key, ["BUY_TO_OPEN", "SELL_TO_OPEN"]
    )
    if not opens:
        return []

    # Determine direction from first opening trade
    first_action = opens[0].option_action
    if not first_action:
        return []  # Can't determine direction without action
    direction, close_action = _determine_option_direction(first_action)

    # Get closing transactions
    closes = _find_option_transactions_for_contract(db, contract_key, [close_action])

    # Filter out already-linked transactions
    all_txn_ids = [t.id for t in opens + closes]
    already_linked = _get_already_linked_ids(db, all_txn_ids)
    opens = [t for t in opens if t.id not in already_linked]
    closes = [t for t in closes if t.id not in already_linked]

    if not opens:
        return []

    # NEW RULE: Only create lot if there's something to link
    has_closes = len(closes) > 0
    has_multiple_opens = len(opens) > 1

    if not has_closes and not has_multiple_opens:
        return []  # Nothing to link - don't create lot

    # Initialize tracking state
    open_remaining = _init_open_remaining(opens)
    lots: list[TradeLot] = []
    current_lot: TradeLot | None = None
    open_legs_added: set[int] = set()

    # Process each closing transaction
    for close_txn in closes:
        allocations = _allocate_close_to_opens(close_txn, opens, open_remaining)

        if allocations:
            # Create new lot if needed
            if current_lot is None or current_lot.is_closed:
                current_lot = _create_lot(db, contract_key, direction, "OPTION")
                lots.append(current_lot)
                open_legs_added = set()

            # Add open legs for all opens used by this close
            total_close_qty = Decimal("0")
            for open_txn, alloc_qty in allocations:
                if open_txn.id not in open_legs_added:
                    full_open_qty = (
                        abs(open_txn.quantity) if open_txn.quantity else Decimal("0")
                    )
                    _add_open_leg(db, current_lot, open_txn, full_open_qty)
                    open_legs_added.add(open_txn.id)
                total_close_qty += alloc_qty

            # Add close leg
            _add_close_leg(db, current_lot, close_txn, total_close_qty)

            # Check if position is fully closed
            if current_lot is not None:
                if (
                    current_lot.total_closed_quantity
                    >= current_lot.total_opened_quantity
                ):
                    current_lot.is_closed = True
                    current_lot.realized_pl = calculate_linked_trade_pl(
                        db, current_lot.id
                    )

    # Handle remaining opens (position still open)
    for open_txn in opens:
        remaining = open_remaining.get(open_txn.id, Decimal("0"))
        if remaining > 0 and open_txn.id not in open_legs_added:
            if current_lot is None or current_lot.is_closed:
                current_lot = _create_lot(db, contract_key, direction, "OPTION")
                lots.append(current_lot)

            _add_open_leg(db, current_lot, open_txn, remaining)
            open_legs_added.add(open_txn.id)

    return lots


def match_stock_position(db: Session, position_key: StockKey) -> list[TradeLot]:
    """
    Run FIFO matching for a single stock position.

    For stocks: BUY = open, SELL = close (long positions).
    Returns list of TradeLots created.
    """
    # Get buy transactions (opens)
    opens = _find_stock_transactions_for_position(db, position_key, ["BUY"])
    if not opens:
        return []

    # Get sell transactions (closes)
    closes = _find_stock_transactions_for_position(db, position_key, ["SELL"])

    # Filter out already-linked transactions
    all_txn_ids = [t.id for t in opens + closes]
    already_linked = _get_already_linked_ids(db, all_txn_ids)
    opens = [t for t in opens if t.id not in already_linked]
    closes = [t for t in closes if t.id not in already_linked]

    if not opens:
        return []

    # NEW RULE: Only create lot if there's something to link
    has_closes = len(closes) > 0
    has_multiple_opens = len(opens) > 1

    if not has_closes and not has_multiple_opens:
        return []  # Nothing to link - don't create lot

    # Initialize tracking state
    open_remaining = _init_open_remaining(opens)
    lots: list[TradeLot] = []
    current_lot: TradeLot | None = None
    open_legs_added: set[int] = set()

    # Direction is always LONG for stocks (BUY to open)
    direction = "LONG"

    # Process each closing transaction
    for close_txn in closes:
        allocations = _allocate_close_to_opens(close_txn, opens, open_remaining)

        if allocations:
            # Create new lot if needed
            if current_lot is None or current_lot.is_closed:
                current_lot = _create_lot(db, position_key, direction, "STOCK")
                lots.append(current_lot)
                open_legs_added = set()

            # Add open legs for all opens used by this close
            total_close_qty = Decimal("0")
            for open_txn, alloc_qty in allocations:
                if open_txn.id not in open_legs_added:
                    full_open_qty = (
                        abs(open_txn.quantity) if open_txn.quantity else Decimal("0")
                    )
                    _add_open_leg(db, current_lot, open_txn, full_open_qty)
                    open_legs_added.add(open_txn.id)
                total_close_qty += alloc_qty

            # Add close leg
            _add_close_leg(db, current_lot, close_txn, total_close_qty)

            # Check if position is fully closed
            if current_lot is not None:
                if (
                    current_lot.total_closed_quantity
                    >= current_lot.total_opened_quantity
                ):
                    current_lot.is_closed = True
                    current_lot.realized_pl = calculate_linked_trade_pl(
                        db, current_lot.id
                    )

    # Handle remaining opens (position still open)
    for open_txn in opens:
        remaining = open_remaining.get(open_txn.id, Decimal("0"))
        if remaining > 0 and open_txn.id not in open_legs_added:
            if current_lot is None or current_lot.is_closed:
                current_lot = _create_lot(db, position_key, direction, "STOCK")
                lots.append(current_lot)

            _add_open_leg(db, current_lot, open_txn, remaining)
            open_legs_added.add(open_txn.id)

    return lots


def auto_match_all(db: Session, account_id: int | None = None) -> dict:
    """
    Run FIFO matching on all unlinked option transactions.

    Returns summary: {created: int, contracts_processed: int, orphans: int}
    """
    contracts = find_unique_option_contracts(db, account_id)

    created = 0
    for contract in contracts:
        lots = auto_match_contract(db, contract)
        created += len(lots)

    db.commit()

    # Recalculate P/L for all lots (needed because legs aren't
    # committed during matching)
    recalculate_all_pl(db)

    # Count orphan transactions (unlinked after matching)
    orphans = len(get_unlinked_option_transactions(db, account_id))

    return {
        "created": created,
        "contracts_processed": len(contracts),
        "orphans": orphans,
    }


def match_all(db: Session, account_id: int | None = None) -> dict:
    """
    Match all unlinked transactions (both options and stocks).

    Returns summary: {
        created: int,
        options_processed: int,
        stocks_processed: int,
        orphan_options: int,
        orphan_stocks: int
    }
    """
    # Match options
    option_contracts = find_unique_option_contracts(db, account_id)
    options_created = 0
    for contract in option_contracts:
        lots = auto_match_contract(db, contract)
        options_created += len(lots)

    # Match stocks
    stock_positions = find_unique_stock_positions(db, account_id)
    stocks_created = 0
    for position in stock_positions:
        lots = match_stock_position(db, position)
        stocks_created += len(lots)

    db.commit()

    # Recalculate P/L for all lots
    recalculate_all_pl(db)

    # Count orphan transactions
    orphan_options = len(get_unlinked_option_transactions(db, account_id))
    orphan_stocks = len(get_unlinked_stock_transactions(db, account_id))

    return {
        "created": options_created + stocks_created,
        "options_processed": len(option_contracts),
        "stocks_processed": len(stock_positions),
        "orphan_options": orphan_options,
        "orphan_stocks": orphan_stocks,
    }


def rematch_all(db: Session, account_id: int | None = None) -> dict:
    """
    Delete all lots and rebuild from scratch.

    Returns same summary as match_all.
    """
    # Delete existing lots
    query = db.query(TradeLot)
    if account_id:
        query = query.filter(TradeLot.account_id == account_id)
    query.delete(synchronize_session=False)
    db.commit()

    # Re-run matching
    return match_all(db, account_id)


# --- P/L Calculation ---


def calculate_linked_trade_pl(db: Session, lot_id: int) -> Decimal:
    """
    Calculate realized P/L for a lot.

    Loads the lot and delegates to pl_calcs module.
    """
    lot = get_lot_by_id(db, lot_id)
    if not lot:
        return Decimal("0")
    return pl_calcs.linked_trade_pl(lot)


def recalculate_all_pl(db: Session) -> int:
    """Recalculate P/L for all lots. Returns count updated."""
    lots = db.query(TradeLot).all()
    count = 0

    for lot in lots:
        new_pl = calculate_linked_trade_pl(db, lot.id)
        if lot.realized_pl != new_pl:
            lot.realized_pl = new_pl
            count += 1

    db.commit()
    return count


# --- Summary Functions ---


def get_pl_summary(
    db: Session,
    account_id: int | None = None,
    account_ids: list[int] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Get P/L summary statistics with optional date filtering."""
    query = db.query(TradeLot)

    if account_id is not None:
        query = query.filter(TradeLot.account_id == account_id)
    elif account_ids:
        query = query.filter(TradeLot.account_id.in_(account_ids))

    # Date filtering requires joining to LotTransaction to find close date
    if start_date or end_date:
        # Subquery: get lot IDs with closing leg in date range
        closing_legs = db.query(LotTransaction.lot_id).filter(
            LotTransaction.leg_type == "CLOSE"
        )
        if start_date:
            closing_legs = closing_legs.filter(LotTransaction.trade_date >= start_date)
        if end_date:
            closing_legs = closing_legs.filter(LotTransaction.trade_date <= end_date)

        query = query.filter(TradeLot.id.in_(closing_legs.scalar_subquery()))

    return pl_calcs.pl_summary(query.all())
