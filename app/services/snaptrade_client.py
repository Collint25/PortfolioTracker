from datetime import date
from typing import Any

from snaptrade_client import SnapTrade
from snaptrade_client.schemas import Unset

from app.config import get_settings


def get_snaptrade_client() -> SnapTrade:
    """Get configured SnapTrade client."""
    settings = get_settings()
    return SnapTrade(
        consumer_key=settings.snaptrade_consumer_key,
        client_id=settings.snaptrade_client_id,
    )


def get_user_credentials() -> tuple[str, str]:
    """Get user_id and user_secret from settings."""
    settings = get_settings()
    return settings.snaptrade_user_id, settings.snaptrade_user_secret


def fetch_accounts(client: SnapTrade, user_id: str, user_secret: str) -> list[Any]:
    """Fetch all accounts for user."""
    response = client.account_information.list_user_accounts(
        user_id=user_id,
        user_secret=user_secret,
    )
    if isinstance(response.body, Unset) or not response.body:
        return []
    return list(response.body)


def fetch_holdings(
    client: SnapTrade, user_id: str, user_secret: str, account_id: str
) -> list[Any]:
    """Fetch holdings/positions for a specific account."""
    response = client.account_information.get_user_holdings(
        account_id=account_id,
        user_id=user_id,
        user_secret=user_secret,
    )
    if isinstance(response.body, Unset) or not response.body:
        return []
    return response.body.get("positions") or []


def fetch_account_activities(
    client: SnapTrade,
    user_id: str,
    user_secret: str,
    account_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Any]:
    """
    Fetch all transactions for a specific account.

    Uses the per-account endpoint (non-deprecated).
    Handles pagination internally - SnapTrade returns max 1000 per request.
    Response format: {"data": [...], "pagination": {...}}
    """
    all_activities: list[Any] = []
    offset = 0
    limit = 1000

    while True:
        response = client.account_information.get_account_activities(
            account_id=account_id,
            user_id=user_id,
            user_secret=user_secret,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )

        # Response is {"data": [...], "pagination": {...}}
        if isinstance(response.body, Unset) or not response.body:
            break
        activities = response.body.get("data", [])
        if not activities:
            break

        all_activities.extend(activities)

        # If we got fewer than limit, we've reached the end
        if len(activities) < limit:
            break

        offset += limit

    return all_activities


def fetch_option_holdings(
    client: SnapTrade, user_id: str, user_secret: str, account_id: str
) -> list[Any]:
    """Fetch option holdings/positions for a specific account."""
    response = client.options.list_option_holdings(
        account_id=account_id,
        user_id=user_id,
        user_secret=user_secret,
    )
    if isinstance(response.body, Unset) or not response.body:
        return []
    return list(response.body)
