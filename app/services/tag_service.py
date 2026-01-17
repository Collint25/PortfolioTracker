from sqlalchemy.orm import Session

from app.models import Tag, Transaction
from app.services import base


def get_all_tags(db: Session) -> list[Tag]:
    """Get all tags ordered by name."""
    return base.get_all(db, Tag, order_by=Tag.name)


def get_tag_by_id(db: Session, tag_id: int) -> Tag | None:
    """Get a single tag by ID."""
    return base.get_by_id(db, Tag, tag_id)


def get_tag_by_name(db: Session, name: str) -> Tag | None:
    """Get a single tag by name."""
    return db.query(Tag).filter(Tag.name == name).first()


def create_tag(db: Session, name: str, color: str = "neutral") -> Tag:
    """Create a new tag."""
    return base.create(db, Tag, name=name, color=color)


def update_tag(
    db: Session, tag_id: int, name: str | None = None, color: str | None = None
) -> Tag | None:
    """Update an existing tag."""
    return base.update(db, Tag, tag_id, name=name, color=color)


def delete_tag(db: Session, tag_id: int) -> bool:
    """Delete a tag. Returns True if deleted, False if not found."""
    return base.delete(db, Tag, tag_id)


def add_tag_to_transaction(db: Session, transaction_id: int, tag_id: int) -> bool:
    """Add a tag to a transaction. Returns True if successful."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    tag = get_tag_by_id(db, tag_id)
    if not transaction or not tag:
        return False
    if tag not in transaction.tags:
        transaction.tags.append(tag)
        db.commit()
    return True


def remove_tag_from_transaction(db: Session, transaction_id: int, tag_id: int) -> bool:
    """Remove a tag from a transaction. Returns True if successful."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    tag = get_tag_by_id(db, tag_id)
    if not transaction or not tag:
        return False
    if tag in transaction.tags:
        transaction.tags.remove(tag)
        db.commit()
    return True


def get_transaction_tags(db: Session, transaction_id: int) -> list[Tag]:
    """Get all tags for a transaction."""
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        return []
    return list(transaction.tags)
