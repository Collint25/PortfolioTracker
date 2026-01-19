from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.database import get_db
from app.services import (
    account_service,
    saved_filter_service,
    tag_service,
    transaction_service,
)
from app.services.filters import (
    PaginationParams,
    get_effective_transaction_filter,
)
from app.utils.htmx import htmx_response, is_htmx_request

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def build_filter_query_string(
    search: str | None,
    account_id: int | None,
    symbol: str | None,
    type: str | None,
    tag_id: int | None,
    start_date: str | None,
    end_date: str | None,
    is_option: str | None,
    option_type: str | None,
    option_action: str | None,
    sort_by: str,
    sort_dir: str,
) -> str:
    """Build a URL query string from filter parameters."""
    params: dict[str, str] = {}
    if search:
        params["search"] = search
    if account_id:
        params["account_id"] = str(account_id)
    if symbol:
        params["symbol"] = symbol
    if type:
        params["type"] = type
    if tag_id:
        params["tag_id"] = str(tag_id)
    if start_date:
        params["start_date"] = str(start_date)
    if end_date:
        params["end_date"] = str(end_date)
    if is_option:
        params["is_option"] = is_option
    if option_type:
        params["option_type"] = option_type
    if option_action:
        params["option_action"] = option_action
    if sort_by and sort_by != "trade_date":
        params["sort_by"] = sort_by
    if sort_dir and sort_dir != "desc":
        params["sort_dir"] = sort_dir
    return urlencode(params)


@router.get("/", response_class=HTMLResponse)
def list_transactions(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    clear_favorite: bool = Query(False),
) -> Response:
    """List transactions with filtering, sorting, and pagination."""
    per_page = 50

    # Handle clearing the favorite filter
    if clear_favorite:
        favorite = saved_filter_service.get_favorite_filter(db, "transactions")
        if favorite:
            saved_filter_service.clear_favorite(db, favorite.id)
        # Use default filters, no favorite applied
        from app.services.filters import TransactionFilter

        filters = TransactionFilter()
        applied_favorite = None
    else:
        # Get effective filter (from request params or favorite)
        filters, applied_favorite = get_effective_transaction_filter(request, db)

    # Build pagination object
    pagination = PaginationParams(page=page, per_page=per_page)

    # Get transactions
    transactions, total = transaction_service.get_transactions(db, filters, pagination)

    total_pages = (total + per_page - 1) // per_page

    # Get filter options
    accounts = account_service.get_all_accounts(db)
    symbols = transaction_service.get_unique_symbols(db)
    types = transaction_service.get_unique_types(db)
    tags = tag_service.get_all_tags(db)
    option_types = transaction_service.get_unique_option_types(db)
    option_actions = transaction_service.get_unique_option_actions(db)

    # Build query string for saved filters and table links
    filter_query_string = build_filter_query_string(
        search=filters.search,
        account_id=filters.account_id,
        symbol=filters.symbol,
        type=filters.transaction_type,
        tag_id=filters.tag_id,
        start_date=str(filters.start_date) if filters.start_date else None,
        end_date=str(filters.end_date) if filters.end_date else None,
        is_option=(
            str(filters.is_option).lower() if filters.is_option is not None else None
        ),
        option_type=filters.option_type,
        option_action=filters.option_action,
        sort_by=filters.sort_by,
        sort_dir=filters.sort_dir,
    )

    # Get saved filters for this page
    saved_filters = saved_filter_service.get_filters_for_page(db, "transactions")

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
        "saved_filters": saved_filters,
        "filter_query_string": filter_query_string,
        "applied_favorite": applied_favorite,
        # Current filter values for form
        "current_account_id": filters.account_id,
        "current_symbol": filters.symbol,
        "current_type": filters.transaction_type,
        "current_tag_id": filters.tag_id,
        "current_start_date": filters.start_date,
        "current_end_date": filters.end_date,
        "current_search": filters.search,
        "current_is_option": (
            str(filters.is_option).lower() if filters.is_option is not None else None
        ),
        "current_option_type": filters.option_type,
        "current_option_action": filters.option_action,
        "current_sort_by": filters.sort_by,
        "current_sort_dir": filters.sort_dir,
        "title": "Transactions",
        "is_htmx": is_htmx_request(request),
    }

    # Use helper for HTMX response
    return htmx_response(
        templates=templates,
        request=request,
        full_template="transactions.html",
        partial_template="partials/transaction_table.html",
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

    related = transaction_service.get_related_transactions(db, transaction)

    return templates.TemplateResponse(
        request=request,
        name="transaction_detail.html",
        context={
            "transaction": transaction,
            "related": related,
            "title": f"Transaction - {transaction.symbol or 'N/A'}",
        },
    )
