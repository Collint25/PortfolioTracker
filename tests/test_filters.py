"""Tests for filter objects and query builders."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models import Account, SavedFilter, Transaction
from app.services.filters import (
    PaginationParams,
    TransactionFilter,
    apply_pagination,
    apply_transaction_filters,
    apply_transaction_sorting,
    build_filter_from_query_string,
    get_effective_transaction_filter,
    has_any_filter_params,
)


@pytest.fixture
def sample_transactions(db_session: Session) -> list[Transaction]:
    """Create sample transactions for testing."""
    account = Account(
        snaptrade_id="test_account",
        name="Test Account",
        account_number="12345",
        institution_name="Test Bank",
    )
    db_session.add(account)
    db_session.flush()

    transactions = [
        Transaction(
            snaptrade_id="txn1",
            account_id=account.id,
            symbol="AAPL",
            trade_date=date(2024, 1, 1),
            type="BUY",
            quantity=Decimal("10"),
            price=Decimal("150"),
            amount=Decimal("-1500"),
            is_option=False,
        ),
        Transaction(
            snaptrade_id="txn2",
            account_id=account.id,
            symbol="MSFT",
            trade_date=date(2024, 1, 2),
            type="SELL",
            quantity=Decimal("5"),
            price=Decimal("200"),
            amount=Decimal("1000"),
            is_option=False,
        ),
        Transaction(
            snaptrade_id="txn3",
            account_id=account.id,
            symbol="TSLA",
            underlying_symbol="TSLA",
            trade_date=date(2024, 1, 3),
            type="BUY",
            quantity=Decimal("1"),
            price=Decimal("5.00"),
            amount=Decimal("-500"),
            is_option=True,
            option_type="CALL",
            option_action="BUY_TO_OPEN",
            strike_price=Decimal("250"),
            expiration_date=date(2024, 2, 1),
        ),
    ]
    for txn in transactions:
        db_session.add(txn)
    db_session.commit()

    return transactions


def test_filter_by_account_id(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Test filtering by account_id."""
    filters = TransactionFilter(account_id=sample_transactions[0].account_id)
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 3
    assert all(t.account_id == sample_transactions[0].account_id for t in results)


def test_filter_by_symbol(db_session: Session, sample_transactions: list[Transaction]):
    """Test filtering by symbol."""
    filters = TransactionFilter(symbols=["AAPL"])
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].symbol == "AAPL"


