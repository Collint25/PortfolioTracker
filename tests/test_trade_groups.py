from datetime import date
from decimal import Decimal

from app.models import Account, Transaction
from app.services import trade_group_service


def test_create_trade_group(db_session):
    """Test creating a trade group."""
    group = trade_group_service.create_trade_group(
        db_session,
        name="AAPL Iron Condor",
        strategy_type="iron_condor",
        description="Test trade group",
    )
    assert group.id is not None
    assert group.name == "AAPL Iron Condor"
    assert group.strategy_type == "iron_condor"
    assert group.description == "Test trade group"


def test_get_all_trade_groups(db_session):
    """Test listing all trade groups."""
    trade_group_service.create_trade_group(db_session, "Group A")
    trade_group_service.create_trade_group(db_session, "Group B")

    groups = trade_group_service.get_all_trade_groups(db_session)
    assert len(groups) == 2


def test_update_trade_group(db_session):
    """Test updating a trade group."""
    group = trade_group_service.create_trade_group(db_session, "Original Name")

    updated = trade_group_service.update_trade_group(
        db_session,
        group.id,
        name="Updated Name",
        strategy_type="vertical_spread",
    )

    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.strategy_type == "vertical_spread"


def test_delete_trade_group(db_session):
    """Test deleting a trade group."""
    group = trade_group_service.create_trade_group(db_session, "Delete Me")
    group_id = group.id

    result = trade_group_service.delete_trade_group(db_session, group_id)
    assert result is True

    group = trade_group_service.get_trade_group_by_id(db_session, group_id)
    assert group is None


def test_add_transaction_to_group(db_session):
    """Test adding a transaction to a trade group."""
    # Create account and transaction first
    account = Account(
        snaptrade_id="test-account",
        account_number="1234",
        name="Test Account",
    )
    db_session.add(account)
    db_session.commit()

    txn = Transaction(
        snaptrade_id="test-txn",
        account_id=account.id,
        trade_date=date(2024, 1, 15),
        type="BUY",
        amount=Decimal("100.00"),
    )
    db_session.add(txn)
    db_session.commit()

    group = trade_group_service.create_trade_group(db_session, "Test Group")

    result = trade_group_service.add_transaction_to_group(db_session, group.id, txn.id)
    assert result is True

    transactions = trade_group_service.get_group_transactions(db_session, group.id)
    assert len(transactions) == 1
    assert transactions[0].id == txn.id


def test_remove_transaction_from_group(db_session):
    """Test removing a transaction from a trade group."""
    # Create account and transaction
    account = Account(
        snaptrade_id="test-account-2",
        account_number="5678",
        name="Test Account 2",
    )
    db_session.add(account)
    db_session.commit()

    txn = Transaction(
        snaptrade_id="test-txn-2",
        account_id=account.id,
        trade_date=date(2024, 1, 15),
        type="SELL",
        amount=Decimal("-50.00"),
    )
    db_session.add(txn)
    db_session.commit()

    group = trade_group_service.create_trade_group(db_session, "Test Group 2")
    trade_group_service.add_transaction_to_group(db_session, group.id, txn.id)

    result = trade_group_service.remove_transaction_from_group(
        db_session, group.id, txn.id
    )
    assert result is True

    transactions = trade_group_service.get_group_transactions(db_session, group.id)
    assert len(transactions) == 0


def test_calculate_group_pl(db_session):
    """Test P/L calculation for a trade group."""
    # Create account
    account = Account(
        snaptrade_id="test-account-pl",
        account_number="9999",
        name="P/L Test Account",
    )
    db_session.add(account)
    db_session.commit()

    # Create transactions with different amounts
    txn1 = Transaction(
        snaptrade_id="txn-pl-1",
        account_id=account.id,
        trade_date=date(2024, 1, 15),
        type="SELL",
        amount=Decimal("150.00"),  # Credit received
    )
    txn2 = Transaction(
        snaptrade_id="txn-pl-2",
        account_id=account.id,
        trade_date=date(2024, 1, 15),
        type="BUY",
        amount=Decimal("-50.00"),  # Debit paid
    )
    db_session.add_all([txn1, txn2])
    db_session.commit()

    group = trade_group_service.create_trade_group(db_session, "P/L Group")
    trade_group_service.add_transaction_to_group(db_session, group.id, txn1.id)
    trade_group_service.add_transaction_to_group(db_session, group.id, txn2.id)

    pl = trade_group_service.calculate_group_pl(db_session, group.id)
    assert pl == Decimal("100.00")


