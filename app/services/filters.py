"""Filter dataclasses and query builders for service layer."""

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING
from urllib.parse import parse_qs

from sqlalchemy import desc, or_
from sqlalchemy.orm import Query

from app.models import TradeLot, Transaction
from app.models.tag import transaction_tags
from app.utils.query_params import parse_bool_param, parse_date_param, parse_int_param

if TYPE_CHECKING:
    from starlette.requests import Request


@dataclass
class TransactionFilter:
    """Filter criteria for transaction queries."""

    account_id: int | None = None
    symbol: str | None = None
    transaction_type: str | None = None
    tag_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    search: str | None = None
    is_option: bool | None = None
    option_type: str | None = None
    option_action: str | None = None
    sort_by: str = "trade_date"
    sort_dir: str = "desc"


@dataclass
class LotFilter:
    """Filter criteria for lot queries."""

    account_id: int | None = None
    symbol: str | None = None
    instrument_type: str | None = None  # STOCK, OPTION
    is_closed: bool | None = None


@dataclass
class PaginationParams:
    """Pagination parameters."""

    page: int = 1
    per_page: int = 50

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


def apply_transaction_filters(query: Query, filters: TransactionFilter) -> Query:
    """Apply TransactionFilter criteria to a query."""
    if filters.account_id is not None:
        query = query.filter(Transaction.account_id == filters.account_id)

    if filters.symbol:
        # Search in both symbol and underlying_symbol for options
        query = query.filter(
            or_(
                Transaction.symbol == filters.symbol,
                Transaction.underlying_symbol == filters.symbol,
            )
        )

    if filters.transaction_type:
        query = query.filter(Transaction.type == filters.transaction_type)

    if filters.start_date:
        query = query.filter(Transaction.trade_date >= filters.start_date)

    if filters.end_date:
        query = query.filter(Transaction.trade_date <= filters.end_date)

    if filters.search:
        search_pattern = f"%{filters.search}%"
        query = query.filter(
            or_(
                Transaction.symbol.ilike(search_pattern),
                Transaction.underlying_symbol.ilike(search_pattern),
                Transaction.description.ilike(search_pattern),
            )
        )

    if filters.tag_id is not None:
        query = query.join(transaction_tags).filter(
            transaction_tags.c.tag_id == filters.tag_id
        )

    if filters.is_option is not None:
        query = query.filter(Transaction.is_option == filters.is_option)

    if filters.option_type:
        query = query.filter(Transaction.option_type == filters.option_type)

    if filters.option_action:
        query = query.filter(Transaction.option_action == filters.option_action)

    return query


def apply_transaction_sorting(query: Query, filters: TransactionFilter) -> Query:
    """Apply sorting to a transaction query."""
    sort_column = getattr(Transaction, filters.sort_by, Transaction.trade_date)
    if filters.sort_dir == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    return query


def apply_lot_filters(query: Query, filters: LotFilter) -> Query:
    """Apply LotFilter criteria to a query."""
    if filters.account_id is not None:
        query = query.filter(TradeLot.account_id == filters.account_id)

    if filters.symbol is not None:
        query = query.filter(TradeLot.symbol == filters.symbol)

    if filters.instrument_type is not None:
        query = query.filter(TradeLot.instrument_type == filters.instrument_type)

    if filters.is_closed is not None:
        query = query.filter(TradeLot.is_closed == filters.is_closed)

    return query


def apply_pagination(query: Query, pagination: PaginationParams) -> Query:
    """Apply pagination to a query."""
    return query.offset(pagination.offset).limit(pagination.per_page)


# Filter param names (excludes sort_by, sort_dir, page which are not filters)
TRANSACTION_FILTER_PARAMS = [
    "account_id",
    "symbol",
    "type",
    "tag_id",
    "start_date",
    "end_date",
    "search",
    "is_option",
    "option_type",
    "option_action",
]


def has_any_filter_params(request: "Request") -> bool:
    """Check if request has any filter params (excludes sort/page)."""
    return any(request.query_params.get(p) for p in TRANSACTION_FILTER_PARAMS)


def build_filter_from_query_string(query_string: str) -> TransactionFilter:
    """Parse a URL query string into a TransactionFilter."""
    if not query_string:
        return TransactionFilter()

    # parse_qs returns lists, extract single values
    parsed = parse_qs(query_string)

    def get_single(key: str) -> str | None:
        values = parsed.get(key, [])
        return values[0] if values else None

    return TransactionFilter(
        account_id=parse_int_param(get_single("account_id")),
        symbol=get_single("symbol") or None,
        transaction_type=get_single("type") or None,
        tag_id=parse_int_param(get_single("tag_id")),
        start_date=parse_date_param(get_single("start_date")),
        end_date=parse_date_param(get_single("end_date")),
        search=get_single("search") or None,
        is_option=parse_bool_param(get_single("is_option")),
        option_type=get_single("option_type") or None,
        option_action=get_single("option_action") or None,
        sort_by=get_single("sort_by") or "trade_date",
        sort_dir=get_single("sort_dir") or "desc",
    )


def build_filter_from_request(request: "Request") -> TransactionFilter:
    """Build a TransactionFilter from request query params."""
    params = request.query_params

    def get(key: str) -> str | None:
        return params.get(key) or None

    return TransactionFilter(
        account_id=parse_int_param(get("account_id")),
        symbol=get("symbol"),
        transaction_type=get("type"),
        tag_id=parse_int_param(get("tag_id")),
        start_date=parse_date_param(get("start_date")),
        end_date=parse_date_param(get("end_date")),
        search=get("search"),
        is_option=parse_bool_param(get("is_option")),
        option_type=get("option_type"),
        option_action=get("option_action"),
        sort_by=get("sort_by") or "trade_date",
        sort_dir=get("sort_dir") or "desc",
    )
