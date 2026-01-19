#!/usr/bin/env python
"""
SnapTrade API Discovery Script

Calls all available read-only SnapTrade endpoints and outputs:
- CSV files for each endpoint with all response fields
- Field manifest showing which fields are currently captured in the app

Usage: uv run python scripts/snaptrade_discovery.py
"""

import csv
import json
import logging
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from snaptrade_client import SnapTrade
from snaptrade_client.schemas import Unset

from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "snaptrade_discovery"


# ============================================================================
# Field Mapping Definitions (What we currently capture)
# ============================================================================

# Maps API field paths to model fields for the manifest
# Format: "endpoint:field_path" -> "Model.field"
CAPTURED_FIELDS: dict[str, str] = {
    # Account fields (from list_user_accounts)
    "accounts:id": "Account.snaptrade_id",
    "accounts:brokerage_account_id": "Account.snaptrade_id",
    "accounts:name": "Account.name",
    "accounts:number": "Account.account_number",
    "accounts:meta.type": "Account.account_type",
    "accounts:institution_name": "Account.institution_name",
    # Position fields (from get_user_holdings)
    "holdings:symbol.id": "Position.snaptrade_id (compound)",
    "holdings:symbol.symbol.symbol": "Position.symbol",
    "holdings:units": "Position.quantity",
    "holdings:average_purchase_price": "Position.average_cost",
    "holdings:price": "Position.current_price",
    "holdings:currency.code": "Position.currency",
    "holdings:symbol.option_symbol.option_type": "Position.option_type",
    "holdings:symbol.option_symbol.strike_price": "Position.strike_price",
    "holdings:symbol.option_symbol.expiration_date": "Position.expiration_date",
    "holdings:symbol.option_symbol.ticker": "Position.option_ticker",
    "holdings:symbol.option_symbol.underlying_symbol.symbol": "Position.underlying_symbol",
    # Option holdings fields (from list_option_holdings)
    "option_holdings:symbol.option_symbol.id": "Position.snaptrade_id (compound)",
    "option_holdings:units": "Position.quantity",
    "option_holdings:average_purchase_price": "Position.average_cost",
    "option_holdings:price": "Position.current_price",
    "option_holdings:currency.code": "Position.currency",
    "option_holdings:symbol.option_symbol.option_type": "Position.option_type",
    "option_holdings:symbol.option_symbol.strike_price": "Position.strike_price",
    "option_holdings:symbol.option_symbol.expiration_date": "Position.expiration_date",
    "option_holdings:symbol.option_symbol.ticker": "Position.option_ticker",
    "option_holdings:symbol.option_symbol.underlying_symbol.symbol": "Position.underlying_symbol",
    # Transaction fields (from get_account_activities)
    "activities:id": "Transaction.snaptrade_id",
    "activities:external_reference_id": "Transaction.external_reference_id",
    "activities:symbol.symbol": "Transaction.symbol",
    "activities:trade_date": "Transaction.trade_date",
    "activities:settlement_date": "Transaction.settlement_date",
    "activities:type": "Transaction.type",
    "activities:units": "Transaction.quantity",
    "activities:price": "Transaction.price",
    "activities:amount": "Transaction.amount",
    "activities:currency.code": "Transaction.currency",
    "activities:description": "Transaction.description",
    "activities:option_symbol.option_type": "Transaction.option_type",
    "activities:option_symbol.strike_price": "Transaction.strike_price",
    "activities:option_symbol.expiration_date": "Transaction.expiration_date",
    "activities:option_symbol.ticker": "Transaction.option_ticker",
    "activities:option_symbol.underlying_symbol.symbol": "Transaction.underlying_symbol",
    "activities:option_type": "Transaction.option_action",
}


# ============================================================================
# Utility Functions
# ============================================================================


def flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    """
    Flatten a nested dictionary into a flat dict with dot-separated keys.

    Example:
        {"a": {"b": {"c": 1}}} -> {"a.b.c": 1}
    """
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep).items())
        elif isinstance(v, list):
            # For lists, store the whole list as JSON string
            items.append((new_key, json.dumps(v) if v else "[]"))
        else:
            items.append((new_key, v))
    return dict(items)


