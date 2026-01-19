"""Tests for filter objects and query builders."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models import Account, Transaction
from app.services.filters import (
    PaginationParams,
    TransactionFilter,
    apply_pagination,
    apply_transaction_filters,
    apply_transaction_sorting,
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
    filters = TransactionFilter(symbol="AAPL")
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].symbol == "AAPL"


def test_filter_by_underlying_symbol(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Test filtering by underlying_symbol for options."""
    filters = TransactionFilter(symbol="TSLA")
    query = db_session.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].underlying_symbol == "TSLA"


def test_filter_by_transaction_type(
    db_session: Session, sample_transactions: list[Transaction]
):
    """Test filtering by transaction type."""
    filters = TransactionFilter(transaction_type="BUY")
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
        transaction_type="BUY",
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
