from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account
from app.services import tag_service, transaction_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def list_transactions(
    request: Request,
    db: Session = Depends(get_db),
    account_id: str | None = Query(None),
    symbol: str | None = Query(None),
    type: str | None = Query(None),
    tag_id: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    search: str | None = Query(None),
    is_option: str | None = Query(None),
    option_type: str | None = Query(None),
    option_action: str | None = Query(None),
    sort_by: str = "trade_date",
    sort_dir: str = "desc",
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    """List transactions with filtering, sorting, and pagination."""
    per_page = 50

    # Convert empty strings to None and parse types
    account_id_int = int(account_id) if account_id else None
    tag_id_int = int(tag_id) if tag_id else None
    symbol_val = symbol if symbol else None
    type_val = type if type else None
    search_val = search if search else None
    option_type_val = option_type if option_type else None
    option_action_val = option_action if option_action else None
    # Parse is_option: "true"/"false" -> True/False, empty -> None
    is_option_val = None
    if is_option == "true":
        is_option_val = True
    elif is_option == "false":
        is_option_val = False

    # Parse dates
    from datetime import datetime
    start_date_val = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    end_date_val = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

    transactions, total = transaction_service.get_transactions(
        db,
        account_id=account_id_int,
        symbol=symbol_val,
        transaction_type=type_val,
        tag_id=tag_id_int,
        start_date=start_date_val,
        end_date=end_date_val,
        search=search_val,
        is_option=is_option_val,
        option_type=option_type_val,
        option_action=option_action_val,
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
    tags = tag_service.get_all_tags(db)
    option_types = transaction_service.get_unique_option_types(db)
    option_actions = transaction_service.get_unique_option_actions(db)

    context = {
        "transactions": transactions,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "accounts": accounts,
        "symbols": symbols,
        "types": types,
        "tags": tags,
        "option_types": option_types,
        "option_actions": option_actions,
        # Current filter values
        "current_account_id": account_id_int,
        "current_symbol": symbol_val,
        "current_type": type_val,
        "current_tag_id": tag_id_int,
        "current_start_date": start_date_val,
        "current_end_date": end_date_val,
        "current_search": search_val,
        "current_is_option": is_option,
        "current_option_type": option_type_val,
        "current_option_action": option_action_val,
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
