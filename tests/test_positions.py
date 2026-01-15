from decimal import Decimal

from app.models import Account, Position
from app.services import position_service


def test_accounts_page_renders(client):
    """Accounts page renders successfully."""
    response = client.get("/accounts")
    assert response.status_code == 200
    assert "Accounts" in response.text


def test_positions_page_404_invalid_account(client):
    """Positions page returns 404 for non-existent account."""
    response = client.get("/accounts/99999/positions")
    assert response.status_code == 404


def test_positions_page_renders(client, db_session):
    """Positions page renders for valid account."""
    # Create test account
    account = Account(
        snaptrade_id="test-account-123",
        name="Test Account",
        account_number="1234567890",
    )
    db_session.add(account)
    db_session.commit()

    response = client.get(f"/accounts/{account.id}/positions")
    assert response.status_code == 200
    assert "Test Account" in response.text


def test_positions_page_with_positions(client, db_session):
    """Positions page displays positions correctly."""
    # Create test account
    account = Account(
        snaptrade_id="test-account-456",
        name="Test Account",
        account_number="1234567890",
    )
    db_session.add(account)
    db_session.commit()

    # Create test position
    position = Position(
        snaptrade_id="test-position-123",
        account_id=account.id,
        symbol="AAPL",
        quantity=Decimal("100"),
        average_cost=Decimal("150.00"),
        current_price=Decimal("175.00"),
    )
    db_session.add(position)
    db_session.commit()

    response = client.get(f"/accounts/{account.id}/positions")
    assert response.status_code == 200
    assert "AAPL" in response.text
    assert "100" in response.text


def test_calculate_market_value(db_session):
    """Market value calculation works correctly."""
    account = Account(
        snaptrade_id="test-mv",
        name="Test",
        account_number="123",
    )
    db_session.add(account)
    db_session.commit()

    position = Position(
        snaptrade_id="test-pos-mv",
        account_id=account.id,
        symbol="TEST",
        quantity=Decimal("10"),
        average_cost=Decimal("100"),
        current_price=Decimal("120"),
    )
    db_session.add(position)
    db_session.commit()

    market_value = position_service.calculate_market_value(position)
    assert market_value == Decimal("1200")


def test_calculate_gain_loss(db_session):
    """Gain/loss calculation works correctly."""
    account = Account(
        snaptrade_id="test-gl",
        name="Test",
        account_number="123",
    )
    db_session.add(account)
    db_session.commit()

    position = Position(
        snaptrade_id="test-pos-gl",
        account_id=account.id,
        symbol="TEST",
        quantity=Decimal("10"),
        average_cost=Decimal("100"),
        current_price=Decimal("120"),
    )
    db_session.add(position)
    db_session.commit()

    gain_loss = position_service.calculate_gain_loss(position)
    # Market value: 10 * 120 = 1200
    # Cost basis: 10 * 100 = 1000
    # Gain: 1200 - 1000 = 200
    assert gain_loss == Decimal("200")


def test_calculate_gain_loss_percent(db_session):
    """Gain/loss percentage calculation works correctly."""
    account = Account(
        snaptrade_id="test-glp",
        name="Test",
        account_number="123",
    )
    db_session.add(account)
    db_session.commit()

    position = Position(
        snaptrade_id="test-pos-glp",
        account_id=account.id,
        symbol="TEST",
        quantity=Decimal("10"),
        average_cost=Decimal("100"),
        current_price=Decimal("120"),
    )
    db_session.add(position)
    db_session.commit()

    gain_loss_percent = position_service.calculate_gain_loss_percent(position)
    # Gain: 200, Cost basis: 1000, Percent: 20%
    assert gain_loss_percent == Decimal("20")


def test_get_account_positions_summary(db_session):
    """Account positions summary includes totals."""
    account = Account(
        snaptrade_id="test-summary",
        name="Test",
        account_number="123",
    )
    db_session.add(account)
    db_session.commit()

    position1 = Position(
        snaptrade_id="test-pos-s1",
        account_id=account.id,
        symbol="AAPL",
        quantity=Decimal("10"),
        average_cost=Decimal("100"),
        current_price=Decimal("120"),
    )
    position2 = Position(
        snaptrade_id="test-pos-s2",
        account_id=account.id,
        symbol="GOOG",
        quantity=Decimal("5"),
        average_cost=Decimal("200"),
        current_price=Decimal("250"),
    )
    db_session.add_all([position1, position2])
    db_session.commit()

    positions, totals = position_service.get_account_positions_summary(
        db_session, account.id
    )

    assert len(positions) == 2
    # AAPL: MV=1200, CB=1000
    # GOOG: MV=1250, CB=1000
    # Total MV: 2450, Total CB: 2000, Gain: 450
    assert totals["market_value"] == Decimal("2450")
    assert totals["cost_basis"] == Decimal("2000")
    assert totals["gain_loss"] == Decimal("450")
