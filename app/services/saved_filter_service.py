from sqlalchemy.orm import Session

from app.models import SavedFilter


def get_filters_for_page(db: Session, page: str) -> list[SavedFilter]:
    """Get all saved filters for a specific page."""
    return (
        db.query(SavedFilter)
        .filter(SavedFilter.page == page)
        .order_by(SavedFilter.is_favorite.desc(), SavedFilter.name)
        .all()
    )


def get_favorite_filter(db: Session, page: str) -> SavedFilter | None:
    """Get the favorite filter for a page (if any)."""
    return (
        db.query(SavedFilter)
        .filter(SavedFilter.page == page, SavedFilter.is_favorite == True)
        .first()
    )


def get_filter_by_id(db: Session, filter_id: int) -> SavedFilter | None:
    """Get a saved filter by ID."""
    return db.query(SavedFilter).filter(SavedFilter.id == filter_id).first()


def create_filter(
    db: Session, name: str, page: str, query_string: str, is_favorite: bool = False
) -> SavedFilter:
    """Create a new saved filter. query_string is the URL query string (without ?)."""
    # If setting as favorite, clear existing favorite for this page
    if is_favorite:
        db.query(SavedFilter).filter(
            SavedFilter.page == page, SavedFilter.is_favorite == True
        ).update({SavedFilter.is_favorite: False})

    saved_filter = SavedFilter(
        name=name,
        page=page,
        filter_json=query_string,  # Store query string directly
        is_favorite=is_favorite,
    )
    db.add(saved_filter)
    db.commit()
    db.refresh(saved_filter)
    return saved_filter


def set_favorite(db: Session, filter_id: int) -> SavedFilter | None:
    """Set a filter as the favorite for its page."""
    saved_filter = get_filter_by_id(db, filter_id)
    if not saved_filter:
        return None

    # Clear existing favorite for this page
    db.query(SavedFilter).filter(
        SavedFilter.page == saved_filter.page, SavedFilter.is_favorite == True
    ).update({SavedFilter.is_favorite: False})

    # Set this one as favorite
    saved_filter.is_favorite = True
    db.commit()
    db.refresh(saved_filter)
    return saved_filter


def clear_favorite(db: Session, filter_id: int) -> SavedFilter | None:
    """Remove favorite status from a filter."""
    saved_filter = get_filter_by_id(db, filter_id)
    if not saved_filter:
        return None

    saved_filter.is_favorite = False
    db.commit()
    db.refresh(saved_filter)
    return saved_filter


def delete_filter(db: Session, filter_id: int) -> bool:
    """Delete a saved filter."""
    saved_filter = get_filter_by_id(db, filter_id)
    if not saved_filter:
        return False

    db.delete(saved_filter)
    db.commit()
    return True


def get_query_string(saved_filter: SavedFilter) -> str:
    """Get the query string for a saved filter."""
    return saved_filter.filter_json or ""
