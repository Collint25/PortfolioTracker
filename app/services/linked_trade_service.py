"""Service for linking opening and closing option trades using FIFO matching."""

from datetime import date
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.calculations import pl_calcs
from app.models import LinkedTrade, LinkedTradeLeg, Transaction
from app.services.filters import (
    LinkedTradeFilter,
    PaginationParams,
    apply_linked_trade_filters,
    apply_pagination,
)


class ContractKey(NamedTuple):
    """Unique identifier for an option contract."""

    account_id: int
    underlying_symbol: str
    option_type: str  # CALL or PUT
    strike_price: Decimal
    expiration_date: date


# --- Query Functions ---


def get_all_linked_trades(
    db: Session,
    filters: LinkedTradeFilter = LinkedTradeFilter(),
    pagination: PaginationParams = PaginationParams(),
) -> tuple[list[LinkedTrade], int]:
    """Get filtered, paginated linked trades."""
    query = db.query(LinkedTrade)

    # Apply filters
    query = apply_linked_trade_filters(query, filters)

    # Get total
    total = query.count()

    # Sort
    query = query.order_by(LinkedTrade.expiration_date.desc(), LinkedTrade.id.desc())

    # Paginate
    query = apply_pagination(query, pagination)

    linked_trades = query.all()
    return linked_trades, total


def get_linked_trade_by_id(db: Session, linked_trade_id: int) -> LinkedTrade | None:
    """Get a single linked trade with all legs."""
    return db.query(LinkedTrade).filter(LinkedTrade.id == linked_trade_id).first()


def get_unique_symbols(db: Session) -> list[str]:
    """Get all unique underlying symbols from linked trades."""
    results = (
        db.query(LinkedTrade.symbol)
        .distinct()
        .order_by(LinkedTrade.symbol)
        .all()
    )
    return [r[0] for r in results if r[0]]


def delete_linked_trade(db: Session, linked_trade_id: int) -> bool:
    """Delete a linked trade (unlink transactions). Returns True if deleted."""
    linked_trade = get_linked_trade_by_id(db, linked_trade_id)
    if not linked_trade:
        return False
    db.delete(linked_trade)
    db.commit()
    return True


def get_linked_trades_for_transaction(
    db: Session, transaction_id: int
) -> list[LinkedTrade]:
    """Get all linked trades that include a specific transaction."""
    return (
        db.query(LinkedTrade)
        .join(LinkedTradeLeg)
        .filter(LinkedTradeLeg.transaction_id == transaction_id)
        .all()
    )


def get_unlinked_option_transactions(
    db: Session, account_id: int | None = None
) -> list[Transaction]:
    """Find option transactions not yet in any linked trade."""
    # Subquery to find transaction IDs that are already linked
    linked_txn_ids = db.query(LinkedTradeLeg.transaction_id).scalar_subquery()

    query = db.query(Transaction).filter(
        Transaction.is_option,
        Transaction.option_action.isnot(None),
        ~Transaction.id.in_(linked_txn_ids),
    )

    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)

    return query.order_by(Transaction.trade_date).all()


def get_open_positions(db: Session, account_id: int | None = None) -> list[LinkedTrade]:
    """Get all linked trades that are not fully closed."""
    query = db.query(LinkedTrade).filter(LinkedTrade.is_closed.is_(False))

    if account_id is not None:
        query = query.filter(LinkedTrade.account_id == account_id)

    return query.order_by(LinkedTrade.expiration_date).all()


# --- Contract Discovery ---


def find_unique_contracts(
    db: Session, account_id: int | None = None
) -> list[ContractKey]:
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
            ContractKey(
                account_id=row.account_id,
                underlying_symbol=row.underlying_symbol,
                option_type=row.option_type,
                strike_price=row.strike_price,
                expiration_date=row.expiration_date,
            )
        )

    return contracts


# --- FIFO Matching Helpers ---


def _find_transactions_for_contract(
    db: Session, contract_key: ContractKey, actions: list[str]
) -> list[Transaction]:
    """Find transactions for a contract with specified actions, ordered by date."""
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


def _get_already_linked_ids(db: Session, transaction_ids: list[int]) -> set[int]:
    """Get set of transaction IDs that are already in linked trades."""
    if not transaction_ids:
        return set()
    return set(
        row[0]
        for row in db.query(LinkedTradeLeg.transaction_id)
        .filter(LinkedTradeLeg.transaction_id.in_(transaction_ids))
        .all()
    )


def _determine_direction(open_action: str) -> tuple[str, str]:
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


def _create_linked_trade(
    db: Session, contract_key: ContractKey, direction: str
) -> LinkedTrade:
    """Create a new LinkedTrade for the contract."""
    linked_trade = LinkedTrade(
        account_id=contract_key.account_id,
        instrument_type="OPTION",  # Old service only handled options
        symbol=contract_key.underlying_symbol,  # TradeLot uses 'symbol' not 'underlying_symbol'
        option_type=contract_key.option_type,
        strike_price=contract_key.strike_price,
        expiration_date=contract_key.expiration_date,
        direction=direction,
        total_opened_quantity=Decimal("0"),
        total_closed_quantity=Decimal("0"),
        is_auto_matched=True,
    )
    db.add(linked_trade)
    db.flush()  # Get ID
    return linked_trade


