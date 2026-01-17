from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import (
    account_service,
    saved_filter_service,
    tag_service,
    transaction_service,
)
from app.utils.query_params import parse_bool_param, parse_date_param, parse_int_param

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

    # Parse query params using utilities
    account_id_int = parse_int_param(account_id)
    tag_id_int = parse_int_param(tag_id)
    symbol_val = symbol or None
    type_val = type or None
    search_val = search or None
    option_type_val = option_type or None
    option_action_val = option_action or None
    is_option_val = parse_bool_param(is_option)
    start_date_val = parse_date_param(start_date)
    end_date_val = parse_date_param(end_date)

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
        search=search_val,
        account_id=account_id_int,
        symbol=symbol_val,
        type=type_val,
        tag_id=tag_id_int,
        start_date=start_date,
        end_date=end_date,
        is_option=is_option,
        option_type=option_type_val,
        option_action=option_action_val,
        sort_by=sort_by,
        sort_dir=sort_dir,
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
