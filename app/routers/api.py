"""API endpoints for AJAX/autocomplete functionality."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction

router = APIRouter()


@router.get("/types")
def get_types(db: Session = Depends(get_db)) -> list[str]:
    """Get all transaction types."""
    results = db.query(Transaction.type).distinct().order_by(Transaction.type).all()
    return [r[0] for r in results if r[0]]
