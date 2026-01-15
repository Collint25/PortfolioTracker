from snaptrade_client import SnapTrade

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


def fetch_accounts(client: SnapTrade, user_id: str, user_secret: str) -> list[dict]:
    """Fetch all accounts for user."""
    response = client.account_information.list_user_accounts(
        user_id=user_id,
        user_secret=user_secret,
    )
    return response.body if response.body else []


def fetch_holdings(
    client: SnapTrade, user_id: str, user_secret: str, account_id: str
) -> list[dict]:
    """Fetch holdings/positions for a specific account."""
    response = client.account_information.get_user_holdings(
        account_id=account_id,
        user_id=user_id,
        user_secret=user_secret,
    )
    return response.body.get("positions", []) if response.body else []


def fetch_account_activities(
    client: SnapTrade,
    user_id: str,
    user_secret: str,
    account_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """
    Fetch all transactions for a specific account.

    Uses the per-account endpoint (non-deprecated).
    Handles pagination internally - SnapTrade returns max 1000 per request.
    Response format: {"data": [...], "pagination": {...}}
    """
    all_activities: list[dict] = []
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
        body = response.body if response.body else {}
        activities = body.get("data", [])
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
) -> list[dict]:
    """Fetch option holdings/positions for a specific account."""
    response = client.options.list_option_holdings(
        account_id=account_id,
        user_id=user_id,
        user_secret=user_secret,
    )
    return response.body if response.body else []
