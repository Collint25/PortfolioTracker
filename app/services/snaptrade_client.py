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


def fetch_transactions(
    client: SnapTrade,
    user_id: str,
    user_secret: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """
    Fetch all transactions for user.

    Handles pagination internally - SnapTrade returns max 1000 per request.
    """
    params = {
        "user_id": user_id,
        "user_secret": user_secret,
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    response = client.transactions_and_reporting.get_activities(
        user_id=user_id,
        user_secret=user_secret,
        start_date=start_date,
        end_date=end_date,
    )
    return response.body if response.body else []
