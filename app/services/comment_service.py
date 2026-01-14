from sqlalchemy.orm import Session

from app.models import Comment


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
    return db.query(Comment).filter(Comment.id == comment_id).first()


def create_comment(db: Session, transaction_id: int, text: str) -> Comment:
    """Create a new comment on a transaction."""
    comment = Comment(transaction_id=transaction_id, text=text)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def update_comment(db: Session, comment_id: int, text: str) -> Comment | None:
    """Update an existing comment."""
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        return None
    comment.text = text
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, comment_id: int) -> bool:
    """Delete a comment. Returns True if deleted, False if not found."""
    comment = get_comment_by_id(db, comment_id)
    if not comment:
        return False
    db.delete(comment)
    db.commit()
    return True
