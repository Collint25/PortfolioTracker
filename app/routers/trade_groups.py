from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import trade_group_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def list_trade_groups(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """List all trade groups."""
    groups = trade_group_service.get_all_trade_groups(db)
    # Calculate P/L for each group
    groups_with_pl = [
        {
            "group": g,
            "pl": trade_group_service.calculate_group_pl(db, g.id),
            "transaction_count": len(g.transactions),
        }
        for g in groups
    ]
    context = {
        "groups": groups_with_pl,
        "strategy_types": trade_group_service.STRATEGY_TYPES,
        "title": "Trade Groups",
    }

    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="partials/trade_group_list.html",
            context=context,
        )

    return templates.TemplateResponse(
        request=request,
        name="trade_groups.html",
        context=context,
    )


@router.get("/suggestions", response_class=HTMLResponse)
def get_group_suggestions(
    request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Get suggested trade groups based on external_reference_id."""
    candidates = trade_group_service.get_ungrouped_multileg_candidates(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/trade_group_suggestions.html",
        context={
            "candidates": candidates,
            "strategy_types": trade_group_service.STRATEGY_TYPES,
        },
    )


@router.post("/", response_class=HTMLResponse)
def create_trade_group(
    request: Request,
    name: str = Form(...),
    strategy_type: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Create a new trade group."""
    trade_group_service.create_trade_group(
        db,
        name=name,
        strategy_type=strategy_type if strategy_type else None,
        description=description if description else None,
    )
    groups = trade_group_service.get_all_trade_groups(db)
    groups_with_pl = [
        {
            "group": g,
            "pl": trade_group_service.calculate_group_pl(db, g.id),
            "transaction_count": len(g.transactions),
        }
        for g in groups
    ]
    return templates.TemplateResponse(
        request=request,
        name="partials/trade_group_list.html",
        context={
            "groups": groups_with_pl,
            "strategy_types": trade_group_service.STRATEGY_TYPES,
        },
    )


@router.post("/from-reference/{external_reference_id}", response_class=HTMLResponse)
def create_from_external_reference(
    request: Request,
    external_reference_id: str,
    name: str = Form(""),
    strategy_type: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Create a trade group from transactions with the same external_reference_id."""
    trade_group_service.create_group_from_external_reference(
        db,
        external_reference_id=external_reference_id,
        name=name if name else None,
        strategy_type=strategy_type if strategy_type else None,
    )
    candidates = trade_group_service.get_ungrouped_multileg_candidates(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/trade_group_suggestions.html",
        context={
            "candidates": candidates,
            "strategy_types": trade_group_service.STRATEGY_TYPES,
        },
    )


@router.get("/{group_id}", response_class=HTMLResponse)
def trade_group_detail(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Show trade group detail page."""
    group = trade_group_service.get_trade_group_by_id(db, group_id)
    if not group:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"title": "Not Found"},
            status_code=404,
        )

    transactions = trade_group_service.get_group_transactions(db, group_id)
    pl = trade_group_service.calculate_group_pl(db, group_id)

    return templates.TemplateResponse(
        request=request,
        name="trade_group_detail.html",
        context={
            "group": group,
            "transactions": transactions,
            "pl": pl,
            "strategy_types": trade_group_service.STRATEGY_TYPES,
            "title": f"Trade Group - {group.name}",
        },
    )


@router.put("/{group_id}", response_class=HTMLResponse)
def update_trade_group(
    request: Request,
    group_id: int,
    name: str = Form(...),
    strategy_type: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Update a trade group."""
    group = trade_group_service.update_trade_group(
        db,
        group_id,
        name=name,
        strategy_type=strategy_type,
        description=description,
    )
    if not group:
        return HTMLResponse(content="Not found", status_code=404)

    transactions = trade_group_service.get_group_transactions(db, group_id)
    pl = trade_group_service.calculate_group_pl(db, group_id)

    return templates.TemplateResponse(
        request=request,
        name="partials/trade_group_detail_content.html",
        context={
            "group": group,
            "transactions": transactions,
            "pl": pl,
            "strategy_types": trade_group_service.STRATEGY_TYPES,
        },
    )


@router.delete("/{group_id}", response_class=HTMLResponse)
def delete_trade_group(
    request: Request,
    group_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Delete a trade group."""
    trade_group_service.delete_trade_group(db, group_id)
    # Return empty response with HX-Redirect header
    response = HTMLResponse(content="")
    response.headers["HX-Redirect"] = "/trade-groups"
    return response


@router.post("/{group_id}/add/{transaction_id}", response_class=HTMLResponse)
def add_transaction_to_group(
    request: Request,
    group_id: int,
    transaction_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Add a transaction to a trade group."""
    trade_group_service.add_transaction_to_group(db, group_id, transaction_id)
    group = trade_group_service.get_trade_group_by_id(db, group_id)
    transactions = trade_group_service.get_group_transactions(db, group_id)
    pl = trade_group_service.calculate_group_pl(db, group_id)
    return templates.TemplateResponse(
        request=request,
        name="partials/trade_group_transactions.html",
        context={
            "group": group,
            "transactions": transactions,
            "pl": pl,
        },
    )


@router.delete("/{group_id}/remove/{transaction_id}", response_class=HTMLResponse)
def remove_transaction_from_group(
    request: Request,
    group_id: int,
    transaction_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Remove a transaction from a trade group."""
    trade_group_service.remove_transaction_from_group(db, group_id, transaction_id)
    group = trade_group_service.get_trade_group_by_id(db, group_id)
    transactions = trade_group_service.get_group_transactions(db, group_id)
    pl = trade_group_service.calculate_group_pl(db, group_id)
    return templates.TemplateResponse(
        request=request,
        name="partials/trade_group_transactions.html",
        context={
            "group": group,
            "transactions": transactions,
            "pl": pl,
        },
    )


@router.get("/transaction/{transaction_id}", response_class=HTMLResponse)
def get_transaction_groups(
    request: Request,
    transaction_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Get trade groups for a transaction."""
    groups = trade_group_service.get_transaction_groups(db, transaction_id)
    all_groups = trade_group_service.get_all_trade_groups(db)
    return templates.TemplateResponse(
        request=request,
        name="partials/transaction_trade_groups.html",
        context={
            "transaction_id": transaction_id,
            "groups": groups,
            "all_groups": all_groups,
        },
    )
