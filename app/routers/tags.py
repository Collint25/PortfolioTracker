from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import tag_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def list_tags(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """List all tags."""
    tags = tag_service.get_all_tags(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/tag_list.html",
        context={"tags": tags},
    )


@router.post("/", response_class=HTMLResponse)
def create_tag(
    request: Request,
    name: str = Form(...),
    color: str = Form("neutral"),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Create a new tag."""
    existing = tag_service.get_tag_by_name(db, name)
    if existing:
        tags = tag_service.get_all_tags(db)
        return templates.TemplateResponse(
            request=request,
            name="partials/tag_list.html",
            context={"tags": tags, "error": f"Tag '{name}' already exists"},
        )
    tag_service.create_tag(db, name, color)
    tags = tag_service.get_all_tags(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/tag_list.html",
        context={"tags": tags},
    )


@router.delete("/{tag_id}", response_class=HTMLResponse)
def delete_tag(
    request: Request,
    tag_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Delete a tag."""
    tag_service.delete_tag(db, tag_id)
    tags = tag_service.get_all_tags(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/tag_list.html",
        context={"tags": tags},
    )


@router.post("/transaction/{transaction_id}/add/{tag_id}", response_class=HTMLResponse)
def add_tag_to_transaction(
    request: Request,
    transaction_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Add a tag to a transaction."""
    tag_service.add_tag_to_transaction(db, transaction_id, tag_id)
    transaction_tags = tag_service.get_transaction_tags(db, transaction_id)
    all_tags = tag_service.get_all_tags(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/transaction_tags.html",
        context={
            "transaction_id": transaction_id,
            "tags": transaction_tags,
            "all_tags": all_tags,
        },
    )


@router.delete(
    "/transaction/{transaction_id}/remove/{tag_id}", response_class=HTMLResponse
)
def remove_tag_from_transaction(
    request: Request,
    transaction_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Remove a tag from a transaction."""
    tag_service.remove_tag_from_transaction(db, transaction_id, tag_id)
    transaction_tags = tag_service.get_transaction_tags(db, transaction_id)
    all_tags = tag_service.get_all_tags(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/transaction_tags.html",
        context={
            "transaction_id": transaction_id,
            "tags": transaction_tags,
            "all_tags": all_tags,
        },
    )


@router.get("/transaction/{transaction_id}", response_class=HTMLResponse)
def get_transaction_tags(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Get tags for a transaction."""
    transaction_tags = tag_service.get_transaction_tags(db, transaction_id)
    all_tags = tag_service.get_all_tags(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/transaction_tags.html",
        context={
            "transaction_id": transaction_id,
            "tags": transaction_tags,
            "all_tags": all_tags,
        },
    )
