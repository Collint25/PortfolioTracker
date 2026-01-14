from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def is_htmx_request(request: Request) -> bool:
    """Check if request came from HTMX."""
    return request.headers.get("HX-Request") == "true"


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Dashboard home page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "Portfolio Tracker"},
    )


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request) -> HTMLResponse:
    """Settings page for tag management."""
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"title": "Settings - Portfolio Tracker"},
    )
