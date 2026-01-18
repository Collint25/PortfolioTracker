from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.database import get_db
from app.services import account_service, market_data_service, position_service
from app.utils.htmx import htmx_response

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def list_accounts(request: Request, db: Session = Depends(get_db)) -> Response:
    """List all accounts with totals."""
    accounts_with_totals = account_service.get_all_accounts_with_totals(db)

    context = {"accounts": accounts_with_totals, "title": "Accounts"}

    return htmx_response(
        templates=templates,
        request=request,
        full_template="accounts.html",
        partial_template="partials/account_list.html",
        context=context,
    )


@router.get("/{account_id}/positions", response_class=HTMLResponse)
def account_positions(
    request: Request, account_id: int, db: Session = Depends(get_db)
) -> Response:
    """View positions for an account."""
    account = account_service.get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    positions, totals = position_service.get_account_positions_summary(db, account_id)

    context = {
        "account": account,
        "positions": positions,
        "totals": totals,
        "title": f"Positions - {account.name}",
    }

    return htmx_response(
        templates=templates,
        request=request,
        full_template="account_positions.html",
        partial_template="partials/position_list.html",
        context=context,
    )


@router.post("/{account_id}/positions/refresh", response_class=HTMLResponse)
def refresh_prices(
    request: Request, account_id: int, db: Session = Depends(get_db)
) -> Response:
    """Refresh current prices for account positions via Finnhub."""
    account = account_service.get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Refresh prices from Finnhub
    result = market_data_service.refresh_position_prices(db, account_id)

    # Re-fetch positions with updated prices
    positions, totals = position_service.get_account_positions_summary(db, account_id)

    return templates.TemplateResponse(
        request=request,
        name="partials/positions_with_status.html",
        context={
            "positions": positions,
            "totals": totals,
            "refresh_result": result,
        },
    )
