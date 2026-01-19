"""Tests for metrics service."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Account, Base, LotTransaction, Position, TradeLot, Transaction
from app.services import metrics_service


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestGetMetrics:
    def test_returns_metrics_result(self, db_session):
        """Returns MetricsResult with summary and time series."""
        account = Account(
            snaptrade_id="test-metrics-1",
            name="Test",
            account_number="12345",
            institution_name="Test",
        )
        db_session.add(account)
        db_session.flush()

        # Create a closed lot
        lot = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="AAPL",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("150"),
            is_closed=True,
        )
        db_session.add(lot)
        db_session.flush()

        txn = Transaction(
            snaptrade_id="txn-1",
            account_id=account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 15),
            type="SELL",
            quantity=Decimal("10"),
            amount=Decimal("1500"),
        )
        db_session.add(txn)
        db_session.flush()

        leg = LotTransaction(
            lot_id=lot.id,
            transaction_id=txn.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 15),
            leg_type="CLOSE",
            price_per_contract=Decimal("15"),
        )
        db_session.add(leg)
        db_session.commit()

        result = metrics_service.get_metrics(db_session)

        assert isinstance(result, metrics_service.MetricsResult)
        assert result.summary.total_realized_pl == Decimal("150")
        assert result.summary.total_trades == 1
        assert result.summary.winning_trades == 1
        assert result.summary.win_rate == 1.0
        assert len(result.pl_over_time) == 1
        assert result.pl_over_time[0].cumulative_pl == Decimal("150")

    def test_filters_by_account_ids(self, db_session):
        """Respects account_ids filter."""
        account1 = Account(
            snaptrade_id="test-metrics-2",
            name="Account1",
            account_number="12346",
            institution_name="Test",
        )
        account2 = Account(
            snaptrade_id="test-metrics-3",
            name="Account2",
            account_number="12347",
            institution_name="Test",
        )
        db_session.add_all([account1, account2])
        db_session.flush()

        lot1 = TradeLot(
            account_id=account1.id,
            instrument_type="STOCK",
            symbol="AAPL",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("100"),
            is_closed=True,
        )
        lot2 = TradeLot(
            account_id=account2.id,
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
            snaptrade_id="txn-2",
            account_id=account1.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 10),
            type="SELL",
            quantity=Decimal("10"),
            amount=Decimal("1000"),
        )
        txn2 = Transaction(
            snaptrade_id="txn-3",
            account_id=account2.id,
            symbol="MSFT",
            trade_date=date(2025, 1, 10),
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
            trade_date=date(2025, 1, 10),
            leg_type="CLOSE",
            price_per_contract=Decimal("10"),
        )
        leg2 = LotTransaction(
            lot_id=lot2.id,
            transaction_id=txn2.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 10),
            leg_type="CLOSE",
            price_per_contract=Decimal("20"),
        )
        db_session.add_all([leg1, leg2])
        db_session.commit()

        result = metrics_service.get_metrics(db_session, account_ids=[account1.id])

        assert result.summary.total_realized_pl == Decimal("100")

    def test_includes_unrealized_pl(self, db_session):
        """Calculates unrealized P/L from open positions."""
        account = Account(
            snaptrade_id="test-metrics-4",
            name="Test",
            account_number="12348",
            institution_name="Test",
        )
        db_session.add(account)
        db_session.flush()

        # Position with unrealized gain
        position = Position(
            snaptrade_id="pos-1",
            account_id=account.id,
            symbol="AAPL",
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            current_price=Decimal("120"),
        )
        db_session.add(position)
        db_session.commit()

        result = metrics_service.get_metrics(db_session)

        # Unrealized = (120 - 100) * 10 = 200
        assert result.summary.total_unrealized_pl == Decimal("200")

    def test_echoes_filters_applied(self, db_session):
        """Returns filters_applied in result."""
        account = Account(
            snaptrade_id="test-metrics-5",
            name="Test",
            account_number="12349",
            institution_name="Test",
        )
        db_session.add(account)
        db_session.commit()

        result = metrics_service.get_metrics(
            db_session,
            account_ids=[account.id],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        assert result.filters_applied.account_ids == [account.id]
        assert result.filters_applied.start_date == date(2025, 1, 1)
        assert result.filters_applied.end_date == date(2025, 12, 31)
