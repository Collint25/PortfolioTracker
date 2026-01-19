# Favorite Filter Auto-Apply Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire up the existing favorite filter feature to automatically apply on transactions page load when no filter params are present.

**Architecture:** Add helper functions in `filters.py` to detect filter params and build filters from saved query strings. Update the transactions router to use these helpers, falling back to favorite filter when no explicit params provided. Display a badge when favorite is active.

**Tech Stack:** FastAPI, SQLAlchemy, Jinja2, urllib.parse

---

## Task 1: Add `has_any_filter_params` function

**Files:**
- Modify: `app/services/filters.py` (add at end of file)
- Test: `tests/test_filters.py`

**Step 1: Write the failing test**

Add to `tests/test_filters.py`:

```python
from unittest.mock import MagicMock

from app.services.filters import has_any_filter_params


def test_has_any_filter_params_empty():
    """Test with no params returns False."""
    request = MagicMock()
    request.query_params = {}
    assert has_any_filter_params(request) is False


def test_has_any_filter_params_with_filter():
    """Test with filter param returns True."""
    request = MagicMock()
    request.query_params = {"symbol": "AAPL"}
    assert has_any_filter_params(request) is True


def test_has_any_filter_params_sort_only():
    """Test with only sort params returns False (sort is not a filter)."""
    request = MagicMock()
    request.query_params = {"sort_by": "symbol", "sort_dir": "asc"}
    assert has_any_filter_params(request) is False


def test_has_any_filter_params_page_only():
    """Test with only page param returns False."""
    request = MagicMock()
    request.query_params = {"page": "2"}
    assert has_any_filter_params(request) is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_filters.py::test_has_any_filter_params_empty -v`
Expected: FAIL with "cannot import name 'has_any_filter_params'"

**Step 3: Write minimal implementation**

Add to `app/services/filters.py`:

```python
from starlette.requests import Request

# Filter param names (excludes sort_by, sort_dir, page which are not filters)
TRANSACTION_FILTER_PARAMS = [
    "account_id",
    "symbol",
    "type",
    "tag_id",
    "start_date",
    "end_date",
    "search",
    "is_option",
    "option_type",
    "option_action",
]


def has_any_filter_params(request: Request) -> bool:
    """Check if request has any filter params (excludes sort/page)."""
    return any(request.query_params.get(p) for p in TRANSACTION_FILTER_PARAMS)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_filters.py::test_has_any_filter_params_empty tests/test_filters.py::test_has_any_filter_params_with_filter tests/test_filters.py::test_has_any_filter_params_sort_only tests/test_filters.py::test_has_any_filter_params_page_only -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add app/services/filters.py tests/test_filters.py
git commit -m "feat: add has_any_filter_params helper"
```

---

## Task 2: Add `build_filter_from_query_string` function

**Files:**
- Modify: `app/services/filters.py`
- Test: `tests/test_filters.py`

**Step 1: Write the failing test**

Add to `tests/test_filters.py`:

```python
from app.services.filters import build_filter_from_query_string


def test_build_filter_from_empty_query_string():
    """Test empty query string returns default filter."""
    result = build_filter_from_query_string("")
    assert result.account_id is None
    assert result.symbol is None
    assert result.sort_by == "trade_date"
    assert result.sort_dir == "desc"


def test_build_filter_from_query_string_basic():
    """Test parsing basic filter params."""
    result = build_filter_from_query_string("symbol=AAPL&account_id=1")
    assert result.symbol == "AAPL"
    assert result.account_id == 1


def test_build_filter_from_query_string_with_dates():
    """Test parsing date params."""
    result = build_filter_from_query_string("start_date=2024-01-01&end_date=2024-12-31")
    assert result.start_date == date(2024, 1, 1)
    assert result.end_date == date(2024, 12, 31)


def test_build_filter_from_query_string_with_bool():
    """Test parsing boolean params."""
    result = build_filter_from_query_string("is_option=true")
    assert result.is_option is True


def test_build_filter_from_query_string_with_sort():
    """Test parsing sort params."""
    result = build_filter_from_query_string("sort_by=symbol&sort_dir=asc")
    assert result.sort_by == "symbol"
    assert result.sort_dir == "asc"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_filters.py::test_build_filter_from_empty_query_string -v`
Expected: FAIL with "cannot import name 'build_filter_from_query_string'"

**Step 3: Write minimal implementation**

Add to `app/services/filters.py`:

