"""Sync orchestration service for SnapTrade data synchronization."""

import logging

from sqlalchemy.orm import Session

from app.models import Account, Position, TradeLot, Transaction
from app.services import lot_service
from app.services.snaptrade_client import (
    fetch_accounts,
    get_snaptrade_client,
    get_user_credentials,
)
from app.services.sync import sync_positions, sync_transactions

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

    # Run lot matching on new transactions
    match_result = lot_service.match_all(db)
    lots_created = match_result.get("created", 0)

    return {
        "accounts": account_count,
        "positions": position_count,
        "transactions": transaction_count,
        "lots_created": lots_created,
    }


def sync_accounts(db: Session, client, user_id: str, user_secret: str) -> int:
    """Sync accounts from SnapTrade."""
    accounts_data = fetch_accounts(client, user_id, user_secret)
    count = 0

    for data in accounts_data:
        snaptrade_id = data.get("id") or data.get("brokerage_account_id")
        if not snaptrade_id:
            continue

        account = _get_or_create_account(db, snaptrade_id)
        _update_account_fields(account, data)
        count += 1

    db.commit()
    return count


def get_sync_status(db: Session) -> dict[str, int]:
    """Get current sync status (record counts)."""
    return {
        "accounts": db.query(Account).count(),
        "positions": db.query(Position).count(),
        "transactions": db.query(Transaction).count(),
        "lots": db.query(TradeLot).count(),
    }


# --- Private helpers ---


def _get_or_create_account(db: Session, snaptrade_id: str) -> Account:
    """Get existing account or create new one."""
    account = db.query(Account).filter(Account.snaptrade_id == snaptrade_id).first()
    if not account:
        account = Account(snaptrade_id=snaptrade_id)
        db.add(account)
    return account


def _update_account_fields(account: Account, data: dict) -> None:
    """Update account fields from API data."""
    account.name = data.get("name", account.name or "Unknown")
    account.account_number = data.get("number", account.account_number or "")
    account.account_type = data.get("meta", {}).get("type")
    account.institution_name = data.get("institution_name", "Fidelity")
    account._raw_json = data
