"""Tests for linked trade service (FIFO matching)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Account, Base, Transaction
from app.services import linked_trade_service
from app.services.linked_trade_service import ContractKey


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def account(db_session):
    """Create test account."""
    account = Account(
        snaptrade_id="test-account-1",
        name="Test Account",
        account_number="12345",
        institution_name="Test Broker",
    )
    db_session.add(account)
    db_session.commit()
    return account


def create_option_transaction(
    db_session,
    account,
    underlying: str,
    option_type: str,
    strike: Decimal,
    expiration: date,
    action: str,
    quantity: Decimal,
    price: Decimal,
    amount: Decimal,
    trade_date: date,
    txn_id: int,
) -> Transaction:
    """Helper to create option transaction."""
    txn = Transaction(
        snaptrade_id=f"txn-{txn_id}",
        account_id=account.id,
        symbol=underlying,
        trade_date=trade_date,
        type="BUY" if "BUY" in action else "SELL",
        quantity=quantity,
        price=price,
        amount=amount,
        is_option=True,
        option_type=option_type,
        strike_price=strike,
        expiration_date=expiration,
        underlying_symbol=underlying,
        option_action=action,
    )
    db_session.add(txn)
    db_session.commit()
    return txn


class TestFIFOSimpleMatch:
    """Test simple open/close matching."""

    def test_open_5_close_5(self, db_session, account):
        """Open 5 contracts, close 5 - should create 1 linked trade."""
        # Create transactions
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="BUY_TO_OPEN",
            quantity=Decimal("5"),
            price=Decimal("2.00"),
            amount=Decimal("-1000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="SELL_TO_CLOSE",
            quantity=Decimal("-5"),
            price=Decimal("3.00"),
            amount=Decimal("1500"),
            trade_date=date(2025, 2, 15),
            txn_id=2,
        )

        # Run matching
        contract = ContractKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = linked_trade_service.auto_match_contract(db_session, contract)
        db_session.commit()

        # Verify
        assert len(linked_trades) == 1
        lt = linked_trades[0]
        assert lt.direction == "LONG"
        assert lt.is_closed
        assert lt.total_opened_quantity == Decimal("5")
        assert lt.total_closed_quantity == Decimal("5")
        assert len(lt.legs) == 2


class TestFIFOPartialClose:
    """Test partial close scenarios."""

    def test_open_5_close_3_close_2(self, db_session, account):
        """Open 5, close 3, close 2 later - should create 1 linked trade with 3 legs."""
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="BUY_TO_OPEN",
            quantity=Decimal("5"),
            price=Decimal("2.00"),
            amount=Decimal("-1000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="SELL_TO_CLOSE",
            quantity=Decimal("-3"),
            price=Decimal("3.00"),
            amount=Decimal("900"),
            trade_date=date(2025, 2, 10),
            txn_id=2,
        )
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="SELL_TO_CLOSE",
            quantity=Decimal("-2"),
            price=Decimal("2.50"),
            amount=Decimal("500"),
            trade_date=date(2025, 2, 15),
            txn_id=3,
        )

        contract = ContractKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = linked_trade_service.auto_match_contract(db_session, contract)
        db_session.commit()

        assert len(linked_trades) == 1
        lt = linked_trades[0]
        assert lt.is_closed
        assert lt.total_opened_quantity == Decimal("5")
        assert lt.total_closed_quantity == Decimal("5")
        assert len(lt.legs) == 3  # 1 open + 2 closes


class TestFIFOMultipleOpens:
    """Test FIFO order with multiple opens."""

    def test_open_3_open_2_close_5(self, db_session, account):
        """Open 3 day 1, open 2 day 2, close 5 - FIFO should use day 1 first."""
        # Day 1: Open 3 @ $2.00
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="BUY_TO_OPEN",
            quantity=Decimal("3"),
            price=Decimal("2.00"),
            amount=Decimal("-600"),
            trade_date=date(2025, 1, 10),
            txn_id=1,
        )
        # Day 2: Open 2 @ $2.50
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="BUY_TO_OPEN",
            quantity=Decimal("2"),
            price=Decimal("2.50"),
            amount=Decimal("-500"),
            trade_date=date(2025, 1, 15),
            txn_id=2,
        )
        # Day 3: Close 5 @ $3.00
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="SELL_TO_CLOSE",
            quantity=Decimal("-5"),
            price=Decimal("3.00"),
            amount=Decimal("1500"),
            trade_date=date(2025, 2, 15),
            txn_id=3,
        )

        contract = ContractKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = linked_trade_service.auto_match_contract(db_session, contract)
        db_session.commit()

        assert len(linked_trades) == 1
        lt = linked_trades[0]
        assert lt.is_closed
        # Should have 3 legs: 2 opens + 1 close
        assert len(lt.legs) == 3


class TestShortPosition:
    """Test short selling (SELL_TO_OPEN -> BUY_TO_CLOSE)."""

    def test_short_position(self, db_session, account):
        """Sell to open, buy to close - should create SHORT direction."""
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="PUT",
            strike=Decimal("140"),
            expiration=date(2025, 3, 21),
            action="SELL_TO_OPEN",
            quantity=Decimal("-5"),
            price=Decimal("3.00"),
            amount=Decimal("1500"),  # Receive premium
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="PUT",
            strike=Decimal("140"),
            expiration=date(2025, 3, 21),
            action="BUY_TO_CLOSE",
            quantity=Decimal("5"),
            price=Decimal("2.00"),
            amount=Decimal("-1000"),  # Pay to close
            trade_date=date(2025, 2, 15),
            txn_id=2,
        )

        contract = ContractKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="PUT",
            strike_price=Decimal("140"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = linked_trade_service.auto_match_contract(db_session, contract)
        db_session.commit()

        assert len(linked_trades) == 1
        lt = linked_trades[0]
        assert lt.direction == "SHORT"
        assert lt.is_closed


class TestCrossAccountNoMatch:
    """Test that different accounts don't match."""

    def test_cross_account_no_match(self, db_session, account):
        """Transactions in different accounts should not link."""
        # Create second account
        account2 = Account(
            snaptrade_id="test-account-2",
            name="Test Account 2",
            account_number="67890",
            institution_name="Test Broker",
        )
        db_session.add(account2)
        db_session.commit()

        # Open in account 1
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="BUY_TO_OPEN",
            quantity=Decimal("5"),
            price=Decimal("2.00"),
            amount=Decimal("-1000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        # Close in account 2 (should NOT match)
        txn2 = Transaction(
            snaptrade_id="txn-2",
            account_id=account2.id,
            symbol="AAPL",
            trade_date=date(2025, 2, 15),
            type="SELL",
            quantity=Decimal("-5"),
            price=Decimal("3.00"),
            amount=Decimal("1500"),
            is_option=True,
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
            underlying_symbol="AAPL",
            option_action="SELL_TO_CLOSE",
        )
        db_session.add(txn2)
        db_session.commit()

        # Match account 1 only
        contract = ContractKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = linked_trade_service.auto_match_contract(db_session, contract)
        db_session.commit()

        # Should create 1 linked trade that's NOT closed (no matching close in account 1)
        assert len(linked_trades) == 1
        assert not linked_trades[0].is_closed


class TestPLCalculation:
    """Test P/L calculation."""

    def test_pl_calculation_profit(self, db_session, account):
        """Test P/L calculation for profitable trade."""
        # Buy @ $2.00, sell @ $3.00 = $100 profit per contract
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="BUY_TO_OPEN",
            quantity=Decimal("1"),
            price=Decimal("2.00"),
            amount=Decimal("-200"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="SELL_TO_CLOSE",
            quantity=Decimal("-1"),
            price=Decimal("3.00"),
            amount=Decimal("300"),
            trade_date=date(2025, 2, 15),
            txn_id=2,
        )

        contract = ContractKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = linked_trade_service.auto_match_contract(db_session, contract)
        db_session.commit()

        # Calculate P/L
        pl = linked_trade_service.calculate_linked_trade_pl(
            db_session, linked_trades[0].id
        )

        # Should be profit: -200 + 300 = 100
        assert pl == Decimal("100")


class TestOrphanHandling:
    """Test handling of unmatched transactions."""

    def test_open_without_close(self, db_session, account):
        """Open position without close should remain open."""
        create_option_transaction(
            db_session,
            account,
            underlying="AAPL",
            option_type="CALL",
            strike=Decimal("150"),
            expiration=date(2025, 3, 21),
            action="BUY_TO_OPEN",
            quantity=Decimal("5"),
            price=Decimal("2.00"),
            amount=Decimal("-1000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )

        contract = ContractKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = linked_trade_service.auto_match_contract(db_session, contract)
        db_session.commit()

        assert len(linked_trades) == 1
        lt = linked_trades[0]
        assert not lt.is_closed
        assert lt.total_opened_quantity == Decimal("5")
        assert lt.total_closed_quantity == Decimal("0")
