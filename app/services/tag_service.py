from sqlalchemy.orm import Session

from app.models import Tag, Transaction


def get_all_tags(db: Session) -> list[Tag]:
    """Get all tags ordered by name."""
    return db.query(Tag).order_by(Tag.name).all()


def get_tag_by_id(db: Session, tag_id: int) -> Tag | None:
    """Get a single tag by ID."""
    return db.query(Tag).filter(Tag.id == tag_id).first()


def get_tag_by_name(db: Session, name: str) -> Tag | None:
    """Get a single tag by name."""
    return db.query(Tag).filter(Tag.name == name).first()


def create_tag(db: Session, name: str, color: str = "neutral") -> Tag:
    """Create a new tag."""
    tag = Tag(name=name, color=color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_tag(db: Session, tag_id: int, name: str | None = None, color: str | None = None) -> Tag | None:
    """Update an existing tag."""
    tag = get_tag_by_id(db, tag_id)
    if not tag:
        return None
    if name is not None:
        tag.name = name
    if color is not None:
        tag.color = color
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int) -> bool:
    """Delete a tag. Returns True if deleted, False if not found."""
    tag = get_tag_by_id(db, tag_id)
    if not tag:
        return False
    db.delete(tag)
    db.commit()
    return True


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