```python
from urllib.parse import parse_qs

from app.utils.query_params import parse_bool_param, parse_date_param, parse_int_param


def build_filter_from_query_string(query_string: str) -> TransactionFilter:
    """Parse a URL query string into a TransactionFilter."""
    if not query_string:
        return TransactionFilter()

    # parse_qs returns lists, extract single values
    parsed = parse_qs(query_string)

    def get_single(key: str) -> str | None:
        values = parsed.get(key, [])
        return values[0] if values else None

    return TransactionFilter(
        account_id=parse_int_param(get_single("account_id")),
        symbol=get_single("symbol") or None,
        transaction_type=get_single("type") or None,
        tag_id=parse_int_param(get_single("tag_id")),
        start_date=parse_date_param(get_single("start_date")),
        end_date=parse_date_param(get_single("end_date")),
        search=get_single("search") or None,
        is_option=parse_bool_param(get_single("is_option")),
        option_type=get_single("option_type") or None,
        option_action=get_single("option_action") or None,
        sort_by=get_single("sort_by") or "trade_date",
        sort_dir=get_single("sort_dir") or "desc",
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_filters.py::test_build_filter_from_empty_query_string tests/test_filters.py::test_build_filter_from_query_string_basic tests/test_filters.py::test_build_filter_from_query_string_with_dates tests/test_filters.py::test_build_filter_from_query_string_with_bool tests/test_filters.py::test_build_filter_from_query_string_with_sort -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add app/services/filters.py tests/test_filters.py
git commit -m "feat: add build_filter_from_query_string helper"
```

---

## Task 3: Add `build_filter_from_request` function

**Files:**
- Modify: `app/services/filters.py`
- Test: `tests/test_filters.py`

**Step 1: Write the failing test**

Add to `tests/test_filters.py`:

```python
from app.services.filters import build_filter_from_request


def test_build_filter_from_request_empty():
    """Test empty request returns default filter."""
    request = MagicMock()
    request.query_params = {}
    result = build_filter_from_request(request)
    assert result.account_id is None
    assert result.sort_by == "trade_date"


def test_build_filter_from_request_with_params():
    """Test request with params builds correct filter."""
    request = MagicMock()
    request.query_params = {
        "symbol": "MSFT",
        "account_id": "2",
        "is_option": "false",
    }
    result = build_filter_from_request(request)
    assert result.symbol == "MSFT"
    assert result.account_id == 2
    assert result.is_option is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_filters.py::test_build_filter_from_request_empty -v`
Expected: FAIL with "cannot import name 'build_filter_from_request'"

**Step 3: Write minimal implementation**

Add to `app/services/filters.py`:

```python
def build_filter_from_request(request: Request) -> TransactionFilter:
    """Build a TransactionFilter from request query params."""
    params = request.query_params

    def get(key: str) -> str | None:
        return params.get(key) or None

    return TransactionFilter(
        account_id=parse_int_param(get("account_id")),
        symbol=get("symbol"),
        transaction_type=get("type"),
        tag_id=parse_int_param(get("tag_id")),
        start_date=parse_date_param(get("start_date")),
        end_date=parse_date_param(get("end_date")),
        search=get("search"),
        is_option=parse_bool_param(get("is_option")),
        option_type=get("option_type"),
        option_action=get("option_action"),
        sort_by=get("sort_by") or "trade_date",
        sort_dir=get("sort_dir") or "desc",
    )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_filters.py::test_build_filter_from_request_empty tests/test_filters.py::test_build_filter_from_request_with_params -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add app/services/filters.py tests/test_filters.py
git commit -m "feat: add build_filter_from_request helper"
```

---

## Task 4: Add `get_effective_transaction_filter` function

**Files:**
- Modify: `app/services/filters.py`
- Test: `tests/test_filters.py`

**Step 1: Write the failing test**

Add to `tests/test_filters.py`:

