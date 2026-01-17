"""Tests for option support functionality."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.position import Position
from app.services.sync.snaptrade_parser import extract_option_data


@pytest.fixture
def db_session():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_account(db_session):
    """Create a sample account."""
    account = Account(
        snaptrade_id="test-account-123",
        name="Test Account",
        account_number="12345",
        institution_name="Test Broker",
    )
    db_session.add(account)
    db_session.commit()
    return account


class TestOptionExtraction:
    """Test option data extraction from raw JSON."""

    def testextract_option_data_with_option(self):
        """Test extracting option data from a valid option transaction."""
        raw_data = {
            "option_symbol": {
                "id": "abc123",
                "ticker": "AAPL  250117C00250000",
                "strike_price": 250.0,
                "expiration_date": "2025-01-17",
                "is_mini_option": False,
                "option_type": "CALL",
                "underlying_symbol": {
                    "id": "xyz789",
                    "symbol": "AAPL",
                    "description": "Apple Inc",
                },
            },
            "option_type": "BUY_TO_OPEN",
        }

        result = extract_option_data(raw_data)

        assert result["is_option"] is True
        assert result["option_type"] == "CALL"
        assert result["strike_price"] == Decimal("250.0")
        assert result["expiration_date"] == date(2025, 1, 17)
        assert result["option_ticker"] == "AAPL  250117C00250000"
        assert result["underlying_symbol"] == "AAPL"
        assert result["option_action"] == "BUY_TO_OPEN"

    def testextract_option_data_without_option(self):
        """Test extracting from a non-option transaction."""
        raw_data = {
            "symbol": {"symbol": "AAPL"},
            "option_symbol": None,
            "option_type": "",
        }

        result = extract_option_data(raw_data)

        assert result["is_option"] is False
        assert result["option_type"] is None
        assert result["strike_price"] is None
        assert result["expiration_date"] is None
        assert result["option_ticker"] is None
        assert result["underlying_symbol"] is None
        assert result["option_action"] is None

    def testextract_option_data_put_option(self):
        """Test extracting PUT option data."""
        raw_data = {
            "option_symbol": {
                "id": "def456",
                "ticker": "SPY   250215P00500000",
                "strike_price": 500.0,
                "expiration_date": "2025-02-15",
                "is_mini_option": False,
                "option_type": "PUT",
                "underlying_symbol": {
                    "symbol": "SPY",
                },
            },
            "option_type": "SELL_TO_CLOSE",
        }

        result = extract_option_data(raw_data)

        assert result["is_option"] is True
        assert result["option_type"] == "PUT"
        assert result["option_action"] == "SELL_TO_CLOSE"


class TestOptionTransactionModel:
    """Test Transaction model with option fields."""

    def test_create_option_transaction(self, db_session, sample_account):
        """Test creating a transaction with option fields."""
        txn = Transaction(
            snaptrade_id="txn-opt-1",
            account_id=sample_account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 14),
            type="BUY",
            amount=Decimal("-500.00"),
            is_option=True,
            option_type="CALL",
            strike_price=Decimal("250.00"),
            expiration_date=date(2025, 1, 17),
            option_ticker="AAPL  250117C00250000",
            underlying_symbol="AAPL",
            option_action="BUY_TO_OPEN",
        )
        db_session.add(txn)
        db_session.commit()

        # Query it back
        saved = db_session.query(Transaction).filter_by(snaptrade_id="txn-opt-1").first()
        assert saved.is_option is True
        assert saved.option_type == "CALL"
        assert saved.strike_price == Decimal("250.00")
        assert saved.expiration_date == date(2025, 1, 17)
        assert saved.option_action == "BUY_TO_OPEN"

    def test_create_stock_transaction(self, db_session, sample_account):
        """Test creating a stock transaction (is_option=False)."""
        txn = Transaction(
            snaptrade_id="txn-stock-1",
            account_id=sample_account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 14),
            type="BUY",
            amount=Decimal("-1000.00"),
            is_option=False,
        )
        db_session.add(txn)
        db_session.commit()

        saved = db_session.query(Transaction).filter_by(snaptrade_id="txn-stock-1").first()
        assert saved.is_option is False
        assert saved.option_type is None


class TestOptionPositionModel:
    """Test Position model with option fields."""

    def test_create_option_position(self, db_session, sample_account):
        """Test creating a position with option fields."""
        pos = Position(
            snaptrade_id="pos-opt-1",
            account_id=sample_account.id,
            symbol="AAPL",
            quantity=Decimal("5"),
            average_cost=Decimal("2.50"),
            current_price=Decimal("3.00"),
            is_option=True,
            option_type="CALL",
            strike_price=Decimal("250.00"),
            expiration_date=date(2025, 1, 17),
            option_ticker="AAPL  250117C00250000",
            underlying_symbol="AAPL",
        )
        db_session.add(pos)
        db_session.commit()

        saved = db_session.query(Position).filter_by(snaptrade_id="pos-opt-1").first()
        assert saved.is_option is True
        assert saved.option_type == "CALL"
        assert saved.underlying_symbol == "AAPL"


class TestTransactionServiceFilters:
    """Test option filters in transaction service."""

    def test_filter_by_is_option(self, db_session, sample_account):
        """Test filtering transactions by is_option."""
        # Create a stock and an option transaction
        stock_txn = Transaction(
            snaptrade_id="txn-stock-filter",
            account_id=sample_account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 14),
            type="BUY",
            amount=Decimal("-1000.00"),
            is_option=False,
        )
        option_txn = Transaction(
            snaptrade_id="txn-opt-filter",
            account_id=sample_account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 14),
            type="BUY",
            amount=Decimal("-500.00"),
            is_option=True,
            option_type="CALL",
        )
        db_session.add_all([stock_txn, option_txn])
        db_session.commit()

        # Filter for options only
        from app.services.transaction_service import get_transactions
        options, count = get_transactions(db_session, is_option=True)
        assert count == 1
        assert options[0].is_option is True

        # Filter for stocks only
        stocks, count = get_transactions(db_session, is_option=False)
        assert count == 1
        assert stocks[0].is_option is False
