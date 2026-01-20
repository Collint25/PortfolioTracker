"""Router for analytics dashboard."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import account_service
from app.services.metrics_service import get_metrics
from app.utils.htmx import htmx_response
from app.utils.query_params import parse_date_param, parse_int_param

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def analytics_page(
    request: Request,
    db: Session = Depends(get_db),
    account_id: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
):
    """Analytics dashboard with P/L metrics and charts."""
    # Parse form values (empty strings become None)
    parsed_account_id = parse_int_param(account_id)
    parsed_start = parse_date_param(start_date)
    parsed_end = parse_date_param(end_date)

    # Convert single account_id to list for metrics service
    account_ids = [parsed_account_id] if parsed_account_id else None

    metrics = get_metrics(
        db,
        account_ids=account_ids,
        start_date=parsed_start,
        end_date=parsed_end,
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
            "account_id": parsed_account_id,
            "start_date": parsed_start.isoformat() if parsed_start else None,
            "end_date": parsed_end.isoformat() if parsed_end else None,
        },
    }

    return htmx_response(
        templates=templates,
        request=request,
        full_template="analytics.html",
        partial_template="partials/analytics_content.html",
        context=context,
    )
