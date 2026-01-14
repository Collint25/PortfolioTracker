from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account
from app.services import transaction_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def list_transactions(
    request: Request,
    db: Session = Depends(get_db),
    account_id: int | None = None,
    symbol: str | None = None,
    type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    sort_by: str = "trade_date",
    sort_dir: str = "desc",
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    """List transactions with filtering, sorting, and pagination."""
    per_page = 50

    transactions, total = transaction_service.get_transactions(
        db,
        account_id=account_id,
        symbol=symbol,
        transaction_type=type,
        start_date=start_date,
        end_date=end_date,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        per_page=per_page,
    )

    # Calculate pagination info
    total_pages = (total + per_page - 1) // per_page

    # Get filter options
    accounts = db.query(Account).order_by(Account.name).all()
    symbols = transaction_service.get_unique_symbols(db)
    types = transaction_service.get_unique_types(db)

    context = {
        "transactions": transactions,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "accounts": accounts,
        "symbols": symbols,
        "types": types,
        # Current filter values
        "current_account_id": account_id,
        "current_symbol": symbol,
        "current_type": type,
        "current_start_date": start_date,
        "current_end_date": end_date,
        "current_search": search,
        "current_sort_by": sort_by,
        "current_sort_dir": sort_dir,
        "title": "Transactions",
    }

    # Return partial for HTMX requests
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="partials/transaction_table.html",
            context=context,
        )

    return templates.TemplateResponse(
        request=request,
        name="transactions.html",
        context=context,
    )


@router.get("/{transaction_id}", response_class=HTMLResponse)
def transaction_detail(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Show transaction detail page."""
    transaction = transaction_service.get_transaction_by_id(db, transaction_id)

    if not transaction:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"title": "Not Found"},
            status_code=404,
        )

    # Get related transactions (same external_reference_id for multi-leg)
    related = []
    if transaction.external_reference_id:
        from app.models import Transaction
        related = (
            db.query(Transaction)
            .filter(
                Transaction.external_reference_id == transaction.external_reference_id,
                Transaction.id != transaction.id,
            )
            .all()
        )

    return templates.TemplateResponse(
        request=request,
        name="transaction_detail.html",
        context={
            "transaction": transaction,
            "related": related,
            "title": f"Transaction - {transaction.symbol or 'N/A'}",
        },
    )