def test_create_group_from_external_reference(db_session):
    """Test creating a group from transactions with same external_reference_id."""
    # Create account
    account = Account(
        snaptrade_id="test-account-ext-ref",
        account_number="1111",
        name="Ext Ref Test Account",
    )
    db_session.add(account)
    db_session.commit()

    # Create transactions with same external_reference_id
    ext_ref = "multi-leg-trade-123"
    txn1 = Transaction(
        snaptrade_id="txn-ext-1",
        account_id=account.id,
        trade_date=date(2024, 1, 15),
        type="BUY",
        symbol="AAPL",
        amount=Decimal("-100.00"),
        external_reference_id=ext_ref,
    )
    txn2 = Transaction(
        snaptrade_id="txn-ext-2",
        account_id=account.id,
        trade_date=date(2024, 1, 15),
        type="SELL",
        symbol="AAPL",
        amount=Decimal("200.00"),
        external_reference_id=ext_ref,
    )
    db_session.add_all([txn1, txn2])
    db_session.commit()

    group = trade_group_service.create_group_from_external_reference(
        db_session,
        ext_ref,
        strategy_type="vertical_spread",
    )

    assert group is not None
    assert group.strategy_type == "vertical_spread"
    assert len(group.transactions) == 2


def test_get_transaction_groups(db_session):
    """Test getting groups that contain a transaction."""
    # Create account and transaction
    account = Account(
        snaptrade_id="test-account-groups",
        account_number="2222",
        name="Groups Test Account",
    )
    db_session.add(account)
    db_session.commit()

    txn = Transaction(
        snaptrade_id="txn-groups",
        account_id=account.id,
        trade_date=date(2024, 1, 15),
        type="BUY",
        amount=Decimal("100.00"),
    )
    db_session.add(txn)
    db_session.commit()

    group1 = trade_group_service.create_trade_group(db_session, "Group 1")
    group2 = trade_group_service.create_trade_group(db_session, "Group 2")

    trade_group_service.add_transaction_to_group(db_session, group1.id, txn.id)
    trade_group_service.add_transaction_to_group(db_session, group2.id, txn.id)

    groups = trade_group_service.get_transaction_groups(db_session, txn.id)
    assert len(groups) == 2


def test_trade_group_list_endpoint(client, db_session):
    """Test the trade group list endpoint."""
    trade_group_service.create_trade_group(db_session, "API Test Group")

    response = client.get("/trade-groups/")
    assert response.status_code == 200
    assert "API Test Group" in response.text


def test_create_trade_group_endpoint(client, db_session):
    """Test the create trade group endpoint."""
    response = client.post(
        "/trade-groups/",
        data={
            "name": "New Group",
            "strategy_type": "iron_condor",
            "description": "Test description",
        },
    )
    assert response.status_code == 200
    assert "New Group" in response.text


def test_trade_group_detail_endpoint(client, db_session):
    """Test the trade group detail endpoint."""
    group = trade_group_service.create_trade_group(
        db_session, "Detail Test Group", "straddle"
    )

    response = client.get(f"/trade-groups/{group.id}")
    assert response.status_code == 200
    assert "Detail Test Group" in response.text
    assert "Straddle" in response.text


def test_trade_group_detail_404(client, db_session):
    """Test that nonexistent trade group returns 404."""
    response = client.get("/trade-groups/99999")
    assert response.status_code == 404
