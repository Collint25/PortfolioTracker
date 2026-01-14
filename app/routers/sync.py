import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import sync_service

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.post("/", response_class=HTMLResponse)
def trigger_sync(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Trigger a full sync from SnapTrade."""
    try:
        logger.info("Starting sync...")
        results = sync_service.sync_all(db)
        logger.info("Sync completed: %s", results)
        return templates.TemplateResponse(
            request=request,
            name="partials/sync_result.html",
            context={"success": True, "results": results},
        )
    except Exception as e:
        logger.exception("Sync failed: %s", e)
        return templates.TemplateResponse(
            request=request,
            name="partials/sync_result.html",
            context={"success": False, "error": str(e)},
        )


@router.get("/status", response_class=HTMLResponse)
def sync_status(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Get current sync status (record counts)."""
    from app.models import Account, Position, Transaction

    counts = {
        "accounts": db.query(Account).count(),
        "positions": db.query(Position).count(),
        "transactions": db.query(Transaction).count(),
    }

    return templates.TemplateResponse(
        request=request,
        name="partials/sync_status.html",
        context=counts,
    )