def serialize_value(value: Any) -> str:
    """Convert a value to string for CSV output."""
    if value is None:
        return ""
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, dict | list):
        return json.dumps(value)
    return str(value)


def write_csv(filename: str, data: list[dict[str, Any]], endpoint_name: str) -> Path:
    """Write list of dicts to CSV file with auto-detected headers."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / filename

    if not data:
        logger.warning(f"No data for {endpoint_name}, writing empty CSV")
        filepath.write_text("")
        return filepath

    # Flatten all rows and collect all keys
    flat_rows = [flatten_dict(row) for row in data]
    all_keys: set[str] = set()
    for row in flat_rows:
        all_keys.update(row.keys())

    # Sort keys for consistent ordering
    headers = sorted(all_keys)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in flat_rows:
            # Serialize all values
            serialized = {k: serialize_value(row.get(k)) for k in headers}
            writer.writerow(serialized)

    logger.info(f"Wrote {len(data)} rows to {filepath.name}")
    return filepath


def get_sample_value(data: list[dict[str, Any]], field_path: str) -> str:
    """Get a sample value for a field from the data."""
    for row in data[:5]:  # Check first 5 rows
        flat = flatten_dict(row)
        if field_path in flat:
            value = flat[field_path]
            if value is not None and value != "":
                sample = str(value)
                # Truncate long values
                return sample[:50] + "..." if len(sample) > 50 else sample
    return ""


# ============================================================================
# Endpoint Definitions
# ============================================================================


@dataclass
class EndpointDef:
    """Definition of a SnapTrade endpoint to survey."""

    name: str
    filename: str
    fetch_func: Callable[[SnapTrade, str, str, dict[str, Any]], list[dict[str, Any]]]
    notes: str = ""
    requires_account: bool = False
    requires_symbol: bool = False


def fetch_accounts(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch all accounts."""
    response = client.account_information.list_user_accounts(
        user_id=user_id,
        user_secret=user_secret,
    )
    if isinstance(response.body, Unset) or not response.body:
        return []
    return [_to_dict(item) for item in response.body]


