"""Router for analytics dashboard."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import account_service
from app.services.filters import build_analytics_filter_from_request
from app.services.metrics_service import get_metrics
from app.utils.htmx import htmx_response

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def analytics_page(
    request: Request,
    db: Session = Depends(get_db),
):
    """Analytics dashboard with P/L metrics and charts."""
    filters = build_analytics_filter_from_request(request)

    # Convert single account_id to list for metrics service
    account_ids = [filters.account_id] if filters.account_id else None

    metrics = get_metrics(
        db,
        account_ids=account_ids,
        start_date=filters.start_date,
        end_date=filters.end_date,
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
        "filters": filters,
    }

    return htmx_response(
        templates=templates,
        request=request,
        full_template="analytics.html",
        partial_template="partials/analytics_content.html",
        context=context,
    )
