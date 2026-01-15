"""Service for linking opening and closing option trades using FIFO matching."""

from datetime import date
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.models import LinkedTrade, LinkedTradeLeg, Transaction


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
    *,
    account_id: int | None = None,
    underlying_symbol: str | None = None,
    is_closed: bool | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[LinkedTrade], int]:
    """Get filtered, paginated linked trades."""
    query = db.query(LinkedTrade)

    if account_id is not None:
        query = query.filter(LinkedTrade.account_id == account_id)
    if underlying_symbol is not None:
        query = query.filter(LinkedTrade.underlying_symbol == underlying_symbol)
    if is_closed is not None:
        query = query.filter(LinkedTrade.is_closed == is_closed)

    total = query.count()
    linked_trades = (
        query.order_by(LinkedTrade.expiration_date.desc(), LinkedTrade.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return linked_trades, total


def get_linked_trade_by_id(db: Session, linked_trade_id: int) -> LinkedTrade | None:
    """Get a single linked trade with all legs."""
    return db.query(LinkedTrade).filter(LinkedTrade.id == linked_trade_id).first()


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
        Transaction.is_option == True,
        Transaction.option_action.isnot(None),
        ~Transaction.id.in_(linked_txn_ids),
    )

    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)

    return query.order_by(Transaction.trade_date).all()


def get_open_positions(db: Session, account_id: int | None = None) -> list[LinkedTrade]:
    """Get all linked trades that are not fully closed."""
    query = db.query(LinkedTrade).filter(LinkedTrade.is_closed == False)

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
        Transaction.is_option == True,
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


# --- FIFO Matching ---


