"""Router for linked trades (open/close matching)."""

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import linked_trade_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def list_linked_trades(
    request: Request,
    db: Session = Depends(get_db),
    account_id: int | None = Query(None),
    underlying_symbol: str | None = Query(None),
    is_closed: str | None = Query(None),
    page: int = Query(1, ge=1),
):
    """List all linked trades with filters."""
    # Convert is_closed string to bool
    closed_filter = None
    if is_closed == "true":
        closed_filter = True
    elif is_closed == "false":
        closed_filter = False

    linked_trades, total = linked_trade_service.get_all_linked_trades(
        db,
        account_id=account_id,
        underlying_symbol=underlying_symbol,
        is_closed=closed_filter,
        page=page,
        per_page=50,
    )

    # Get summary stats
    summary = linked_trade_service.get_pl_summary(db, account_id)

    # Get unique symbols for filter dropdown
    from app.models import LinkedTrade
    symbols = db.query(LinkedTrade.underlying_symbol).distinct().order_by(LinkedTrade.underlying_symbol).all()
    symbols = [s[0] for s in symbols]

    # Get accounts for filter
    from app.models import Account
    accounts = db.query(Account).all()

    total_pages = (total + 49) // 50

    context = {
        "request": request,
        "linked_trades": linked_trades,
        "summary": summary,
        "symbols": symbols,
        "accounts": accounts,
        "filters": {
            "account_id": account_id,
            "underlying_symbol": underlying_symbol,
            "is_closed": is_closed,
        },
        "page": page,
        "total_pages": total_pages,
        "total": total,
    }

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("partials/linked_trade_list.html", context)
    return templates.TemplateResponse("linked_trades.html", context)


@router.get("/{linked_trade_id}", response_class=HTMLResponse)
def linked_trade_detail(
    request: Request,
    linked_trade_id: int,
    db: Session = Depends(get_db),
):
    """Show detailed view of a linked trade with all legs."""
    linked_trade = linked_trade_service.get_linked_trade_by_id(db, linked_trade_id)
    if not linked_trade:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Linked trade not found")

    context = {
        "request": request,
        "linked_trade": linked_trade,
    }

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("partials/linked_trade_detail_content.html", context)
    return templates.TemplateResponse("linked_trade_detail.html", context)


@router.post("/auto-match", response_class=HTMLResponse)
def run_auto_match(
    request: Request,
    db: Session = Depends(get_db),
    account_id: int | None = Form(None),
):
    """Run FIFO auto-matching on all unlinked transactions."""
    result = linked_trade_service.auto_match_all(db, account_id)

    # Return updated list
    linked_trades, total = linked_trade_service.get_all_linked_trades(db, account_id=account_id)
    summary = linked_trade_service.get_pl_summary(db, account_id)

    from app.models import LinkedTrade, Account
    symbols = db.query(LinkedTrade.underlying_symbol).distinct().order_by(LinkedTrade.underlying_symbol).all()
    symbols = [s[0] for s in symbols]
    accounts = db.query(Account).all()

    context = {
        "request": request,
        "linked_trades": linked_trades,
        "summary": summary,
        "symbols": symbols,
        "accounts": accounts,
        "filters": {"account_id": account_id, "underlying_symbol": None, "is_closed": None},
        "page": 1,
        "total_pages": (total + 49) // 50,
        "total": total,
        "match_result": result,
    }

    return templates.TemplateResponse("partials/linked_trade_list.html", context)


@router.delete("/{linked_trade_id}", response_class=HTMLResponse)
def delete_linked_trade(
    request: Request,
    linked_trade_id: int,
    db: Session = Depends(get_db),
):
    """Delete a linked trade (unlink transactions)."""
    from app.models import LinkedTrade
    linked_trade = db.query(LinkedTrade).filter(LinkedTrade.id == linked_trade_id).first()
    if linked_trade:
        db.delete(linked_trade)
        db.commit()

    # Return empty response for HTMX to remove the row
    return HTMLResponse(content="", status_code=200)


@router.get("/transaction/{transaction_id}", response_class=HTMLResponse)
def get_transaction_links(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """Get linked trades for a specific transaction (for embedding in detail page)."""
    linked_trades = linked_trade_service.get_linked_trades_for_transaction(db, transaction_id)

    context = {
        "request": request,
        "linked_trades": linked_trades,
        "transaction_id": transaction_id,
    }

    return templates.TemplateResponse("partials/transaction_linked_trades.html", context)