```python
from app.models import SavedFilter
from app.services.filters import get_effective_transaction_filter


def test_get_effective_filter_with_explicit_params(db_session: Session):
    """When request has filter params, use them (ignore favorite)."""
    # Create a favorite filter
    favorite = SavedFilter(
        name="Favorite",
        page="transactions",
        filter_json="symbol=IGNORED",
        is_favorite=True,
    )
    db_session.add(favorite)
    db_session.commit()

    request = MagicMock()
    request.query_params = {"symbol": "AAPL"}

    filter_obj, applied_favorite = get_effective_transaction_filter(request, db_session)

    assert filter_obj.symbol == "AAPL"
    assert applied_favorite is None


def test_get_effective_filter_applies_favorite(db_session: Session):
    """When no filter params and favorite exists, apply it."""
    favorite = SavedFilter(
        name="My Favorite",
        page="transactions",
        filter_json="symbol=TSLA&account_id=5",
        is_favorite=True,
    )
    db_session.add(favorite)
    db_session.commit()

    request = MagicMock()
    request.query_params = {}

    filter_obj, applied_favorite = get_effective_transaction_filter(request, db_session)

    assert filter_obj.symbol == "TSLA"
    assert filter_obj.account_id == 5
    assert applied_favorite is not None
    assert applied_favorite.name == "My Favorite"


def test_get_effective_filter_no_favorite(db_session: Session):
    """When no filter params and no favorite, return defaults."""
    request = MagicMock()
    request.query_params = {}

    filter_obj, applied_favorite = get_effective_transaction_filter(request, db_session)

    assert filter_obj.symbol is None
    assert filter_obj.account_id is None
    assert applied_favorite is None


def test_get_effective_filter_sort_only_applies_favorite(db_session: Session):
    """Sort params alone should still allow favorite to apply."""
    favorite = SavedFilter(
        name="Favorite",
        page="transactions",
        filter_json="symbol=GOOG",
        is_favorite=True,
    )
    db_session.add(favorite)
    db_session.commit()

    request = MagicMock()
    request.query_params = {"sort_by": "symbol", "sort_dir": "asc"}

    filter_obj, applied_favorite = get_effective_transaction_filter(request, db_session)

    assert filter_obj.symbol == "GOOG"
    assert applied_favorite is not None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_filters.py::test_get_effective_filter_with_explicit_params -v`
Expected: FAIL with "cannot import name 'get_effective_transaction_filter'"

**Step 3: Write minimal implementation**

Add to `app/services/filters.py`:

```python
from sqlalchemy.orm import Session

from app.models import SavedFilter
from app.services.saved_filter_service import get_favorite_filter


def get_effective_transaction_filter(
    request: Request,
    db: Session,
) -> tuple[TransactionFilter, SavedFilter | None]:
    """
    Build TransactionFilter from request params, or from favorite if no params.

    Returns (filter, applied_favorite) tuple.
    applied_favorite is None if explicit params were used or no favorite exists.
    """
    if has_any_filter_params(request):
        return build_filter_from_request(request), None

    favorite = get_favorite_filter(db, "transactions")
    if favorite:
        return build_filter_from_query_string(favorite.filter_json), favorite

    return TransactionFilter(), None
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_filters.py::test_get_effective_filter_with_explicit_params tests/test_filters.py::test_get_effective_filter_applies_favorite tests/test_filters.py::test_get_effective_filter_no_favorite tests/test_filters.py::test_get_effective_filter_sort_only_applies_favorite -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add app/services/filters.py tests/test_filters.py
git commit -m "feat: add get_effective_transaction_filter helper"
```

---

## Task 5: Update transactions router to use new helper

**Files:**
- Modify: `app/routers/transactions.py:67-183`

**Step 1: Run existing tests to ensure baseline**

Run: `uv run pytest tests/ -v -k transaction`
Expected: All existing tests PASS

**Step 2: Update the route handler**

Replace the query param parsing and filter building in `app/routers/transactions.py`:

