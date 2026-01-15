from datetime import date, datetime
from decimal import Decimal
import logging

from sqlalchemy.orm import Session

from app.models import Account, Position, Transaction
from app.services.snaptrade_client import (
    fetch_account_activities,
    fetch_accounts,
    fetch_holdings,
    fetch_option_holdings,
    get_snaptrade_client,
    get_user_credentials,
)

logger = logging.getLogger(__name__)


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
    """Sync positions for all accounts (stock and option holdings)."""
    accounts = db.query(Account).all()
    count = 0

    for account in accounts:
        # Sync regular stock holdings
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
                # Stock positions are not options
                position.is_option = False
                position.option_type = None
                position.strike_price = None
                position.expiration_date = None
                position.option_ticker = None
                position.underlying_symbol = None
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
                    is_option=False,
                )
                db.add(position)
            count += 1

        # Sync option holdings
        try:
            option_holdings = fetch_option_holdings(
                client, user_id, user_secret, account.snaptrade_id
            )
            for data in option_holdings:
                count += _sync_option_position(db, account, data)
        except Exception as e:
            # Log but don't fail if option holdings fetch fails
            logger.warning(f"Failed to fetch option holdings for account {account.id}: {e}")

    db.commit()
    return count


def _sync_option_position(db: Session, account: Account, data: dict) -> int:
    """Sync a single option position."""
    # Option holdings structure: symbol.option_symbol contains option details
    symbol_data = data.get("symbol", {})
    option_symbol = symbol_data.get("option_symbol", {}) if isinstance(symbol_data, dict) else {}
    if not option_symbol:
        return 0

    # Create unique ID from account + option symbol ID
    option_id = option_symbol.get("id")
    if not option_id:
        return 0
    snaptrade_id = f"{account.snaptrade_id}:opt:{option_id}"

    position = db.query(Position).filter(
        Position.snaptrade_id == snaptrade_id
    ).first()

    # Extract option details
    option_ticker = option_symbol.get("ticker", "")
    option_type = option_symbol.get("option_type")  # CALL or PUT
    strike_price = _to_decimal(option_symbol.get("strike_price"))
    expiration_date = _parse_date(option_symbol.get("expiration_date"))

    # Get underlying symbol
    underlying = option_symbol.get("underlying_symbol", {})
    underlying_symbol = underlying.get("symbol") if isinstance(underlying, dict) else None
    # Use underlying symbol as the display symbol
    symbol_str = underlying_symbol or option_ticker

    # Get position data
    quantity = Decimal(str(data.get("units", 0)))
    average_cost = _to_decimal(data.get("average_purchase_price"))
    current_price = _to_decimal(data.get("price"))
    # Currency might be None in option holdings response
    currency_data = data.get("currency")
    currency = currency_data.get("code", "USD") if isinstance(currency_data, dict) else "USD"

    if position:
        # Update existing
        position.symbol = symbol_str
        position.quantity = quantity
        position.average_cost = average_cost
        position.current_price = current_price
        position.currency = currency
        position._raw_json = data
        position.is_option = True
        position.option_type = option_type
        position.strike_price = strike_price
        position.expiration_date = expiration_date
        position.option_ticker = option_ticker
        position.underlying_symbol = underlying_symbol
    else:
        # Create new
        position = Position(
            snaptrade_id=snaptrade_id,
            account_id=account.id,
            symbol=symbol_str,
            quantity=quantity,
            average_cost=average_cost,
            current_price=current_price,
            currency=currency,
            _raw_json=data,
            is_option=True,
            option_type=option_type,
            strike_price=strike_price,
            expiration_date=expiration_date,
            option_ticker=option_ticker,
            underlying_symbol=underlying_symbol,
        )
        db.add(position)

    return 1


def sync_transactions(
    db: Session, client, user_id: str, user_secret: str
) -> int:
    """Sync all transactions using per-account endpoint."""
    accounts = db.query(Account).all()
    count = 0

    for account in accounts:
        transactions_data = fetch_account_activities(
            client, user_id, user_secret, account.snaptrade_id
        )

        for data in transactions_data:
            snaptrade_id = data.get("id")
            if not snaptrade_id:
                continue

            transaction = db.query(Transaction).filter(
                Transaction.snaptrade_id == snaptrade_id
            ).first()

            # Account ID is known from the loop context
            account_id = account.id

            symbol = data.get("symbol", {})
            symbol_str = symbol.get("symbol", "") if isinstance(symbol, dict) else str(symbol) if symbol else None

            trade_date = _parse_date(data.get("trade_date"))
            settlement_date = _parse_date(data.get("settlement_date"))

            # Extract option data
            option_data = _extract_option_data(data)

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
                # Update option fields
                transaction.is_option = option_data["is_option"]
                transaction.option_type = option_data["option_type"]
                transaction.strike_price = option_data["strike_price"]
                transaction.expiration_date = option_data["expiration_date"]
                transaction.option_ticker = option_data["option_ticker"]
                transaction.underlying_symbol = option_data["underlying_symbol"]
                transaction.option_action = option_data["option_action"]
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
                    # Option fields
                    is_option=option_data["is_option"],
                    option_type=option_data["option_type"],
                    strike_price=option_data["strike_price"],
                    expiration_date=option_data["expiration_date"],
                    option_ticker=option_data["option_ticker"],
                    underlying_symbol=option_data["underlying_symbol"],
                    option_action=option_data["option_action"],
                )
                db.add(transaction)
            count += 1

    db.commit()
    return count


def _extract_option_data(data: dict) -> dict:
    """Extract option-related fields from raw transaction data."""
    option_symbol = data.get("option_symbol")
    option_action = data.get("option_type")  # BUY_TO_OPEN, SELL_TO_CLOSE, etc.

    if not option_symbol:
        return {
            "is_option": False,
            "option_type": None,
            "strike_price": None,
            "expiration_date": None,
            "option_ticker": None,
            "underlying_symbol": None,
            "option_action": None,
        }

    # Extract fields from option_symbol object
    option_type = option_symbol.get("option_type")  # CALL or PUT
    strike_price = _to_decimal(option_symbol.get("strike_price"))
    expiration_date = _parse_date(option_symbol.get("expiration_date"))
    option_ticker = option_symbol.get("ticker")

    # Get underlying symbol
    underlying = option_symbol.get("underlying_symbol", {})
    underlying_symbol = underlying.get("symbol") if isinstance(underlying, dict) else None

    return {
        "is_option": True,
        "option_type": option_type,
        "strike_price": strike_price,
        "expiration_date": expiration_date,
        "option_ticker": option_ticker,
        "underlying_symbol": underlying_symbol,
        "option_action": option_action if option_action else None,
    }


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
