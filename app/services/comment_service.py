from sqlalchemy.orm import Session

from app.models import Comment
from app.services import base


def get_comments_for_transaction(db: Session, transaction_id: int) -> list[Comment]:
    """Get all comments for a transaction, ordered by creation date."""
    return (
        db.query(Comment)
        .filter(Comment.transaction_id == transaction_id)
        .order_by(Comment.created_at.desc())
        .all()
    )


def get_comment_by_id(db: Session, comment_id: int) -> Comment | None:
    """Get a single comment by ID."""
    return base.get_by_id(db, Comment, comment_id)


def create_comment(db: Session, transaction_id: int, text: str) -> Comment:
    """Create a new comment on a transaction."""
    return base.create(db, Comment, transaction_id=transaction_id, text=text)


def update_comment(db: Session, comment_id: int, text: str) -> Comment | None:
    """Update an existing comment."""
    return base.update(db, Comment, comment_id, text=text)


def delete_comment(db: Session, comment_id: int) -> bool:
    """Delete a comment. Returns True if deleted, False if not found."""
    return base.delete(db, Comment, comment_id)
