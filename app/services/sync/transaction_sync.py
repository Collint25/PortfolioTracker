"""Transaction synchronization from SnapTrade."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account, Transaction
from app.services.snaptrade_client import fetch_account_activities
from app.services.sync.snaptrade_parser import (
    extract_option_data,
    extract_currency,
    to_decimal,
    parse_date,
)


def sync_transactions(
    db: Session, client, user_id: str, user_secret: str
) -> int:
    """Sync all transactions using per-account endpoint."""
    accounts = db.query(Account).all()
    count = 0

    for account in accounts:
        count += _sync_account_transactions(db, client, user_id, user_secret, account)

    db.commit()
    return count


def _sync_account_transactions(
    db: Session, client, user_id: str, user_secret: str, account: Account
) -> int:
    """Sync transactions for a single account."""
    transactions_data = fetch_account_activities(
        client, user_id, user_secret, account.snaptrade_id
    )
    count = 0

    for data in transactions_data:
        snaptrade_id = data.get("id")
        if not snaptrade_id:
            continue

        transaction = _get_or_create_transaction(db, snaptrade_id, account.id)
        _update_transaction_fields(transaction, data)
        count += 1

    return count


def _get_or_create_transaction(
    db: Session, snaptrade_id: str, account_id: int
) -> Transaction:
    """Get existing transaction or create new one."""
    transaction = db.query(Transaction).filter(
        Transaction.snaptrade_id == snaptrade_id
    ).first()
    if not transaction:
        transaction = Transaction(snaptrade_id=snaptrade_id, account_id=account_id)
        db.add(transaction)
    return transaction


def _update_transaction_fields(transaction: Transaction, data: dict) -> None:
    """Update transaction fields from API data."""
    # Extract symbol
    symbol = data.get("symbol", {})
    symbol_str = symbol.get("symbol", "") if isinstance(symbol, dict) else str(symbol) if symbol else None

    # Extract option data
    option_data = extract_option_data(data)

    # Update basic fields
    transaction.symbol = symbol_str
    transaction.trade_date = parse_date(data.get("trade_date"))
    transaction.settlement_date = parse_date(data.get("settlement_date"))
    transaction.type = data.get("type", "UNKNOWN")
    transaction.quantity = to_decimal(data.get("units"))
    transaction.price = to_decimal(data.get("price"))
    transaction.amount = Decimal(str(data.get("amount", 0)))
    transaction.currency = extract_currency(data)
    transaction.description = data.get("description")
    transaction.external_reference_id = data.get("external_reference_id")
    transaction._raw_json = data

    # Update option fields
    transaction.is_option = option_data["is_option"]
    transaction.option_type = option_data["option_type"]
    transaction.strike_price = option_data["strike_price"]
    transaction.expiration_date = option_data["expiration_date"]
    transaction.option_ticker = option_data["option_ticker"]
    transaction.underlying_symbol = option_data["underlying_symbol"]
    transaction.option_action = option_data["option_action"]