```python
from app.services.filters import (
    PaginationParams,
    TransactionFilter,
    get_effective_transaction_filter,
)


@router.get("/", response_class=HTMLResponse)
def list_transactions(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
) -> Response:
    """List transactions with filtering, sorting, and pagination."""
    per_page = 50

    # Get effective filter (from request params or favorite)
    filters, applied_favorite = get_effective_transaction_filter(request, db)

    # Build pagination object
    pagination = PaginationParams(page=page, per_page=per_page)

    # Get transactions
    transactions, total = transaction_service.get_transactions(db, filters, pagination)

    total_pages = (total + per_page - 1) // per_page

    # Get filter options
    accounts = account_service.get_all_accounts(db)
    symbols = transaction_service.get_unique_symbols(db)
    types = transaction_service.get_unique_types(db)
    tags = tag_service.get_all_tags(db)
    option_types = transaction_service.get_unique_option_types(db)
    option_actions = transaction_service.get_unique_option_actions(db)

    # Build query string for saved filters and table links
    filter_query_string = build_filter_query_string(
        search=filters.search,
        account_id=filters.account_id,
        symbol=filters.symbol,
        type=filters.transaction_type,
        tag_id=filters.tag_id,
        start_date=str(filters.start_date) if filters.start_date else None,
        end_date=str(filters.end_date) if filters.end_date else None,
        is_option=str(filters.is_option).lower() if filters.is_option is not None else None,
        option_type=filters.option_type,
        option_action=filters.option_action,
        sort_by=filters.sort_by,
        sort_dir=filters.sort_dir,
    )

    # Get saved filters for this page
    saved_filters = saved_filter_service.get_filters_for_page(db, "transactions")

    context = {
        "transactions": transactions,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "accounts": accounts,
        "symbols": symbols,
        "types": types,
        "tags": tags,
        "option_types": option_types,
        "option_actions": option_actions,
        "saved_filters": saved_filters,
        "filter_query_string": filter_query_string,
        "applied_favorite": applied_favorite,
        # Current filter values for form
        "current_account_id": filters.account_id,
        "current_symbol": filters.symbol,
        "current_type": filters.transaction_type,
        "current_tag_id": filters.tag_id,
        "current_start_date": filters.start_date,
        "current_end_date": filters.end_date,
        "current_search": filters.search,
        "current_is_option": str(filters.is_option).lower() if filters.is_option is not None else None,
        "current_option_type": filters.option_type,
        "current_option_action": filters.option_action,
        "current_sort_by": filters.sort_by,
        "current_sort_dir": filters.sort_dir,
        "title": "Transactions",
    }

    # Use helper for HTMX response
    return htmx_response(
        templates=templates,
        request=request,
        full_template="transactions.html",
        partial_template="partials/transaction_table.html",
        context=context,
    )
```

**Step 3: Clean up unused imports**

Remove from imports at top of file:
- `parse_bool_param, parse_date_param, parse_int_param` (no longer used directly)

Update import from filters:
```python
from app.services.filters import (
    PaginationParams,
    get_effective_transaction_filter,
)
```

**Step 4: Run tests to verify nothing broke**

Run: `uv run pytest tests/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add app/routers/transactions.py
git commit -m "refactor: use get_effective_transaction_filter in transactions route"
```

---

## Task 6: Add UI badge for applied favorite

**Files:**
- Modify: `app/templates/transactions.html:9-27`

**Step 1: Update the Saved Filters section**

Replace lines 9-27 in `app/templates/transactions.html` with:

```html
<!-- Saved Filters -->
<div class="flex flex-wrap items-center gap-3 mb-4">
    <span class="text-sm font-medium">Saved:</span>
    <div id="saved-filters">
        {% set filter_page = "transactions" %}
        {% include "partials/saved_filter_list.html" %}
    </div>
    {% if filter_query_string %}
    <button
        class="btn btn-ghost btn-xs"
        onclick="document.getElementById('save-filter-modal').showModal()"
    >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Save Current
    </button>
    {% endif %}
    {% if applied_favorite %}
    <div class="badge badge-info gap-1">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
        </svg>
        <span>Using: {{ applied_favorite.name }}</span>
        <a href="/transactions" class="hover:text-info-content">&times;</a>
    </div>
    {% endif %}
</div>
```

**Step 2: Test manually**

1. Start the dev server: `uv run python run.py`
2. Create a saved filter and mark it as favorite
3. Navigate away, then back to `/transactions`
4. Verify the favorite filter is applied and badge shows
5. Click the × on the badge to clear

**Step 3: Commit**

```bash
git add app/templates/transactions.html
git commit -m "feat: show badge when favorite filter is auto-applied"
```

---

## Task 7: Run full test suite and type check

**Step 1: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All PASS

**Step 2: Run type checker**

Run: `uv run mypy app/ tests/`
Expected: No errors (or only pre-existing ones)

**Step 3: Run linter**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: No issues

**Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address linting/type issues"
```

---

## Summary

| Task | Description | Est. Time |
|------|-------------|-----------|
| 1 | Add `has_any_filter_params` | 5 min |
| 2 | Add `build_filter_from_query_string` | 5 min |
| 3 | Add `build_filter_from_request` | 5 min |
| 4 | Add `get_effective_transaction_filter` | 5 min |
| 5 | Update transactions router | 10 min |
| 6 | Add UI badge | 5 min |
| 7 | Final verification | 5 min |

**Total:** ~40 minutes

**Files changed:**
- `app/services/filters.py` — Add 4 new functions (~60 lines)
- `app/routers/transactions.py` — Simplify route handler (~-30 lines)
- `app/templates/transactions.html` — Add badge (~15 lines)
- `tests/test_filters.py` — Add tests (~80 lines)
