from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import comment_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/transaction/{transaction_id}", response_class=HTMLResponse)
def get_comments(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Get all comments for a transaction."""
    comments = comment_service.get_comments_for_transaction(db, transaction_id)
    return templates.TemplateResponse(
        request=request,
        name="partials/comment_list.html",
        context={"transaction_id": transaction_id, "comments": comments},
    )


@router.post("/transaction/{transaction_id}", response_class=HTMLResponse)
def create_comment(
    request: Request,
    transaction_id: int,
    text: str = Form(...),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Create a new comment on a transaction."""
    comment_service.create_comment(db, transaction_id, text)
    comments = comment_service.get_comments_for_transaction(db, transaction_id)
    return templates.TemplateResponse(
        request=request,
        name="partials/comment_list.html",
        context={"transaction_id": transaction_id, "comments": comments},
    )


@router.delete("/{comment_id}", response_class=HTMLResponse)
def delete_comment(
    request: Request,
    comment_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Delete a comment."""
    comment = comment_service.get_comment_by_id(db, comment_id)
    if not comment:
        return HTMLResponse(content="", status_code=200)
    transaction_id = comment.transaction_id
    comment_service.delete_comment(db, comment_id)
    comments = comment_service.get_comments_for_transaction(db, transaction_id)
    return templates.TemplateResponse(
        request=request,
        name="partials/comment_list.html",
        context={"transaction_id": transaction_id, "comments": comments},
    )
