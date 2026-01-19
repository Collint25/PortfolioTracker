# Favorite Filter Auto-Apply

## Overview

Wire up the existing "favorite filter" feature to actually apply on page load. Currently the UI says "Set as favorite (auto-apply on page load)" but the routes never check for a favorite.

## Scope

- **Transactions view only** (lots view doesn't have saved filters integrated)
- **Silent apply** — no URL redirect, filters applied internally
- **Favorite always wins** — when URL has no filter params and a favorite exists, apply it

## Design

### Detection Logic

Check if user provided any filter params:

```python
FILTER_PARAMS = [
    "account_id", "symbol", "type", "tag_id",
    "start_date", "end_date", "search",
    "is_option", "option_type", "option_action"
]

def has_any_filter_params(request: Request) -> bool:
    return any(request.query_params.get(p) for p in FILTER_PARAMS)
```

Note: `sort_by` and `sort_dir` are NOT filter params — sorting alone won't prevent favorite from applying.

### Helper Function

New function in `app/services/filters.py`:

```python
def get_effective_transaction_filter(
    request: Request,
    db: Session,
) -> tuple[TransactionFilter, SavedFilter | None]:
    """
    Build TransactionFilter from request params,
    or from favorite if no params provided.

    Returns (filter, applied_favorite) tuple.
    """
    if has_any_filter_params(request):
        return build_filter_from_request(request), None

    favorite = get_favorite_filter(db, "transactions")
    if favorite:
        return build_filter_from_query_string(favorite.filter_json), favorite

    return TransactionFilter(), None
```

Supporting functions:
- `build_filter_from_query_string(qs: str) -> TransactionFilter` — parse query string into filter
- `build_filter_from_request(request: Request) -> TransactionFilter` — extract params from request

### Route Handler

Simplified `GET /transactions`:

```python
@router.get("/transactions")
async def list_transactions(request: Request, db: Session):
    filter, applied_favorite = get_effective_transaction_filter(request, db)

    transactions, total = get_transactions(db, filter, pagination)

    return templates.TemplateResponse(..., {
        "transactions": transactions,
        "applied_favorite": applied_favorite,
        **filter_to_template_context(filter),
    })
```

### UI Indication

Badge near filters when favorite is active:

```html
{% if applied_favorite %}
<div class="badge badge-info gap-1">
    <span>Using: {{ applied_favorite.name }}</span>
    <a href="/transactions" class="text-xs">(clear)</a>
</div>
{% endif %}
```

## Files to Modify

| File | Changes |
|------|---------|
| `app/services/filters.py` | Add `has_any_filter_params()`, `build_filter_from_query_string()`, `build_filter_from_request()`, `get_effective_transaction_filter()` |
| `app/routers/transactions.py` | Replace manual param handling with helper, pass `applied_favorite` to template |
| `app/templates/transactions.html` | Add badge showing active favorite with clear link |

## What's NOT Changing

- `SavedFilter` model (already has `is_favorite`)
- `saved_filter_service.py` (already has `get_favorite_filter()`)
- Saved filter creation/toggle UI (already works)

## Estimated Scope

- ~50 lines new code in `filters.py`
- ~20 lines removed / simplified in `transactions.py`
- ~6 lines added to template
