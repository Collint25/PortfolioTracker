from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import saved_filter_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/{page}", response_class=HTMLResponse)
def list_saved_filters(
    request: Request, page: str, db: Session = Depends(get_db)
) -> HTMLResponse:
    """List saved filters for a page."""
    filters = saved_filter_service.get_filters_for_page(db, page)
    return templates.TemplateResponse(
        request=request,
        name="partials/saved_filter_list.html",
        context={"saved_filters": filters, "filter_page": page},
    )


@router.post("/{page}", response_class=HTMLResponse)
def create_saved_filter(
    request: Request,
    page: str,
    name: str = Form(...),
    query_string: str = Form(...),
    is_favorite: bool = Form(False),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Create a new saved filter. query_string is the URL params (without ?)."""
    saved_filter_service.create_filter(db, name, page, query_string, is_favorite)
    filters = saved_filter_service.get_filters_for_page(db, page)
    return templates.TemplateResponse(
        request=request,
        name="partials/saved_filter_list.html",
        context={"saved_filters": filters, "filter_page": page},
    )


@router.post("/{filter_id}/favorite", response_class=HTMLResponse)
def toggle_favorite(
    request: Request, filter_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Toggle favorite status for a filter."""
    saved_filter = saved_filter_service.get_filter_by_id(db, filter_id)
    if not saved_filter:
        return HTMLResponse(content="", status_code=404)

    page = saved_filter.page
    if saved_filter.is_favorite:
        saved_filter_service.clear_favorite(db, filter_id)
    else:
        saved_filter_service.set_favorite(db, filter_id)

    filters = saved_filter_service.get_filters_for_page(db, page)
    return templates.TemplateResponse(
        request=request,
        name="partials/saved_filter_list.html",
        context={"saved_filters": filters, "filter_page": page},
    )


@router.delete("/{filter_id}", response_class=HTMLResponse)
def delete_saved_filter(
    request: Request, filter_id: int, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Delete a saved filter."""
    saved_filter = saved_filter_service.get_filter_by_id(db, filter_id)
    if not saved_filter:
        return HTMLResponse(content="", status_code=404)

    page = saved_filter.page
    saved_filter_service.delete_filter(db, filter_id)
    filters = saved_filter_service.get_filters_for_page(db, page)
    return templates.TemplateResponse(
        request=request,
        name="partials/saved_filter_list.html",
        context={"saved_filters": filters, "filter_page": page},
    )
