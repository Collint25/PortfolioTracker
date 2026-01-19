"""API endpoints for AJAX/autocomplete functionality."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction

router = APIRouter()


@router.get("/symbols")
def get_symbols(
    db: Session = Depends(get_db),
    q: str = Query(default="", description="Search query"),
) -> list[str]:
    """Get symbols for autocomplete, optionally filtered by query."""
    query = (
        db.query(Transaction.symbol).filter(Transaction.symbol.isnot(None)).distinct()
    )

    if q:
        query = query.filter(Transaction.symbol.ilike(f"{q}%"))

    query = query.order_by(Transaction.symbol).limit(20)
    results = query.all()
    return [r[0] for r in results if r[0]]


@router.get("/types")
def get_types(db: Session = Depends(get_db)) -> list[str]:
    """Get all transaction types."""
    results = db.query(Transaction.type).distinct().order_by(Transaction.type).all()
    return [r[0] for r in results if r[0]]
