"""Router for trade lots (open/close matching)."""

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import account_service, lot_service
from app.services.filters import (
    LotFilter,
    PaginationParams,
    build_lot_filter_from_request,
)
from app.utils.htmx import htmx_response

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def list_lots(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
):
    """List all lots with filters."""
    filters = build_lot_filter_from_request(request)
    pagination = PaginationParams(page=page, per_page=50)

    lots, total = lot_service.get_all_lots(db, filters, pagination)

    summary = lot_service.get_pl_summary(db, filters.account_id)
    symbols = lot_service.get_unique_symbols(db)
    accounts = account_service.get_all_accounts(db)
    total_pages = (total + 49) // 50

    context = {
        "lots": lots,
        "summary": summary,
        "symbols": symbols,
        "accounts": accounts,
        "filters": filters,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    }

    return htmx_response(
        templates=templates,
        request=request,
        full_template="lots.html",
        partial_template="partials/lot_list.html",
        context=context,
    )


@router.get("/{lot_id}", response_class=HTMLResponse)
def lot_detail(
    request: Request,
    lot_id: int,
    db: Session = Depends(get_db),
):
    """Show detailed view of a lot with all legs."""
    lot = lot_service.get_lot_by_id(db, lot_id)
    if not lot:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Lot not found")

    context = {
        "lot": lot,
    }

    return htmx_response(
        templates=templates,
        request=request,
        full_template="lot_detail.html",
        partial_template="partials/lot_detail_content.html",
        context=context,
    )


@router.post("/auto-match", response_class=HTMLResponse)
def run_auto_match(
    request: Request,
    db: Session = Depends(get_db),
    account_id: int | None = Form(None),
):
    """Run FIFO auto-matching on all unlinked transactions."""
    result = lot_service.match_all(db, account_id)

    filters = LotFilter(account_id=account_id)
    lots, total = lot_service.get_all_lots(db, filters)
    summary = lot_service.get_pl_summary(db, account_id)
    symbols = lot_service.get_unique_symbols(db)
    accounts = account_service.get_all_accounts(db)

    context = {
        "request": request,
        "lots": lots,
        "summary": summary,
        "symbols": symbols,
        "accounts": accounts,
        "filters": filters,
        "page": 1,
        "total_pages": (total + 49) // 50,
        "total": total,
        "match_result": result,
    }

    return templates.TemplateResponse("partials/lot_list.html", context)


@router.post("/rematch", response_class=HTMLResponse)
def run_full_rematch(
    request: Request,
    db: Session = Depends(get_db),
    account_id: int | None = Form(None),
):
    """Delete all lots and rebuild from scratch."""
    result = lot_service.rematch_all(db, account_id)

    filters = LotFilter(account_id=account_id)
    lots, total = lot_service.get_all_lots(db, filters)
    summary = lot_service.get_pl_summary(db, account_id)
    symbols = lot_service.get_unique_symbols(db)
    accounts = account_service.get_all_accounts(db)

    context = {
        "request": request,
        "lots": lots,
        "summary": summary,
        "symbols": symbols,
        "accounts": accounts,
        "filters": filters,
        "page": 1,
        "total_pages": (total + 49) // 50,
        "total": total,
        "match_result": result,
    }

    return templates.TemplateResponse("partials/lot_list.html", context)


@router.delete("/{lot_id}", response_class=HTMLResponse)
def delete_lot_route(
    lot_id: int,
    db: Session = Depends(get_db),
):
    """Delete a lot (unlink transactions)."""
    lot_service.delete_lot(db, lot_id)
    # Return empty response for HTMX to remove the row
    return HTMLResponse(content="", status_code=200)


@router.get("/transaction/{transaction_id}", response_class=HTMLResponse)
def get_transaction_lots(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """Get lots for a specific transaction (for embedding in detail page)."""
    lots = lot_service.get_lots_for_transaction(db, transaction_id)

    context = {
        "request": request,
        "lots": lots,
        "transaction_id": transaction_id,
    }

    return templates.TemplateResponse("partials/transaction_lots.html", context)
