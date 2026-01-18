from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import account_service, position_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Dashboard home page with account cards."""
    accounts_with_totals = account_service.get_all_accounts_with_totals(db)

    # Calculate portfolio-wide totals
    portfolio_totals = {
        "market_value": Decimal("0"),
        "daily_change": Decimal("0"),
        "daily_change_percent": None,
    }
    total_previous_value = Decimal("0")
    has_daily_data = False

    for item in accounts_with_totals:
        totals = item["totals"]
        portfolio_totals["market_value"] += totals["market_value"]
        if totals["daily_change"] is not None:
            portfolio_totals["daily_change"] += totals["daily_change"]
            has_daily_data = True
            # Approximate previous value for portfolio-level percent calculation
            if (
                totals["daily_change_percent"] is not None
                and totals["market_value"] > 0
            ):
                prev = totals["market_value"] - totals["daily_change"]
                total_previous_value += prev

    if has_daily_data and total_previous_value > 0:
        daily_change = portfolio_totals["daily_change"]
        if daily_change is not None:
            portfolio_totals["daily_change_percent"] = (
                daily_change / total_previous_value * 100
            )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "Portfolio Tracker",
            "accounts": accounts_with_totals,
            "portfolio_totals": portfolio_totals,
        },
    )


@router.get("/accounts/{account_id}/positions-inline", response_class=HTMLResponse)
def account_positions_inline(
    request: Request, account_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Return inline positions list for expandable account cards."""
    positions, totals = position_service.get_account_positions_summary(db, account_id)
    return templates.TemplateResponse(
        request=request,
        name="partials/position_list_compact.html",
        context={"positions": positions, "totals": totals},
    )


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request) -> HTMLResponse:
    """Settings page for tag management."""
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"title": "Settings - Portfolio Tracker"},
    )
