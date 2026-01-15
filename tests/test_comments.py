from datetime import date

from app.models import Account, Transaction
from app.services import comment_service


def test_create_comment(db_session):
    """Test creating a comment on a transaction."""
    # Create account and transaction
    account = Account(
        snaptrade_id="comment-test-account",
        account_number="9999",
        name="Comment Test Account",
    )
    db_session.add(account)
    db_session.commit()

    txn = Transaction(
        snaptrade_id="comment-test-txn",
        account_id=account.id,
        trade_date=date(2024, 2, 1),
        type="BUY",
        amount=200.00,
    )
    db_session.add(txn)
    db_session.commit()

    comment = comment_service.create_comment(db_session, txn.id, "This is a test note")
    assert comment.id is not None
    assert comment.text == "This is a test note"
    assert comment.transaction_id == txn.id


def test_get_comments_for_transaction(db_session):
    """Test getting comments for a transaction."""
    # Create account and transaction
    account = Account(
        snaptrade_id="comments-list-account",
        account_number="8888",
        name="Comments List Account",
    )
    db_session.add(account)
    db_session.commit()

    txn = Transaction(
        snaptrade_id="comments-list-txn",
        account_id=account.id,
        trade_date=date(2024, 2, 1),
        type="SELL",
        amount=-150.00,
    )
    db_session.add(txn)
    db_session.commit()

    comment_service.create_comment(db_session, txn.id, "First comment")
    comment_service.create_comment(db_session, txn.id, "Second comment")

    comments = comment_service.get_comments_for_transaction(db_session, txn.id)
    assert len(comments) == 2


def test_delete_comment(db_session):
    """Test deleting a comment."""
    # Create account and transaction
    account = Account(
        snaptrade_id="delete-comment-account",
        account_number="7777",
        name="Delete Comment Account",
    )
    db_session.add(account)
    db_session.commit()

    txn = Transaction(
        snaptrade_id="delete-comment-txn",
        account_id=account.id,
        trade_date=date(2024, 2, 1),
        type="DIVIDEND",
        amount=25.00,
    )
    db_session.add(txn)
    db_session.commit()

    comment = comment_service.create_comment(db_session, txn.id, "Delete me")
    comment_id = comment.id

    result = comment_service.delete_comment(db_session, comment_id)
    assert result is True

    comment = comment_service.get_comment_by_id(db_session, comment_id)
    assert comment is None


def test_update_comment(db_session):
    """Test updating a comment."""
    # Create account and transaction
    account = Account(
        snaptrade_id="update-comment-account",
        account_number="6666",
        name="Update Comment Account",
    )
    db_session.add(account)
    db_session.commit()

    txn = Transaction(
        snaptrade_id="update-comment-txn",
        account_id=account.id,
        trade_date=date(2024, 2, 1),
        type="BUY",
        amount=300.00,
    )
    db_session.add(txn)
    db_session.commit()

    comment = comment_service.create_comment(db_session, txn.id, "Original text")

    updated = comment_service.update_comment(db_session, comment.id, "Updated text")
    assert updated.text == "Updated text"


def test_comment_endpoints(client, db_session):
    """Test comment API endpoints."""
    # Create account and transaction
    account = Account(
        snaptrade_id="endpoint-comment-account",
        account_number="5555",
        name="Endpoint Comment Account",
    )
    db_session.add(account)
    db_session.commit()

    txn = Transaction(
        snaptrade_id="endpoint-comment-txn",
        account_id=account.id,
        trade_date=date(2024, 2, 1),
        type="BUY",
        amount=400.00,
    )
    db_session.add(txn)
    db_session.commit()

    # Test creating a comment
    response = client.post(
        f"/comments/transaction/{txn.id}",
        data={"text": "API test comment"},
    )
    assert response.status_code == 200
    assert "API test comment" in response.text

    # Test getting comments
    response = client.get(f"/comments/transaction/{txn.id}")
    assert response.status_code == 200
    assert "API test comment" in response.text
