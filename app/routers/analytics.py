"""Router for analytics dashboard."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import account_service
from app.services.metrics_service import get_metrics
from app.utils.htmx import htmx_response

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def analytics_page(
    request: Request,
    db: Session = Depends(get_db),
    account_id: int | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    """Analytics dashboard with P/L metrics and charts."""
    # Convert single account_id to list for metrics service
    account_ids = [account_id] if account_id else None

    metrics = get_metrics(
        db,
        account_ids=account_ids,
        start_date=start_date,
        end_date=end_date,
    )

    accounts = account_service.get_all_accounts(db)

    # Format time series data for Chart.js
    chart_labels = [dp.date.isoformat() for dp in metrics.pl_over_time]
    chart_data = [float(dp.cumulative_pl) for dp in metrics.pl_over_time]

    context = {
        "metrics": metrics,
        "accounts": accounts,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "filters": {
            "account_id": account_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    }

    return htmx_response(
        templates=templates,
        request=request,
        full_template="analytics.html",
        partial_template="partials/analytics_content.html",
        context=context,
    )