def fetch_account_details(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch detailed info for each account."""
    results = []
    for account_id in context.get("account_ids", []):
        try:
            response = client.account_information.get_user_account_details(
                account_id=account_id,
                user_id=user_id,
                user_secret=user_secret,
            )
            if not isinstance(response.body, Unset) and response.body:
                results.append(_to_dict(response.body))
        except Exception as e:
            logger.warning(f"Failed to get details for account {account_id}: {e}")
    return results


def fetch_account_balances(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch balance info for each account."""
    results = []
    for account_id in context.get("account_ids", []):
        try:
            response = client.account_information.get_user_account_balance(
                account_id=account_id,
                user_id=user_id,
                user_secret=user_secret,
            )
            if not isinstance(response.body, Unset) and response.body:
                # Add account_id to each balance record
                for item in response.body:
                    item_dict = _to_dict(item)
                    item_dict["_account_id"] = account_id
                    results.append(item_dict)
        except Exception as e:
            logger.warning(f"Failed to get balance for account {account_id}: {e}")
    return results


def fetch_holdings(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch holdings for each account."""
    results = []
    for account_id in context.get("account_ids", []):
        try:
            response = client.account_information.get_user_holdings(
                account_id=account_id,
                user_id=user_id,
                user_secret=user_secret,
            )
            if not isinstance(response.body, Unset) and response.body:
                positions = response.body.get("positions") or []
                for pos in positions:
                    pos_dict = _to_dict(pos)
                    pos_dict["_account_id"] = account_id
                    results.append(pos_dict)
        except Exception as e:
            logger.warning(f"Failed to get holdings for account {account_id}: {e}")
    return results


def fetch_all_holdings(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch all holdings across all accounts."""
    try:
        response = client.account_information.get_all_user_holdings(
            user_id=user_id,
            user_secret=user_secret,
        )
        if isinstance(response.body, Unset) or not response.body:
            return []
        # Response is list of account holdings
        results = []
        for account_data in response.body:
            account_dict = _to_dict(account_data)
            results.append(account_dict)
        return results
    except Exception as e:
        logger.warning(f"Failed to get all holdings: {e}")
        return []


def fetch_option_holdings(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch option holdings for each account."""
    results = []
    for account_id in context.get("account_ids", []):
        try:
            response = client.options.list_option_holdings(
                account_id=account_id,
                user_id=user_id,
                user_secret=user_secret,
            )
            if not isinstance(response.body, Unset) and response.body:
                for item in response.body:
                    item_dict = _to_dict(item)
                    item_dict["_account_id"] = account_id
                    results.append(item_dict)
        except Exception as e:
            logger.warning(
                f"Failed to get option holdings for account {account_id}: {e}"
            )
    return results


def fetch_activities(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch activities for each account with pagination."""
    results = []
    for account_id in context.get("account_ids", []):
        offset = 0
        limit = 100  # Use smaller limit for discovery to save time
        max_records = 500  # Cap total records per account

        while offset < max_records:
            try:
                response = client.account_information.get_account_activities(
                    account_id=account_id,
                    user_id=user_id,
                    user_secret=user_secret,
                    offset=offset,
                    limit=limit,
                )
                if isinstance(response.body, Unset) or not response.body:
                    break
                activities = response.body.get("data", [])
                if not activities:
                    break
                for item in activities:
                    item_dict = _to_dict(item)
                    item_dict["_account_id"] = account_id
                    results.append(item_dict)
                if len(activities) < limit:
                    break
                offset += limit
            except Exception as e:
                logger.warning(
                    f"Failed to get activities for account {account_id}: {e}"
                )
                break
    return results


def fetch_orders(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch orders for each account."""
    results = []
    for account_id in context.get("account_ids", []):
        try:
            response = client.account_information.get_user_account_orders(
                account_id=account_id,
                user_id=user_id,
                user_secret=user_secret,
                state="all",
            )
            if not isinstance(response.body, Unset) and response.body:
                for item in response.body:
                    item_dict = _to_dict(item)
                    item_dict["_account_id"] = account_id
                    results.append(item_dict)
        except Exception as e:
            logger.warning(f"Failed to get orders for account {account_id}: {e}")
    return results


def fetch_return_rates(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch return rates for each account."""
    results = []
    for account_id in context.get("account_ids", []):
        try:
            response = client.account_information.get_user_account_return_rates(
                account_id=account_id,
                user_id=user_id,
                user_secret=user_secret,
            )
            if not isinstance(response.body, Unset) and response.body:
                result = _to_dict(response.body)
                result["_account_id"] = account_id
                results.append(result)
        except Exception as e:
            logger.warning(f"Failed to get return rates for account {account_id}: {e}")
    return results


def fetch_currencies(
    client: SnapTrade, _user_id: str, _user_secret: str, _context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch all supported currencies."""
    try:
        response = client.reference_data.list_all_currencies()
        if isinstance(response.body, Unset) or not response.body:
            return []
        return [_to_dict(item) for item in response.body]
    except Exception as e:
        logger.warning(f"Failed to get currencies: {e}")
        return []


def fetch_currency_rates(
    client: SnapTrade, _user_id: str, _user_secret: str, _context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch currency exchange rates."""
    try:
        response = client.reference_data.list_all_currencies_rates()
        if isinstance(response.body, Unset) or not response.body:
            return []
        return [_to_dict(item) for item in response.body]
    except Exception as e:
        logger.warning(f"Failed to get currency rates: {e}")
        return []


def fetch_exchanges(
    client: SnapTrade, _user_id: str, _user_secret: str, _context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch all stock exchanges."""
    try:
        response = client.reference_data.get_stock_exchanges()
        if isinstance(response.body, Unset) or not response.body:
            return []
        return [_to_dict(item) for item in response.body]
    except Exception as e:
        logger.warning(f"Failed to get exchanges: {e}")
        return []


def fetch_security_types(
    client: SnapTrade, _user_id: str, _user_secret: str, _context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch all security types."""
    try:
        response = client.reference_data.get_security_types()
        if isinstance(response.body, Unset) or not response.body:
            return []
        return [_to_dict(item) for item in response.body]
    except Exception as e:
        logger.warning(f"Failed to get security types: {e}")
        return []


def fetch_brokerages(
    client: SnapTrade, _user_id: str, _user_secret: str, _context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch all supported brokerages."""
    try:
        response = client.reference_data.list_all_brokerages()
        if isinstance(response.body, Unset) or not response.body:
            return []
        return [_to_dict(item) for item in response.body]
    except Exception as e:
        logger.warning(f"Failed to get brokerages: {e}")
        return []


def fetch_brokerage_authorizations(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch brokerage authorizations."""
    try:
        response = client.connections.list_brokerage_authorizations(
            user_id=user_id,
            user_secret=user_secret,
        )
        if isinstance(response.body, Unset) or not response.body:
            return []
        return [_to_dict(item) for item in response.body]
    except Exception as e:
        logger.warning(f"Failed to get brokerage authorizations: {e}")
        return []


def fetch_symbol_search(
    client: SnapTrade, _user_id: str, _user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Search for symbols using sample symbols from holdings."""
    results = []
    symbols_to_search = context.get("sample_symbols", ["AAPL", "SPY", "MSFT"])[:5]

    for symbol in symbols_to_search:
        try:
            response = client.reference_data.get_symbols_by_ticker(
                query=symbol,
            )
            if not isinstance(response.body, Unset) and response.body:
                for item in response.body:
                    item_dict = _to_dict(item)
                    item_dict["_search_query"] = symbol
                    results.append(item_dict)
        except Exception as e:
            logger.warning(f"Failed to search symbol {symbol}: {e}")
    return results


def fetch_options_chain(
    client: SnapTrade, user_id: str, user_secret: str, context: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Fetch options chain for sample symbols.

    NOTE: As of Jan 2026, this endpoint returns 500 errors for Fidelity connections.
    The endpoint exists but appears unsupported for this brokerage. Use
    list_option_holdings() instead to get current option positions.
    """
    results = []
    account_ids = context.get("account_ids", [])
    symbols_to_search = context.get("sample_symbols", [])[:2]  # Limit to 2 symbols

    if not account_ids or not symbols_to_search:
        return []

    account_id = account_ids[0]
    for symbol in symbols_to_search:
        try:
            # First get the symbol ID
            symbol_response = client.reference_data.get_symbols_by_ticker(query=symbol)
            if isinstance(symbol_response.body, Unset) or not symbol_response.body:
                continue
            symbol_id = symbol_response.body[0].get("id")
            if not symbol_id:
                continue

            # Then get options chain
            response = client.options.get_options_chain(
                account_id=account_id,
                user_id=user_id,
                user_secret=user_secret,
                symbol=symbol_id,
            )
            if not isinstance(response.body, Unset) and response.body:
                for chain in response.body:
                    chain_dict = _to_dict(chain)
                    chain_dict["_symbol"] = symbol
                    results.append(chain_dict)
        except Exception as e:
            logger.warning(f"Failed to get options chain for {symbol}: {e}")
    return results


def fetch_api_status(
    client: SnapTrade, _user_id: str, _user_secret: str, _context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Check API status."""
    try:
        response = client.api_status.check()
        if isinstance(response.body, Unset) or not response.body:
            return []
        return [_to_dict(response.body)]
    except Exception as e:
        logger.warning(f"Failed to check API status: {e}")
        return []


def _to_dict(obj: Any) -> dict[str, Any]:
    """Convert SnapTrade response object to dict."""
    if isinstance(obj, dict):
        return dict(obj)
    if hasattr(obj, "to_dict"):
        result = obj.to_dict()
        return dict(result) if isinstance(result, dict) else {"value": result}
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {"value": obj}


# Endpoint registry
ENDPOINTS: list[EndpointDef] = [
    # High Priority - Account/Portfolio Data
    EndpointDef(
        name="accounts",
        filename="accounts.csv",
        fetch_func=fetch_accounts,
        notes="Currently used - list_user_accounts",
    ),
    EndpointDef(
        name="account_details",
        filename="account_details.csv",
        fetch_func=fetch_account_details,
        notes="May have additional fields",
        requires_account=True,
    ),
    EndpointDef(
        name="account_balances",
        filename="account_balances.csv",
        fetch_func=fetch_account_balances,
        notes="Cash, buying power, etc.",
        requires_account=True,
    ),
    EndpointDef(
        name="holdings",
        filename="holdings.csv",
        fetch_func=fetch_holdings,
        notes="Currently used - get_user_holdings",
        requires_account=True,
    ),
    EndpointDef(
        name="all_holdings",
        filename="all_holdings.csv",
        fetch_func=fetch_all_holdings,
        notes="Cross-account view",
    ),
    EndpointDef(
        name="option_holdings",
        filename="option_holdings.csv",
        fetch_func=fetch_option_holdings,
        notes="Currently used - list_option_holdings",
        requires_account=True,
    ),
    EndpointDef(
        name="activities",
        filename="activities.csv",
        fetch_func=fetch_activities,
        notes="Currently used - get_account_activities",
        requires_account=True,
    ),
    EndpointDef(
        name="orders",
        filename="orders.csv",
        fetch_func=fetch_orders,
        notes="Order history",
        requires_account=True,
    ),
    EndpointDef(
        name="return_rates",
        filename="return_rates.csv",
        fetch_func=fetch_return_rates,
        notes="UNAVAILABLE: Returns 403 for Fidelity (premium feature not enabled)",
        requires_account=True,
    ),
    # Medium Priority - Reference Data
    EndpointDef(
        name="currencies",
        filename="currencies.csv",
        fetch_func=fetch_currencies,
        notes="Supported currencies",
    ),
    EndpointDef(
        name="currency_rates",
        filename="currency_rates.csv",
        fetch_func=fetch_currency_rates,
        notes="FX exchange rates",
    ),
    EndpointDef(
        name="exchanges",
        filename="exchanges.csv",
        fetch_func=fetch_exchanges,
        notes="Stock exchanges",
    ),
    EndpointDef(
        name="security_types",
        filename="security_types.csv",
        fetch_func=fetch_security_types,
        notes="Security type definitions",
    ),
    EndpointDef(
        name="brokerages",
        filename="brokerages.csv",
        fetch_func=fetch_brokerages,
        notes="Supported brokerages",
    ),
    # Low Priority - Connection Management
    EndpointDef(
        name="brokerage_authorizations",
        filename="brokerage_authorizations.csv",
        fetch_func=fetch_brokerage_authorizations,
        notes="Broker connection info",
    ),
    EndpointDef(
        name="api_status",
        filename="api_status.csv",
        fetch_func=fetch_api_status,
        notes="Health check",
    ),
    # Symbol-specific endpoints
    EndpointDef(
        name="symbol_search",
        filename="symbol_search.csv",
        fetch_func=fetch_symbol_search,
        notes="Symbol metadata lookup",
        requires_symbol=True,
    ),
    EndpointDef(
        name="options_chain",
        filename="options_chain.csv",
        fetch_func=fetch_options_chain,
        notes="BROKEN: Returns 500 for Fidelity. Use list_option_holdings instead.",
        requires_account=True,
        requires_symbol=True,
    ),
]


# ============================================================================
# Manifest Generation
# ============================================================================


@dataclass
class ManifestEntry:
    """Entry in the field manifest."""

    endpoint: str
    field_path: str
    sample_value: str
    currently_captured: bool
    captured_in_model: str
    notes: str


def generate_manifest(
    endpoint_data: dict[str, list[dict[str, Any]]],
) -> list[ManifestEntry]:
    """Generate manifest of all fields across all endpoints."""
    entries: list[ManifestEntry] = []

    for endpoint_name, data in endpoint_data.items():
        if not data:
            continue

        # Collect all unique field paths
        all_fields: set[str] = set()
        for row in data:
            flat = flatten_dict(row)
            all_fields.update(flat.keys())

        # Create manifest entry for each field
        for field_path in sorted(all_fields):
            # Skip internal fields
            if field_path.startswith("_"):
                continue

            lookup_key = f"{endpoint_name}:{field_path}"
            captured_in = CAPTURED_FIELDS.get(lookup_key, "")
            is_captured = bool(captured_in)

            sample = get_sample_value(data, field_path)

            entries.append(
                ManifestEntry(
                    endpoint=endpoint_name,
                    field_path=field_path,
                    sample_value=sample,
                    currently_captured=is_captured,
                    captured_in_model=captured_in,
                    notes="",
                )
            )

    return entries


def write_manifest(entries: list[ManifestEntry]) -> Path:
    """Write field manifest to CSV."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / "field_manifest.csv"

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "endpoint",
                "field_path",
                "sample_value",
                "currently_captured",
                "captured_in_model",
                "notes",
            ]
        )
        for entry in entries:
            writer.writerow(
                [
                    entry.endpoint,
                    entry.field_path,
                    entry.sample_value,
                    entry.currently_captured,
                    entry.captured_in_model,
                    entry.notes,
                ]
            )

    logger.info(f"Wrote {len(entries)} fields to {filepath.name}")
    return filepath


# ============================================================================
# Main Execution
# ============================================================================


def run_discovery() -> None:
    """Run the full discovery process."""
    logger.info("Starting SnapTrade API Discovery")
    logger.info(f"Output directory: {OUTPUT_DIR}")

    # Initialize client
    settings = get_settings()
    client = SnapTrade(
        consumer_key=settings.snaptrade_consumer_key,
        client_id=settings.snaptrade_client_id,
    )
    user_id = settings.snaptrade_user_id
    user_secret = settings.snaptrade_user_secret

    logger.info("Initialized SnapTrade client")

    # Build context (account IDs, sample symbols)
    context: dict[str, Any] = {}

    # First, fetch accounts to get account IDs
    logger.info("Fetching accounts...")
    accounts_data = fetch_accounts(client, user_id, user_secret, context)
    context["account_ids"] = [
        acc.get("id") or acc.get("brokerage_account_id") for acc in accounts_data
    ]
    logger.info(f"Found {len(context['account_ids'])} accounts")

    # Fetch holdings to get sample symbols
    logger.info("Fetching holdings for sample symbols...")
    holdings_data = fetch_holdings(client, user_id, user_secret, context)
    sample_symbols: set[str] = set()
    for holding in holdings_data:
        flat = flatten_dict(holding)
        symbol = flat.get("symbol.symbol.symbol") or flat.get("symbol")
        if symbol and isinstance(symbol, str) and len(symbol) <= 5:
            sample_symbols.add(symbol)
    context["sample_symbols"] = list(sample_symbols)[:10]
    logger.info(f"Sample symbols: {context['sample_symbols']}")

    # Store data for each endpoint
    endpoint_data: dict[str, list[dict]] = {}

    # Store already-fetched data
    endpoint_data["accounts"] = accounts_data
    endpoint_data["holdings"] = holdings_data

    # Run each endpoint
    for endpoint in ENDPOINTS:
        # Skip already-fetched endpoints
        if endpoint.name in endpoint_data:
            logger.info(f"Skipping {endpoint.name} (already fetched)")
            write_csv(endpoint.filename, endpoint_data[endpoint.name], endpoint.name)
            continue

        logger.info(f"Fetching {endpoint.name}... ({endpoint.notes})")

        try:
            data = endpoint.fetch_func(client, user_id, user_secret, context)
            endpoint_data[endpoint.name] = data
            write_csv(endpoint.filename, data, endpoint.name)

            # Rate limiting: small delay between endpoints
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Failed to fetch {endpoint.name}: {e}")
            endpoint_data[endpoint.name] = []

    # Generate and write manifest
    logger.info("Generating field manifest...")
    manifest_entries = generate_manifest(endpoint_data)
    write_manifest(manifest_entries)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("DISCOVERY COMPLETE")
    logger.info("=" * 60)

    total_records = sum(len(data) for data in endpoint_data.values())
    captured_fields = sum(1 for e in manifest_entries if e.currently_captured)
    total_fields = len(manifest_entries)

    logger.info(f"Total endpoints surveyed: {len(endpoint_data)}")
    logger.info(f"Total records fetched: {total_records}")
    logger.info(f"Total unique fields: {total_fields}")
    logger.info(f"Currently captured fields: {captured_fields}")
    logger.info(f"Uncaptured fields: {total_fields - captured_fields}")
    logger.info(f"\nOutput written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    run_discovery()