def auto_match_contract(db: Session, contract_key: ContractKey) -> list[LinkedTrade]:
    """
    Run FIFO matching for a single option contract.

    Returns list of LinkedTrades created/updated.
    """
    # Determine direction based on opening action
    # LONG: BUY_TO_OPEN -> SELL_TO_CLOSE
    # SHORT: SELL_TO_OPEN -> BUY_TO_CLOSE

    # Get opening transactions (BUY_TO_OPEN or SELL_TO_OPEN)
    opens = (
        db.query(Transaction)
        .filter(
            Transaction.account_id == contract_key.account_id,
            Transaction.underlying_symbol == contract_key.underlying_symbol,
            Transaction.option_type == contract_key.option_type,
            Transaction.strike_price == contract_key.strike_price,
            Transaction.expiration_date == contract_key.expiration_date,
            Transaction.option_action.in_(["BUY_TO_OPEN", "SELL_TO_OPEN"]),
        )
        .order_by(Transaction.trade_date, Transaction.id)
        .all()
    )

    if not opens:
        return []

    # Determine direction from first opening trade
    first_open = opens[0]
    if first_open.option_action == "BUY_TO_OPEN":
        direction = "LONG"
        close_action = "SELL_TO_CLOSE"
    else:
        direction = "SHORT"
        close_action = "BUY_TO_CLOSE"

    # Get closing transactions
    closes = (
        db.query(Transaction)
        .filter(
            Transaction.account_id == contract_key.account_id,
            Transaction.underlying_symbol == contract_key.underlying_symbol,
            Transaction.option_type == contract_key.option_type,
            Transaction.strike_price == contract_key.strike_price,
            Transaction.expiration_date == contract_key.expiration_date,
            Transaction.option_action == close_action,
        )
        .order_by(Transaction.trade_date, Transaction.id)
        .all()
    )

    # Check which transactions are already linked
    all_txn_ids = [t.id for t in opens + closes]
    already_linked = set(
        row[0]
        for row in db.query(LinkedTradeLeg.transaction_id)
        .filter(LinkedTradeLeg.transaction_id.in_(all_txn_ids))
        .all()
    )

    # Filter to unlinked transactions only
    opens = [t for t in opens if t.id not in already_linked]
    closes = [t for t in closes if t.id not in already_linked]

    if not opens:
        return []

    # Track remaining quantity per opening transaction
    open_remaining: dict[int, Decimal] = {}
    for t in opens:
        qty = abs(t.quantity) if t.quantity else Decimal("0")
        open_remaining[t.id] = qty

    linked_trades: list[LinkedTrade] = []
    current_link: LinkedTrade | None = None
    open_legs_added: set[int] = set()

    def get_next_open_with_remaining() -> Transaction | None:
        """Find first open transaction with remaining quantity (FIFO)."""
        for t in opens:
            if open_remaining.get(t.id, Decimal("0")) > 0:
                return t
        return None

    # Process each closing transaction
    for close_txn in closes:
        close_qty_remaining = abs(close_txn.quantity) if close_txn.quantity else Decimal("0")
        close_allocations: list[tuple[Transaction, Decimal]] = []  # (open_txn, alloc_qty)

        while close_qty_remaining > 0:
            open_txn = get_next_open_with_remaining()
            if not open_txn:
                # No more opens to match - orphan close
                break

            # Calculate allocation
            open_qty = open_remaining[open_txn.id]
            alloc_qty = min(close_qty_remaining, open_qty)

            close_allocations.append((open_txn, alloc_qty))
            open_remaining[open_txn.id] -= alloc_qty
            close_qty_remaining -= alloc_qty

        # Now create/update linked trade with all allocations for this close
        if close_allocations:
            # Create new linked trade if needed
            if current_link is None or current_link.is_closed:
                current_link = LinkedTrade(
                    account_id=contract_key.account_id,
                    underlying_symbol=contract_key.underlying_symbol,
                    option_type=contract_key.option_type,
                    strike_price=contract_key.strike_price,
                    expiration_date=contract_key.expiration_date,
                    direction=direction,
                    total_opened_quantity=Decimal("0"),
                    total_closed_quantity=Decimal("0"),
                    is_auto_matched=True,
                )
                db.add(current_link)
                db.flush()  # Get ID
                linked_trades.append(current_link)
                open_legs_added = set()

            # Add open legs for all opens used by this close
            total_close_qty = Decimal("0")
            for open_txn, alloc_qty in close_allocations:
                if open_txn.id not in open_legs_added:
                    full_open_qty = abs(open_txn.quantity) if open_txn.quantity else Decimal("0")
                    open_leg = LinkedTradeLeg(
                        linked_trade_id=current_link.id,
                        transaction_id=open_txn.id,
                        allocated_quantity=full_open_qty,
                        leg_type="OPEN",
                        trade_date=open_txn.trade_date,
                        price_per_contract=open_txn.price or Decimal("0"),
                    )
                    db.add(open_leg)
                    current_link.total_opened_quantity += full_open_qty
                    open_legs_added.add(open_txn.id)
                total_close_qty += alloc_qty

            # Add close leg for total allocation
            close_leg = LinkedTradeLeg(
                linked_trade_id=current_link.id,
                transaction_id=close_txn.id,
                allocated_quantity=total_close_qty,
                leg_type="CLOSE",
                trade_date=close_txn.trade_date,
                price_per_contract=close_txn.price or Decimal("0"),
            )
            db.add(close_leg)
            current_link.total_closed_quantity += total_close_qty

            # Check if position is fully closed (after processing complete close)
            if current_link.total_closed_quantity >= current_link.total_opened_quantity:
                current_link.is_closed = True
                current_link.realized_pl = calculate_linked_trade_pl(db, current_link.id)

    # Handle remaining opens (position still open)
    for open_txn in opens:
        remaining = open_remaining.get(open_txn.id, Decimal("0"))
        if remaining > 0 and open_txn.id not in open_legs_added:
            # Create linked trade for open position
            if current_link is None or current_link.is_closed:
                current_link = LinkedTrade(
                    account_id=contract_key.account_id,
                    underlying_symbol=contract_key.underlying_symbol,
                    option_type=contract_key.option_type,
                    strike_price=contract_key.strike_price,
                    expiration_date=contract_key.expiration_date,
                    direction=direction,
                    total_opened_quantity=remaining,
                    total_closed_quantity=Decimal("0"),
                    is_closed=False,
                    is_auto_matched=True,
                )
                db.add(current_link)
                db.flush()
                linked_trades.append(current_link)

            open_leg = LinkedTradeLeg(
                linked_trade_id=current_link.id,
                transaction_id=open_txn.id,
                allocated_quantity=remaining,
                leg_type="OPEN",
                trade_date=open_txn.trade_date,
                price_per_contract=open_txn.price or Decimal("0"),
            )
            db.add(open_leg)

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

    P/L = sum of all transaction amounts in the linked trade.
    For options: positive amount = credit (received money), negative = debit (paid money)
    """
    linked_trade = get_linked_trade_by_id(db, linked_trade_id)
    if not linked_trade:
        return Decimal("0")

    total_pl = Decimal("0")
    for leg in linked_trade.legs:
        # Get the transaction's amount (cash impact)
        txn = leg.transaction
        if txn and txn.amount:
            # Proportion the amount based on allocated quantity vs total quantity
            txn_qty = abs(txn.quantity) if txn.quantity else Decimal("1")
            if txn_qty > 0:
                proportion = leg.allocated_quantity / txn_qty
                total_pl += txn.amount * proportion

    return total_pl


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

    linked_trades = query.all()

    total_pl = Decimal("0")
    winners = 0
    losers = 0
    open_count = 0
    closed_count = 0

    for lt in linked_trades:
        if lt.is_closed:
            closed_count += 1
            total_pl += lt.realized_pl
            if lt.realized_pl > 0:
                winners += 1
            elif lt.realized_pl < 0:
                losers += 1
        else:
            open_count += 1

    win_rate = (winners / closed_count * 100) if closed_count > 0 else 0

    return {
        "total_pl": total_pl,
        "winners": winners,
        "losers": losers,
        "win_rate": win_rate,
        "open_count": open_count,
        "closed_count": closed_count,
    }