def test_filter_by_underlying_symbol(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Test filtering by underlying_symbol for options."""
    filters = TransactionFilter(symbols=["TSLA"])
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].underlying_symbol == "TSLA"


def test_filter_by_transaction_type(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Test filtering by transaction type."""
    filters = TransactionFilter(types=["BUY"])
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 2
    assert all(t.type == "BUY" for t in results)


def test_filter_by_date_range(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Test filtering by date range."""
    filters = TransactionFilter(
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 2),
    )
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].trade_date == date(2024, 1, 2)


def test_filter_by_is_option(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Test filtering by is_option flag."""
    filters = TransactionFilter(is_option=True)
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].is_option is True


def test_filter_by_option_type(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Test filtering by option_type."""
    filters = TransactionFilter(option_type="CALL")
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].option_type == "CALL"


def test_sorting_asc(db_session: Session, sample_transactions: list[Transaction]):
    """Test sorting ascending."""
    filters = TransactionFilter(sort_by="trade_date", sort_dir="asc")
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)
    query = apply_transaction_sorting(query, filters)

    results = query.all()
    assert results[0].trade_date == date(2024, 1, 1)
    assert results[-1].trade_date == date(2024, 1, 3)


def test_sorting_desc(db_session: Session, sample_transactions: list[Transaction]):
    """Test sorting descending."""
    filters = TransactionFilter(sort_by="trade_date", sort_dir="desc")
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)
    query = apply_transaction_sorting(query, filters)

    results = query.all()
    assert results[0].trade_date == date(2024, 1, 3)
    assert results[-1].trade_date == date(2024, 1, 1)


def test_pagination(db_session: Session, sample_transactions: list[Transaction]):
    """Test pagination."""
    pagination = PaginationParams(page=1, per_page=2)
    query = db_session.query(Transaction)
    query = apply_pagination(query, pagination)

    results = query.all()
    assert len(results) == 2


def test_pagination_offset(db_session: Session, sample_transactions: list[Transaction]):
    """Test pagination offset."""
    pagination = PaginationParams(page=2, per_page=2)
    query = db_session.query(Transaction)
    query = apply_pagination(query, pagination)

    results = query.all()
    assert len(results) == 1


def test_combined_filters(db_session: Session, sample_transactions: list[Transaction]):
    """Test combining multiple filters."""
    filters = TransactionFilter(
        types=["BUY"],
        is_option=False,
    )
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].symbol == "AAPL"


# Tests for has_any_filter_params


def test_has_any_filter_params_empty():
    """Test with no params returns False."""
    request = MagicMock()
    request.query_params = {}
    assert has_any_filter_params(request) is False


def test_has_any_filter_params_with_filter():
    """Test with filter param returns True."""
    request = MagicMock()
    request.query_params = {"symbol": "AAPL"}
    assert has_any_filter_params(request) is True


def test_has_any_filter_params_sort_only():
    """Test with only sort params returns False (sort is not a filter)."""
    request = MagicMock()
    request.query_params = {"sort_by": "symbol", "sort_dir": "asc"}
    assert has_any_filter_params(request) is False


def test_has_any_filter_params_page_only():
    """Test with only page param returns False."""
    request = MagicMock()
    request.query_params = {"page": "2"}
    assert has_any_filter_params(request) is False


# Tests for build_filter_from_query_string


def test_build_filter_from_empty_query_string():
    """Test empty query string returns default filter."""
    result = build_filter_from_query_string("")
    assert result.account_id is None
    assert result.symbols is None
    assert result.sort_by == "trade_date"
    assert result.sort_dir == "desc"


def test_build_filter_from_query_string_basic():
    """Test parsing basic filter params."""
    result = build_filter_from_query_string("symbol=AAPL&account_id=1")
    assert result.symbols == ["AAPL"]
    assert result.account_id == 1


def test_build_filter_from_query_string_with_dates():
    """Test parsing date params."""
    result = build_filter_from_query_string("start_date=2024-01-01&end_date=2024-12-31")
    assert result.start_date == date(2024, 1, 1)
    assert result.end_date == date(2024, 12, 31)


def test_build_filter_from_query_string_with_bool():
    """Test parsing boolean params."""
    result = build_filter_from_query_string("is_option=true")
    assert result.is_option is True


def test_build_filter_from_query_string_with_sort():
    """Test parsing sort params."""
    result = build_filter_from_query_string("sort_by=symbol&sort_dir=asc")
    assert result.sort_by == "symbol"
    assert result.sort_dir == "asc"


# Tests for build_filter_from_request


def test_build_filter_from_request_empty():
    """Test empty request returns default filter."""
    from app.services.filters import build_filter_from_request

    request = MagicMock()
    request.query_params = MagicMock()
    request.query_params.get = lambda k: None
    request.query_params.getlist = lambda k: []
    result = build_filter_from_request(request)
    assert result.account_id is None
    assert result.sort_by == "trade_date"


def test_build_filter_from_request_with_params():
    """Test request with params builds correct filter."""
    from app.services.filters import build_filter_from_request

    request = MagicMock()
    request.query_params = MagicMock()
    request.query_params.get = lambda k: {"account_id": "2", "is_option": "false"}.get(
        k
    )
    request.query_params.getlist = lambda k: ["MSFT"] if k == "symbol" else []
    result = build_filter_from_request(request)
    assert result.symbols == ["MSFT"]
    assert result.account_id == 2
    assert result.is_option is False


# Tests for get_effective_transaction_filter


def test_get_effective_filter_with_explicit_params(db_session: Session):
    """When request has filter params, use them (ignore favorite)."""
    # Create a favorite filter
    favorite = SavedFilter(
        name="Favorite",
        page="transactions",
        filter_json="symbol=IGNORED",
        is_favorite=True,
    )
    db_session.add(favorite)
    db_session.commit()

    request = MagicMock()
    request.query_params = MagicMock()
    request.query_params.get = lambda k: {"symbol": "AAPL"}.get(k)
    request.query_params.getlist = lambda k: ["AAPL"] if k == "symbol" else []

    filter_obj, applied_favorite = get_effective_transaction_filter(request, db_session)

    assert filter_obj.symbols == ["AAPL"]
    assert applied_favorite is None


def test_get_effective_filter_applies_favorite(db_session: Session):
    """When no filter params and favorite exists, apply it."""
    favorite = SavedFilter(
        name="My Favorite",
        page="transactions",
        filter_json="symbol=TSLA&account_id=5",
        is_favorite=True,
    )
    db_session.add(favorite)
    db_session.commit()

    request = MagicMock()
    request.query_params = {}

    filter_obj, applied_favorite = get_effective_transaction_filter(request, db_session)

    assert filter_obj.symbols == ["TSLA"]
    assert filter_obj.account_id == 5
    assert applied_favorite is not None
    assert applied_favorite.name == "My Favorite"


def test_get_effective_filter_no_favorite(db_session: Session):
    """When no filter params and no favorite, return defaults."""
    request = MagicMock()
    request.query_params = {}

    filter_obj, applied_favorite = get_effective_transaction_filter(request, db_session)

    assert filter_obj.symbols is None
    assert filter_obj.account_id is None
    assert applied_favorite is None


def test_get_effective_filter_sort_only_applies_favorite(db_session: Session):
    """Sort params alone should still allow favorite to apply."""
    favorite = SavedFilter(
        name="Favorite",
        page="transactions",
        filter_json="symbol=GOOG",
        is_favorite=True,
    )
    db_session.add(favorite)
    db_session.commit()

    request = MagicMock()
    request.query_params = {"sort_by": "symbol", "sort_dir": "asc"}

    filter_obj, applied_favorite = get_effective_transaction_filter(request, db_session)

    assert filter_obj.symbols == ["GOOG"]
    assert applied_favorite is not None


# Tests for multi-value fields in TransactionFilter


def test_transaction_filter_defaults():
    """TransactionFilter has correct default values for multi-value fields."""
    f = TransactionFilter()
    assert f.symbols is None
    assert f.symbol_mode == "include"
    assert f.types is None
    assert f.type_mode == "include"
    assert f.tag_ids is None
    assert f.tag_mode == "include"


def test_transaction_filter_with_multi_values():
    """TransactionFilter accepts list values."""
    f = TransactionFilter(
        symbols=["AAPL", "MSFT"],
        symbol_mode="exclude",
        types=["BUY", "SELL"],
        tag_ids=[1, 2, 3],
    )
    assert f.symbols == ["AAPL", "MSFT"]
    assert f.symbol_mode == "exclude"
    assert f.types == ["BUY", "SELL"]
    assert f.tag_ids == [1, 2, 3]


# Tests for multi-value IN/NOT IN filtering


def test_apply_filters_symbols_include(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Include mode uses IN clause for multiple symbols."""
    filters = TransactionFilter(symbols=["AAPL", "MSFT"], symbol_mode="include")
    query = db_session.query(Transaction)
    result = apply_transaction_filters(query, filters)
    results = result.all()
    # Should match AAPL and MSFT
    assert len(results) == 2
    symbols = {r.symbol for r in results}
    assert symbols == {"AAPL", "MSFT"}


def test_apply_filters_symbols_exclude(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Exclude mode uses NOT IN clause."""
    filters = TransactionFilter(symbols=["AAPL"], symbol_mode="exclude")
    query = db_session.query(Transaction)
    result = apply_transaction_filters(query, filters)
    results = result.all()
    # Should exclude AAPL, leaving MSFT and TSLA (option)
    assert len(results) == 2
    assert all(r.symbol != "AAPL" for r in results)


def test_apply_filters_types_include(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Types include mode uses IN clause."""
    filters = TransactionFilter(types=["BUY", "SELL"], type_mode="include")
    query = db_session.query(Transaction)
    result = apply_transaction_filters(query, filters)
    results = result.all()
    assert len(results) == 3
    assert all(r.type in ["BUY", "SELL"] for r in results)


def test_apply_filters_types_exclude(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Types exclude mode uses NOT IN clause."""
    filters = TransactionFilter(types=["SELL"], type_mode="exclude")
    query = db_session.query(Transaction)
    result = apply_transaction_filters(query, filters)
    results = result.all()
    # Should exclude SELL, leaving only BUY transactions
    assert len(results) == 2
    assert all(r.type == "BUY" for r in results)


# Tests for multi-value query string parsing


def test_build_filter_from_query_string_multi_symbols():
    """Parses multiple symbol values from query string."""
    qs = "symbol=AAPL&symbol=MSFT&symbol_mode=exclude"
    f = build_filter_from_query_string(qs)
    assert f.symbols == ["AAPL", "MSFT"]
    assert f.symbol_mode == "exclude"


def test_build_filter_from_query_string_multi_types():
    """Parses multiple type values from query string."""
    qs = "type=BUY&type=SELL&type_mode=include"
    f = build_filter_from_query_string(qs)
    assert f.types == ["BUY", "SELL"]
    assert f.type_mode == "include"


def test_build_filter_from_query_string_single_symbol_compat():
    """Single symbol value still works (backward compat)."""
    qs = "symbol=AAPL"
    f = build_filter_from_query_string(qs)
    assert f.symbols == ["AAPL"]
    assert f.symbol_mode == "include"


def test_build_filter_from_query_string_multi_tag_ids():
    """Parses multiple tag_id values."""
    qs = "tag_id=1&tag_id=2&tag_mode=exclude"
    f = build_filter_from_query_string(qs)
    assert f.tag_ids == [1, 2]
    assert f.tag_mode == "exclude"
