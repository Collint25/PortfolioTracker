"""Filter dataclasses and query builders for service layer."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import desc, or_
from sqlalchemy.orm import Query

from app.models import LinkedTrade, Transaction
from app.models.tag import transaction_tags


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
class LinkedTradeFilter:
    """Filter criteria for linked trade queries."""

    account_id: int | None = None
    underlying_symbol: str | None = None
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


def apply_linked_trade_filters(query: Query, filters: LinkedTradeFilter) -> Query:
    """Apply LinkedTradeFilter criteria to a query."""
    if filters.account_id is not None:
        query = query.filter(LinkedTrade.account_id == filters.account_id)

    if filters.underlying_symbol is not None:
        query = query.filter(LinkedTrade.symbol == filters.underlying_symbol)

    if filters.is_closed is not None:
        query = query.filter(LinkedTrade.is_closed == filters.is_closed)

    return query


def apply_pagination(query: Query, pagination: PaginationParams) -> Query:
    """Apply pagination to a query."""
    return query.offset(pagination.offset).limit(pagination.per_page)
