from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import account_service, market_data_service, position_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def list_accounts(
    request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    """List all accounts."""
    accounts = account_service.get_all_accounts(db)

    # Return partial for HTMX requests
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="partials/account_list.html",
            context={"accounts": accounts},
        )

    return templates.TemplateResponse(
        request=request,
        name="accounts.html",
        context={"accounts": accounts, "title": "Accounts"},
    )


@router.get("/{account_id}/positions", response_class=HTMLResponse)
def account_positions(
    request: Request, account_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    """View positions for an account."""
    account = account_service.get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    positions, totals = position_service.get_account_positions_summary(db, account_id)

    # Return partial for HTMX requests
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="partials/position_list.html",
            context={"positions": positions, "totals": totals},
        )

    return templates.TemplateResponse(
        request=request,
        name="account_positions.html",
        context={
            "account": account,
            "positions": positions,
            "totals": totals,
            "title": f"Positions - {account.name}",
        },
    )


@router.post("/{account_id}/positions/refresh", response_class=HTMLResponse)
def refresh_prices(
    request: Request, account_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
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