def _add_open_leg(
    db: Session,
    linked_trade: LinkedTrade,
    open_txn: Transaction,
    quantity: Decimal,
) -> None:
    """Add an opening leg to a linked trade."""
    leg = LinkedTradeLeg(
        linked_trade_id=linked_trade.id,
        transaction_id=open_txn.id,
        allocated_quantity=quantity,
        leg_type="OPEN",
        trade_date=open_txn.trade_date,
        price_per_contract=open_txn.price or Decimal("0"),
    )
    db.add(leg)
    linked_trade.total_opened_quantity += quantity


def _add_close_leg(
    db: Session,
    linked_trade: LinkedTrade,
    close_txn: Transaction,
    quantity: Decimal,
) -> None:
    """Add a closing leg to a linked trade."""
    leg = LinkedTradeLeg(
        linked_trade_id=linked_trade.id,
        transaction_id=close_txn.id,
        allocated_quantity=quantity,
        leg_type="CLOSE",
        trade_date=close_txn.trade_date,
        price_per_contract=close_txn.price or Decimal("0"),
    )
    db.add(leg)
    linked_trade.total_closed_quantity += quantity


# --- FIFO Matching ---


def auto_match_contract(db: Session, contract_key: ContractKey) -> list[LinkedTrade]:
    """
    Run FIFO matching for a single option contract.

    Returns list of LinkedTrades created/updated.
    """
    # Get opening transactions
    opens = _find_transactions_for_contract(
        db, contract_key, ["BUY_TO_OPEN", "SELL_TO_OPEN"]
    )
    if not opens:
        return []

    # Determine direction from first opening trade
    first_action = opens[0].option_action
    if not first_action:
        return []  # Can't determine direction without action
    direction, close_action = _determine_direction(first_action)

    # Get closing transactions
    closes = _find_transactions_for_contract(db, contract_key, [close_action])

    # Filter out already-linked transactions
    all_txn_ids = [t.id for t in opens + closes]
    already_linked = _get_already_linked_ids(db, all_txn_ids)
    opens = [t for t in opens if t.id not in already_linked]
    closes = [t for t in closes if t.id not in already_linked]

    if not opens:
        return []

    # Initialize tracking state
    open_remaining = _init_open_remaining(opens)
    linked_trades: list[LinkedTrade] = []
    current_link: LinkedTrade | None = None
    open_legs_added: set[int] = set()

    # Process each closing transaction
    for close_txn in closes:
        allocations = _allocate_close_to_opens(close_txn, opens, open_remaining)

        if allocations:
            # Create new linked trade if needed
            if current_link is None or current_link.is_closed:
                current_link = _create_linked_trade(db, contract_key, direction)
                linked_trades.append(current_link)
                open_legs_added = set()

            # Add open legs for all opens used by this close
            total_close_qty = Decimal("0")
            for open_txn, alloc_qty in allocations:
                if open_txn.id not in open_legs_added:
                    full_open_qty = (
                        abs(open_txn.quantity) if open_txn.quantity else Decimal("0")
                    )
                    _add_open_leg(db, current_link, open_txn, full_open_qty)
                    open_legs_added.add(open_txn.id)
                total_close_qty += alloc_qty

            # Add close leg
            _add_close_leg(db, current_link, close_txn, total_close_qty)

            # Check if position is fully closed
            if current_link.total_closed_quantity >= current_link.total_opened_quantity:
                current_link.is_closed = True
                current_link.realized_pl = calculate_linked_trade_pl(
                    db, current_link.id
                )

    # Handle remaining opens (position still open)
    for open_txn in opens:
        remaining = open_remaining.get(open_txn.id, Decimal("0"))
        if remaining > 0 and open_txn.id not in open_legs_added:
            if current_link is None or current_link.is_closed:
                current_link = _create_linked_trade(db, contract_key, direction)
                linked_trades.append(current_link)

            _add_open_leg(db, current_link, open_txn, remaining)

    return linked_trades


def auto_match_all(db: Session, account_id: int | None = None) -> dict:
    """
    Run FIFO matching on all unlinked option transactions.

    Returns summary: {created: int, contracts_processed: int, orphans: int}
    """
    contracts = find_unique_contracts(db, account_id)

    created = 0
    for contract in contracts:
        linked_trades = auto_match_contract(db, contract)
        created += len(linked_trades)

    db.commit()

    # Recalculate P/L for all linked trades (needed because legs aren't
    # committed during matching)
    recalculate_all_pl(db)

    # Count orphan transactions (unlinked after matching)
    orphans = len(get_unlinked_option_transactions(db, account_id))

    return {
        "created": created,
        "contracts_processed": len(contracts),
        "orphans": orphans,
    }


# --- P/L Calculation ---


def calculate_linked_trade_pl(db: Session, linked_trade_id: int) -> Decimal:
    """
    Calculate realized P/L for a linked trade.

    Loads the trade and delegates to pl_calcs module.
    """
    linked_trade = get_linked_trade_by_id(db, linked_trade_id)
    if not linked_trade:
        return Decimal("0")
    return pl_calcs.linked_trade_pl(linked_trade)


def recalculate_all_pl(db: Session) -> int:
    """Recalculate P/L for all linked trades. Returns count updated."""
    linked_trades = db.query(LinkedTrade).all()
    count = 0

    for lt in linked_trades:
        new_pl = calculate_linked_trade_pl(db, lt.id)
        if lt.realized_pl != new_pl:
            lt.realized_pl = new_pl
            count += 1

    db.commit()
    return count


# --- Summary Functions ---


def get_pl_summary(db: Session, account_id: int | None = None) -> dict:
    """Get P/L summary statistics."""
    query = db.query(LinkedTrade)

    if account_id is not None:
        query = query.filter(LinkedTrade.account_id == account_id)

    return pl_calcs.pl_summary(query.all())
