from datetime import date

from app.models import Account, Tag, Transaction
from app.services import tag_service


def test_create_tag(db_session):
    """Test creating a tag."""
    tag = tag_service.create_tag(db_session, "Tax Loss", "warning")
    assert tag.id is not None
    assert tag.name == "Tax Loss"
    assert tag.color == "warning"


def test_get_all_tags(db_session):
    """Test listing all tags."""
    tag_service.create_tag(db_session, "Tag A", "primary")
    tag_service.create_tag(db_session, "Tag B", "secondary")

    tags = tag_service.get_all_tags(db_session)
    assert len(tags) == 2
    assert tags[0].name == "Tag A"  # ordered by name


def test_delete_tag(db_session):
    """Test deleting a tag."""
    tag = tag_service.create_tag(db_session, "Delete Me", "error")
    tag_id = tag.id

    result = tag_service.delete_tag(db_session, tag_id)
    assert result is True

    tag = tag_service.get_tag_by_id(db_session, tag_id)
    assert tag is None


def test_add_tag_to_transaction(db_session):
    """Test adding a tag to a transaction."""
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
        amount=100.00,
    )
    db_session.add(txn)
    db_session.commit()

    tag = tag_service.create_tag(db_session, "Test Tag", "info")

    result = tag_service.add_tag_to_transaction(db_session, txn.id, tag.id)
    assert result is True

    tags = tag_service.get_transaction_tags(db_session, txn.id)
    assert len(tags) == 1
    assert tags[0].name == "Test Tag"


def test_remove_tag_from_transaction(db_session):
    """Test removing a tag from a transaction."""
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
        amount=-50.00,
    )
    db_session.add(txn)
    db_session.commit()

    tag = tag_service.create_tag(db_session, "Remove Me", "accent")
    tag_service.add_tag_to_transaction(db_session, txn.id, tag.id)

    result = tag_service.remove_tag_from_transaction(db_session, txn.id, tag.id)
    assert result is True

    tags = tag_service.get_transaction_tags(db_session, txn.id)
    assert len(tags) == 0


def test_tag_list_endpoint(client, db_session):
    """Test the tag list API endpoint."""
    tag_service.create_tag(db_session, "API Tag", "success")

    response = client.get("/tags/")
    assert response.status_code == 200
    assert "API Tag" in response.text


def test_create_tag_endpoint(client, db_session):
    """Test the create tag API endpoint."""
    response = client.post(
        "/tags/",
        data={"name": "New Tag", "color": "primary"},
    )
    assert response.status_code == 200
    assert "New Tag" in response.text


def test_delete_tag_endpoint(client, db_session):
    """Test the delete tag API endpoint."""
    tag = tag_service.create_tag(db_session, "To Delete", "error")

    response = client.delete(f"/tags/{tag.id}")
    assert response.status_code == 200
    assert "To Delete" not in response.text
