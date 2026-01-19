"""Tests for lot service (FIFO matching for options and stocks)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Account, Base, LotTransaction, TradeLot, Transaction
from app.services import lot_service
from app.services.lot_service import OptionKey


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


def create_stock_transaction(
    db_session,
    account,
    symbol: str,
    txn_type: str,  # BUY or SELL
    quantity: Decimal,
    price: Decimal,
    amount: Decimal,
    trade_date: date,
    txn_id: int,
) -> Transaction:
    """Helper to create stock transaction."""
    txn = Transaction(
        snaptrade_id=f"txn-{txn_id}",
        account_id=account.id,
        symbol=symbol,
        trade_date=trade_date,
        type=txn_type,
        quantity=quantity,
        price=price,
        amount=amount,
        is_option=False,
    )
    db_session.add(txn)
    db_session.commit()
    return txn


class TestStockFIFOMatching:
    """Test FIFO matching for stocks."""

    def test_stock_buy_sell_creates_lot(self, db_session, account):
        """Buy then sell stock should create closed lot."""
        create_stock_transaction(
            db_session,
            account,
            symbol="AAPL",
            txn_type="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            amount=Decimal("-15000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        create_stock_transaction(
            db_session,
            account,
            symbol="AAPL",
            txn_type="SELL",
            quantity=Decimal("-100"),
            price=Decimal("160.00"),
            amount=Decimal("16000"),
            trade_date=date(2025, 2, 15),
            txn_id=2,
        )

        lot_service.match_all(db_session, account.id)
        db_session.commit()

        lots, _ = lot_service.get_all_lots(db_session)
        assert len(lots) == 1
        lot = lots[0]
        assert lot.instrument_type == "STOCK"
        assert lot.symbol == "AAPL"
        assert lot.is_closed
        assert lot.total_opened_quantity == Decimal("100")
        assert lot.total_closed_quantity == Decimal("100")

    def test_stock_partial_sell(self, db_session, account):
        """Partial sell should leave lot open with remaining quantity."""
        create_stock_transaction(
            db_session,
            account,
            symbol="AAPL",
            txn_type="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            amount=Decimal("-15000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        create_stock_transaction(
            db_session,
            account,
            symbol="AAPL",
            txn_type="SELL",
            quantity=Decimal("-60"),
            price=Decimal("160.00"),
            amount=Decimal("9600"),
            trade_date=date(2025, 2, 15),
            txn_id=2,
        )

        lot_service.match_all(db_session, account.id)
        db_session.commit()

        lots, _ = lot_service.get_all_lots(db_session)
        assert len(lots) == 1
        lot = lots[0]
        assert lot.instrument_type == "STOCK"
        assert not lot.is_closed
        assert lot.total_opened_quantity == Decimal("100")
        assert lot.total_closed_quantity == Decimal("60")
        assert lot.remaining_quantity == Decimal("40")


class TestLotCreationRules:
    """Test when lots should/shouldn't be created."""

    def test_single_open_no_lot(self, db_session, account):
        """Single open transaction should NOT create a lot."""
        create_stock_transaction(
            db_session,
            account,
            symbol="AAPL",
            txn_type="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            amount=Decimal("-15000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )

        lot_service.match_all(db_session, account.id)
        db_session.commit()

        lots, _ = lot_service.get_all_lots(db_session)
        assert len(lots) == 0  # No lot created for single open

    def test_two_opens_creates_lot(self, db_session, account):
        """Two opens for same position should create a lot."""
        create_stock_transaction(
            db_session,
            account,
            symbol="AAPL",
            txn_type="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            amount=Decimal("-15000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        create_stock_transaction(
            db_session,
            account,
            symbol="AAPL",
            txn_type="BUY",
            quantity=Decimal("50"),
            price=Decimal("155.00"),
            amount=Decimal("-7750"),
            trade_date=date(2025, 1, 20),
            txn_id=2,
        )

        lot_service.match_all(db_session, account.id)
        db_session.commit()

        lots, _ = lot_service.get_all_lots(db_session)
        assert len(lots) == 1
        lot = lots[0]
        assert not lot.is_closed  # Still open
        assert lot.total_opened_quantity == Decimal("150")
        assert len(lot.legs) == 2  # Both opens linked

    def test_single_open_with_close_creates_lot(self, db_session, account):
        """One open + one close should create a lot."""
        create_stock_transaction(
            db_session,
            account,
            symbol="AAPL",
            txn_type="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            amount=Decimal("-15000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        create_stock_transaction(
            db_session,
            account,
            symbol="AAPL",
            txn_type="SELL",
            quantity=Decimal("-100"),
            price=Decimal("160.00"),
            amount=Decimal("16000"),
            trade_date=date(2025, 2, 15),
            txn_id=2,
        )

        lot_service.match_all(db_session, account.id)
        db_session.commit()

        lots, _ = lot_service.get_all_lots(db_session)
        assert len(lots) == 1
        lot = lots[0]
        assert lot.is_closed
        assert len(lot.legs) == 2  # One open + one close

    def test_single_option_open_no_lot(self, db_session, account):
        """Single option open should NOT create a lot (same rule as stocks)."""
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

        lot_service.match_all(db_session, account.id)
        db_session.commit()

        lots, _ = lot_service.get_all_lots(db_session)
        assert len(lots) == 0  # No lot for single option open


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
        contract = OptionKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = lot_service.auto_match_contract(db_session, contract)
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

        contract = OptionKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = lot_service.auto_match_contract(db_session, contract)
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

        contract = OptionKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = lot_service.auto_match_contract(db_session, contract)
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

        contract = OptionKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="PUT",
            strike_price=Decimal("140"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = lot_service.auto_match_contract(db_session, contract)
        db_session.commit()

        assert len(linked_trades) == 1
        lt = linked_trades[0]
        assert lt.direction == "SHORT"
        assert lt.is_closed


class TestCrossAccountNoMatch:
    """Test that different accounts don't match."""

    def test_cross_account_no_match(self, db_session, account):
        """Transactions in different accounts should not link.

        With new lot creation rules: single open in account 1 with no closes
        (the close is in account 2) means no lot is created for account 1.
        This confirms cross-account isolation works correctly.
        """
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
        contract = OptionKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = lot_service.auto_match_contract(db_session, contract)
        db_session.commit()

        # Single open with no closes (close is in different account) = no lot created
        assert len(linked_trades) == 0


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

        contract = OptionKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = lot_service.auto_match_contract(db_session, contract)
        db_session.commit()

        # Calculate P/L
        pl = lot_service.calculate_linked_trade_pl(db_session, linked_trades[0].id)

        # Should be profit: -200 + 300 = 100
        assert pl == Decimal("100")


class TestOrphanHandling:
    """Test handling of unmatched transactions."""

    def test_single_open_without_close_no_lot(self, db_session, account):
        """Single open position without close should NOT create a lot.

        This is the new behavior: lots are only created when there's
        something to link (2+ opens or any close exists).
        """
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

        contract = OptionKey(
            account_id=account.id,
            underlying_symbol="AAPL",
            option_type="CALL",
            strike_price=Decimal("150"),
            expiration_date=date(2025, 3, 21),
        )
        linked_trades = lot_service.auto_match_contract(db_session, contract)
        db_session.commit()

        # Single open with no closes = no lot created (new behavior)
        assert len(linked_trades) == 0


class TestGetPlSummaryDateFiltering:
    def test_filters_by_start_date(self, db_session):
        """Only includes lots closed on or after start_date."""
        account = Account(
            snaptrade_id="test-pl-summary",
            name="Test",
            account_number="12345",
            institution_name="Test",
        )
        db_session.add(account)
        db_session.flush()

        # Create two closed lots with different close dates via legs
        lot1 = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="AAPL",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("100"),
            is_closed=True,
        )
        lot2 = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="MSFT",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("200"),
            is_closed=True,
        )
        db_session.add_all([lot1, lot2])
        db_session.flush()

        # Add closing transactions with dates
        txn1 = Transaction(
            snaptrade_id="txn-1",
            account_id=account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 5),
            type="SELL",
            quantity=Decimal("10"),
            amount=Decimal("1000"),
        )
        txn2 = Transaction(
            snaptrade_id="txn-2",
            account_id=account.id,
            symbol="MSFT",
            trade_date=date(2025, 1, 15),
            type="SELL",
            quantity=Decimal("10"),
            amount=Decimal("2000"),
        )
        db_session.add_all([txn1, txn2])
        db_session.flush()

        leg1 = LotTransaction(
            lot_id=lot1.id,
            transaction_id=txn1.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 5),
            leg_type="CLOSE",
            price_per_contract=Decimal("10"),
        )
        leg2 = LotTransaction(
            lot_id=lot2.id,
            transaction_id=txn2.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 15),
            leg_type="CLOSE",
            price_per_contract=Decimal("10"),
        )
        db_session.add_all([leg1, leg2])
        db_session.commit()

        # Filter: only lots closed on/after Jan 10
        result = lot_service.get_pl_summary(db_session, start_date=date(2025, 1, 10))

        assert result["total_pl"] == Decimal("200")  # Only lot2
        assert result["closed_count"] == 1

    def test_filters_by_end_date(self, db_session):
        """Only includes lots closed on or before end_date."""
        account = Account(
            snaptrade_id="test-pl-summary-2",
            name="Test",
            account_number="12346",
            institution_name="Test",
        )
        db_session.add(account)
        db_session.flush()

        lot1 = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="AAPL",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("100"),
            is_closed=True,
        )
        lot2 = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="MSFT",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("200"),
            is_closed=True,
        )
        db_session.add_all([lot1, lot2])
        db_session.flush()

        txn1 = Transaction(
            snaptrade_id="txn-3",
            account_id=account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 5),
            type="SELL",
            quantity=Decimal("10"),
            amount=Decimal("1000"),
        )
        txn2 = Transaction(
            snaptrade_id="txn-4",
            account_id=account.id,
            symbol="MSFT",
            trade_date=date(2025, 1, 15),
            type="SELL",
            quantity=Decimal("10"),
            amount=Decimal("2000"),
        )
        db_session.add_all([txn1, txn2])
        db_session.flush()

        leg1 = LotTransaction(
            lot_id=lot1.id,
            transaction_id=txn1.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 5),
            leg_type="CLOSE",
            price_per_contract=Decimal("10"),
        )
        leg2 = LotTransaction(
            lot_id=lot2.id,
            transaction_id=txn2.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 15),
            leg_type="CLOSE",
            price_per_contract=Decimal("10"),
        )
        db_session.add_all([leg1, leg2])
        db_session.commit()

        # Filter: only lots closed on/before Jan 10
        result = lot_service.get_pl_summary(db_session, end_date=date(2025, 1, 10))

        assert result["total_pl"] == Decimal("100")  # Only lot1
        assert result["closed_count"] == 1
