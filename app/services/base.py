"""Base CRUD operations for services."""

from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class CRUDMixin(Generic[T]):
    """
    Mixin class providing generic CRUD operations.

    Usage:
        class TagCRUD(CRUDMixin[Tag]):
            model = Tag

        tag_crud = TagCRUD()
        tag = tag_crud.get_by_id(db, 1)
    """

    model: type[T]

    def get_by_id(self, db: Session, id: int) -> T | None:
        """Get a single record by ID."""
        return db.query(self.model).filter(self.model.id == id).first()  # type: ignore[attr-defined]

    def get_all(self, db: Session, *, order_by: Any | None = None) -> list[T]:
        """Get all records, optionally ordered."""
        query = db.query(self.model)
        if order_by is not None:
            query = query.order_by(order_by)
        return query.all()

    def create(self, db: Session, **kwargs) -> T:
        """Create a new record."""
        obj = self.model(**kwargs)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, id: int, **kwargs) -> T | None:
        """Update an existing record. Returns None if not found."""
        obj = self.get_by_id(db, id)
        if not obj:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int) -> bool:
        """Delete a record. Returns True if deleted, False if not found."""
        obj = self.get_by_id(db, id)
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True


def get_by_id(db: Session, model: type[T], id: int) -> T | None:
    """Generic get by ID function."""
    return db.query(model).filter(model.id == id).first()  # type: ignore[attr-defined]


def get_all(db: Session, model: type[T], order_by: Any | None = None) -> list[T]:
    """Generic get all function."""
    query = db.query(model)
    if order_by is not None:
        query = query.order_by(order_by)
    return query.all()


def create(db: Session, model: type[T], **kwargs) -> T:
    """Generic create function."""
    obj = model(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update(db: Session, model: type[T], id: int, **kwargs) -> T | None:
    """Generic update function. Returns None if not found."""
    obj = get_by_id(db, model, id)
    if not obj:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete(db: Session, model: type[T], id: int) -> bool:
    """Generic delete function. Returns True if deleted."""
    obj = get_by_id(db, model, id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
