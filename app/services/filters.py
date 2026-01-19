"""Filter dataclasses and query builders for service layer."""

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING
from urllib.parse import parse_qs

from sqlalchemy import desc, or_
from sqlalchemy.orm import Query, Session

from app.models import SavedFilter, TradeLot, Transaction
from app.models.tag import transaction_tags
from app.services.saved_filter_service import get_favorite_filter
from app.utils.query_params import parse_bool_param, parse_date_param, parse_int_param

if TYPE_CHECKING:
    from starlette.requests import Request


@dataclass
class TransactionFilter:
    """Filter criteria for transaction queries."""

    account_id: int | None = None
    # Multi-select fields with include/exclude mode
    symbols: list[str] | None = None
    symbol_mode: str = "include"  # "include" or "exclude"
    types: list[str] | None = None
    type_mode: str = "include"
    tag_ids: list[int] | None = None
    tag_mode: str = "include"
    # Single-value fields
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

    # Symbols (multi-select with mode)
    if filters.symbols:
        if filters.symbol_mode == "exclude":
            # For exclude, need to handle NULLs properly
            # NOT IN returns NULL when comparing to NULL, so exclude explicitly
            query = query.filter(
                Transaction.symbol.notin_(filters.symbols),
                or_(
                    Transaction.underlying_symbol.is_(None),
                    Transaction.underlying_symbol.notin_(filters.symbols),
                ),
            )
        else:
            # Include: match if symbol OR underlying_symbol is in list
            query = query.filter(
                or_(
                    Transaction.symbol.in_(filters.symbols),
                    Transaction.underlying_symbol.in_(filters.symbols),
                )
            )

    # Types (multi-select with mode)
    if filters.types:
        if filters.type_mode == "exclude":
            query = query.filter(Transaction.type.notin_(filters.types))
        else:
            query = query.filter(Transaction.type.in_(filters.types))

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

    # Tag IDs (multi-select with mode)
    if filters.tag_ids:
        if filters.tag_mode == "exclude":
            # Exclude transactions that have ANY of these tags
            subquery = (
                query.session.query(transaction_tags.c.transaction_id)
                .filter(transaction_tags.c.tag_id.in_(filters.tag_ids))
                .distinct()
            )
            query = query.filter(Transaction.id.notin_(subquery))
        else:
            # Include transactions that have ANY of these tags
            query = query.join(transaction_tags).filter(
                transaction_tags.c.tag_id.in_(filters.tag_ids)
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
    "symbol_mode",
    "type",
    "type_mode",
    "tag_id",
    "tag_mode",
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

    parsed = parse_qs(query_string)

    def get_single(key: str) -> str | None:
        values = parsed.get(key, [])
        return values[0] if values else None

    def get_list(key: str) -> list[str] | None:
        values = parsed.get(key, [])
        return values if values else None

    def get_int_list(key: str) -> list[int] | None:
        values = parsed.get(key, [])
        if not values:
            return None
        result = []
        for v in values:
            parsed_int = parse_int_param(v)
            if parsed_int is not None:
                result.append(parsed_int)
        return result if result else None

    return TransactionFilter(
        account_id=parse_int_param(get_single("account_id")),
        symbols=get_list("symbol"),
        symbol_mode=get_single("symbol_mode") or "include",
        types=get_list("type"),
        type_mode=get_single("type_mode") or "include",
        tag_ids=get_int_list("tag_id"),
        tag_mode=get_single("tag_mode") or "include",
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

    def get_list(key: str) -> list[str] | None:
        values = params.getlist(key)
        return values if values else None

    def get_int_list(key: str) -> list[int] | None:
        values = params.getlist(key)
        if not values:
            return None
        result = []
        for v in values:
            parsed_int = parse_int_param(v)
            if parsed_int is not None:
                result.append(parsed_int)
        return result if result else None

    return TransactionFilter(
        account_id=parse_int_param(get("account_id")),
        symbols=get_list("symbol"),
        symbol_mode=get("symbol_mode") or "include",
        types=get_list("type"),
        type_mode=get("type_mode") or "include",
        tag_ids=get_int_list("tag_id"),
        tag_mode=get("tag_mode") or "include",
        start_date=parse_date_param(get("start_date")),
        end_date=parse_date_param(get("end_date")),
        search=get("search"),
        is_option=parse_bool_param(get("is_option")),
        option_type=get("option_type"),
        option_action=get("option_action"),
        sort_by=get("sort_by") or "trade_date",
        sort_dir=get("sort_dir") or "desc",
    )


def get_effective_transaction_filter(
    request: "Request",
    db: Session,
) -> tuple[TransactionFilter, SavedFilter | None]:
    """
    Build TransactionFilter from request params, or from favorite if no params.

    Returns (filter, applied_favorite) tuple.
    applied_favorite is None if explicit params were used or no favorite exists.
    """
    if has_any_filter_params(request):
        return build_filter_from_request(request), None

    favorite = get_favorite_filter(db, "transactions")
    if favorite:
        return build_filter_from_query_string(favorite.filter_json), favorite

    return TransactionFilter(), None
