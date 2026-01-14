from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Account, Position, Transaction
from app.services.snaptrade_client import (
    fetch_accounts,
    fetch_holdings,
    fetch_transactions,
    get_snaptrade_client,
    get_user_credentials,
)


def sync_all(db: Session) -> dict[str, int]:
    """
    Sync all data from SnapTrade.

    Returns counts of synced records.
    """
    client = get_snaptrade_client()
    user_id, user_secret = get_user_credentials()

    # Sync accounts first
    account_count = sync_accounts(db, client, user_id, user_secret)

    # Sync positions for each account
    position_count = sync_positions(db, client, user_id, user_secret)

    # Sync transactions
    transaction_count = sync_transactions(db, client, user_id, user_secret)

    return {
        "accounts": account_count,
        "positions": position_count,
        "transactions": transaction_count,
    }


def sync_accounts(
    db: Session, client, user_id: str, user_secret: str
) -> int:
    """Sync accounts from SnapTrade."""
    accounts_data = fetch_accounts(client, user_id, user_secret)
    count = 0

    for data in accounts_data:
        snaptrade_id = data.get("id") or data.get("brokerage_account_id")
        if not snaptrade_id:
            continue

        account = db.query(Account).filter(
            Account.snaptrade_id == snaptrade_id
        ).first()

        if account:
            # Update existing
            account.name = data.get("name", account.name)
            account.account_number = data.get("number", account.account_number)
            account.account_type = data.get("meta", {}).get("type")
            account._raw_json = data
        else:
            # Create new
            account = Account(
                snaptrade_id=snaptrade_id,
                name=data.get("name", "Unknown"),
                account_number=data.get("number", ""),
                account_type=data.get("meta", {}).get("type"),
                institution_name=data.get("institution_name", "Fidelity"),
                _raw_json=data,
            )
            db.add(account)
        count += 1

    db.commit()
    return count


def sync_positions(
    db: Session, client, user_id: str, user_secret: str
) -> int:
    """Sync positions for all accounts."""
    accounts = db.query(Account).all()
    count = 0

    for account in accounts:
        holdings_data = fetch_holdings(
            client, user_id, user_secret, account.snaptrade_id
        )

        for data in holdings_data:
            # ID is nested: data.symbol.id - but this is per-security, not per-position
            # Create compound ID: account_id + symbol_id
            symbol_outer = data.get("symbol", {})
            symbol_id = symbol_outer.get("id") if isinstance(symbol_outer, dict) else None
            if not symbol_id:
                continue
            snaptrade_id = f"{account.snaptrade_id}:{symbol_id}"

            position = db.query(Position).filter(
                Position.snaptrade_id == snaptrade_id
            ).first()

            # Symbol string is nested: data.symbol.symbol.symbol
            symbol_inner = symbol_outer.get("symbol", {}) if isinstance(symbol_outer, dict) else {}
            symbol_str = symbol_inner.get("symbol", "") if isinstance(symbol_inner, dict) else str(symbol_inner)

            if position:
                # Update existing
                position.symbol = symbol_str
                position.quantity = Decimal(str(data.get("units", 0)))
                position.average_cost = _to_decimal(data.get("average_purchase_price"))
                position.current_price = _to_decimal(data.get("price"))
                position.currency = data.get("currency", {}).get("code", "USD")
                position._raw_json = data
            else:
                # Create new
                position = Position(
                    snaptrade_id=snaptrade_id,
                    account_id=account.id,
                    symbol=symbol_str,
                    quantity=Decimal(str(data.get("units", 0))),
                    average_cost=_to_decimal(data.get("average_purchase_price")),
                    current_price=_to_decimal(data.get("price")),
                    currency=data.get("currency", {}).get("code", "USD"),
                    _raw_json=data,
                )
                db.add(position)
            count += 1

    db.commit()
    return count


def sync_transactions(
    db: Session, client, user_id: str, user_secret: str
) -> int:
    """Sync all transactions."""
    transactions_data = fetch_transactions(client, user_id, user_secret)
    count = 0

    # Build account lookup by snaptrade_id
    accounts = {a.snaptrade_id: a.id for a in db.query(Account).all()}

    for data in transactions_data:
        snaptrade_id = data.get("id")
        if not snaptrade_id:
            continue

        transaction = db.query(Transaction).filter(
            Transaction.snaptrade_id == snaptrade_id
        ).first()

        # Get account_id from the transaction's account reference
        account_ref = data.get("account", {})
        account_snaptrade_id = account_ref.get("id") if isinstance(account_ref, dict) else None
        account_id = accounts.get(account_snaptrade_id) if account_snaptrade_id else None

        if not account_id:
            # Skip transactions without matching account
            continue

        symbol = data.get("symbol", {})
        symbol_str = symbol.get("symbol", "") if isinstance(symbol, dict) else str(symbol) if symbol else None

        trade_date = _parse_date(data.get("trade_date"))
        settlement_date = _parse_date(data.get("settlement_date"))

        if transaction:
            # Update existing
            transaction.symbol = symbol_str
            transaction.trade_date = trade_date
            transaction.settlement_date = settlement_date
            transaction.type = data.get("type", "UNKNOWN")
            transaction.quantity = _to_decimal(data.get("units"))
            transaction.price = _to_decimal(data.get("price"))
            transaction.amount = Decimal(str(data.get("amount", 0)))
            transaction.currency = data.get("currency", {}).get("code", "USD")
            transaction.description = data.get("description")
            transaction.external_reference_id = data.get("external_reference_id")
            transaction._raw_json = data
        else:
            # Create new
            transaction = Transaction(
                snaptrade_id=snaptrade_id,
                account_id=account_id,
                external_reference_id=data.get("external_reference_id"),
                symbol=symbol_str,
                trade_date=trade_date,
                settlement_date=settlement_date,
                type=data.get("type", "UNKNOWN"),
                quantity=_to_decimal(data.get("units")),
                price=_to_decimal(data.get("price")),
                amount=Decimal(str(data.get("amount", 0))),
                currency=data.get("currency", {}).get("code", "USD"),
                description=data.get("description"),
                _raw_json=data,
            )
            db.add(transaction)
        count += 1

    db.commit()
    return count


def _to_decimal(value) -> Decimal | None:
    """Convert value to Decimal, handling None."""
    if value is None:
        return None
    return Decimal(str(value))


def _parse_date(value) -> date | None:
    """Parse date string to date object."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    # Try ISO format
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None
