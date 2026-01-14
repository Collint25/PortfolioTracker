from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import account_service

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
