# Filter Panel Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign transactions filter panel with multi-select include/exclude chips, two-row layout, and auto-trigger filtering.

**Architecture:** Extend `TransactionFilter` dataclass for multi-value fields with mode. Create reusable Jinja2 macro for chip multi-select. Use custom HTMX events for debounced auto-trigger.

**Tech Stack:** FastAPI, SQLAlchemy, Jinja2, HTMX, DaisyUI, vanilla JS

---

## Task 1: Update TransactionFilter Dataclass

**Files:**
- Modify: `app/services/filters.py:20-36`
- Test: `tests/test_filters.py` (create)

**Step 1: Write the failing test**

Create `tests/test_filters.py`:

```python
"""Tests for filter dataclasses and query builders."""

import pytest
from app.services.filters import TransactionFilter


def test_transaction_filter_defaults():
    """TransactionFilter has correct default values."""
    f = TransactionFilter()
    assert f.symbols is None
    assert f.symbol_mode == "include"
    assert f.types is None
    assert f.type_mode == "include"
    assert f.tag_ids is None
    assert f.tag_mode == "include"


def test_transaction_filter_with_multi_values():
    """TransactionFilter accepts list values."""
    f = TransactionFilter(
        symbols=["AAPL", "MSFT"],
        symbol_mode="exclude",
        types=["BUY", "SELL"],
        tag_ids=[1, 2, 3],
    )
    assert f.symbols == ["AAPL", "MSFT"]
    assert f.symbol_mode == "exclude"
    assert f.types == ["BUY", "SELL"]
    assert f.tag_ids == [1, 2, 3]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_filters.py -v`
Expected: FAIL - `TransactionFilter` doesn't have `symbols` field

**Step 3: Update TransactionFilter dataclass**

In `app/services/filters.py`, replace single-value fields with multi-value:

```python
@dataclass
class TransactionFilter:
    """Filter criteria for transaction queries."""

    account_id: int | None = None
    # Multi-select fields with include/exclude mode
    symbols: list[str] | None = None
    symbol_mode: str = "include"  # "include" or "exclude"
    types: list[str] | None = None
    type_mode: str = "include"
    tag_ids: list[int] | None = None
    tag_mode: str = "include"
    # Single-value fields
    start_date: date | None = None
    end_date: date | None = None
    search: str | None = None
    is_option: bool | None = None
    option_type: str | None = None
    option_action: str | None = None
    sort_by: str = "trade_date"
    sort_dir: str = "desc"
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_filters.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/filters.py tests/test_filters.py
git commit -m "feat(filters): add multi-value fields to TransactionFilter"
```

---

## Task 2: Update apply_transaction_filters for IN/NOT IN

**Files:**
- Modify: `app/services/filters.py:60-107`
- Test: `tests/test_filters.py`

**Step 1: Write the failing tests**

Add to `tests/test_filters.py`:

```python
from unittest.mock import MagicMock
from sqlalchemy.orm import Query
from app.services.filters import apply_transaction_filters, TransactionFilter
from app.models import Transaction


def test_apply_filters_symbols_include(db_session):
    """Include mode uses IN clause."""
    filters = TransactionFilter(symbols=["AAPL", "MSFT"], symbol_mode="include")
    query = db_session.query(Transaction)
    result = apply_transaction_filters(query, filters)
    # Check the query has IN clause
    sql = str(result.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "IN ('AAPL', 'MSFT')" in sql or "IN (\"AAPL\", \"MSFT\")" in sql


def test_apply_filters_symbols_exclude(db_session):
    """Exclude mode uses NOT IN clause."""
    filters = TransactionFilter(symbols=["AAPL"], symbol_mode="exclude")
    query = db_session.query(Transaction)
    result = apply_transaction_filters(query, filters)
    sql = str(result.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "NOT IN" in sql


def test_apply_filters_types_include(db_session):
    """Types include mode uses IN clause."""
    filters = TransactionFilter(types=["BUY", "SELL"], type_mode="include")
    query = db_session.query(Transaction)
    result = apply_transaction_filters(query, filters)
    sql = str(result.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "IN ('BUY', 'SELL')" in sql or "IN (\"BUY\", \"SELL\")" in sql


def test_apply_filters_tag_ids_exclude(db_session):
    """Tag IDs exclude mode filters out tagged transactions."""
    filters = TransactionFilter(tag_ids=[1, 2], tag_mode="exclude")
    query = db_session.query(Transaction)
    result = apply_transaction_filters(query, filters)
    sql = str(result.statement.compile(compile_kwargs={"literal_binds": True}))
    assert "NOT IN" in sql
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_filters.py::test_apply_filters_symbols_include -v`
Expected: FAIL - old code uses `==` not `IN`

**Step 3: Update apply_transaction_filters**

Replace the symbol, type, and tag filtering logic in `app/services/filters.py`:

```python
def apply_transaction_filters(query: Query, filters: TransactionFilter) -> Query:
    """Apply TransactionFilter criteria to a query."""
    if filters.account_id is not None:
        query = query.filter(Transaction.account_id == filters.account_id)

    # Symbols (multi-select with mode)
    if filters.symbols:
        symbol_condition = or_(
            Transaction.symbol.in_(filters.symbols),
            Transaction.underlying_symbol.in_(filters.symbols),
        )
        if filters.symbol_mode == "exclude":
            query = query.filter(~symbol_condition)
        else:
            query = query.filter(symbol_condition)

    # Types (multi-select with mode)
    if filters.types:
        if filters.type_mode == "exclude":
            query = query.filter(Transaction.type.notin_(filters.types))
        else:
            query = query.filter(Transaction.type.in_(filters.types))

    if filters.start_date:
        query = query.filter(Transaction.trade_date >= filters.start_date)

    if filters.end_date:
        query = query.filter(Transaction.trade_date <= filters.end_date)

    if filters.search:
        search_pattern = f"%{filters.search}%"
        query = query.filter(
            or_(
                Transaction.symbol.ilike(search_pattern),
                Transaction.underlying_symbol.ilike(search_pattern),
                Transaction.description.ilike(search_pattern),
            )
        )

    # Tag IDs (multi-select with mode)
    if filters.tag_ids:
        if filters.tag_mode == "exclude":
            # Exclude transactions that have ANY of these tags
            subquery = (
                query.session.query(transaction_tags.c.transaction_id)
                .filter(transaction_tags.c.tag_id.in_(filters.tag_ids))
                .distinct()
            )
            query = query.filter(Transaction.id.notin_(subquery))
        else:
            # Include transactions that have ANY of these tags
            query = query.join(transaction_tags).filter(
                transaction_tags.c.tag_id.in_(filters.tag_ids)
            )

    if filters.is_option is not None:
        query = query.filter(Transaction.is_option == filters.is_option)

    if filters.option_type:
        query = query.filter(Transaction.option_type == filters.option_type)

    if filters.option_action:
        query = query.filter(Transaction.option_action == filters.option_action)

    return query
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_filters.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/filters.py tests/test_filters.py
git commit -m "feat(filters): implement IN/NOT IN for multi-select filters"
```

---

## Task 3: Update Filter Parsing Functions

**Files:**
- Modify: `app/services/filters.py:162-210`
- Test: `tests/test_filters.py`

**Step 1: Write the failing tests**

Add to `tests/test_filters.py`:

```python
from app.services.filters import build_filter_from_query_string


def test_build_filter_from_query_string_multi_symbols():
    """Parses multiple symbol values from query string."""
    qs = "symbol=AAPL&symbol=MSFT&symbol_mode=exclude"
    f = build_filter_from_query_string(qs)
    assert f.symbols == ["AAPL", "MSFT"]
    assert f.symbol_mode == "exclude"


def test_build_filter_from_query_string_multi_types():
    """Parses multiple type values from query string."""
    qs = "type=BUY&type=SELL&type_mode=include"
    f = build_filter_from_query_string(qs)
    assert f.types == ["BUY", "SELL"]
    assert f.type_mode == "include"


def test_build_filter_from_query_string_single_symbol_compat():
    """Single symbol value still works (backward compat)."""
    qs = "symbol=AAPL"
    f = build_filter_from_query_string(qs)
    assert f.symbols == ["AAPL"]
    assert f.symbol_mode == "include"


def test_build_filter_from_query_string_multi_tag_ids():
    """Parses multiple tag_id values."""
    qs = "tag_id=1&tag_id=2&tag_mode=exclude"
    f = build_filter_from_query_string(qs)
    assert f.tag_ids == [1, 2]
    assert f.tag_mode == "exclude"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_filters.py::test_build_filter_from_query_string_multi_symbols -v`
Expected: FAIL

**Step 3: Update build_filter_from_query_string**

```python
def build_filter_from_query_string(query_string: str) -> TransactionFilter:
    """Parse a URL query string into a TransactionFilter."""
    if not query_string:
        return TransactionFilter()

    parsed = parse_qs(query_string)

    def get_single(key: str) -> str | None:
        values = parsed.get(key, [])
        return values[0] if values else None

    def get_list(key: str) -> list[str] | None:
        values = parsed.get(key, [])
        return values if values else None

    def get_int_list(key: str) -> list[int] | None:
        values = parsed.get(key, [])
        if not values:
            return None
        result = []
        for v in values:
            parsed_int = parse_int_param(v)
            if parsed_int is not None:
                result.append(parsed_int)
        return result if result else None

    return TransactionFilter(
        account_id=parse_int_param(get_single("account_id")),
        symbols=get_list("symbol"),
        symbol_mode=get_single("symbol_mode") or "include",
        types=get_list("type"),
        type_mode=get_single("type_mode") or "include",
        tag_ids=get_int_list("tag_id"),
        tag_mode=get_single("tag_mode") or "include",
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

**Step 4: Update build_filter_from_request similarly**

```python
def build_filter_from_request(request: "Request") -> TransactionFilter:
    """Build a TransactionFilter from request query params."""
    params = request.query_params

    def get(key: str) -> str | None:
        return params.get(key) or None

    def get_list(key: str) -> list[str] | None:
        values = params.getlist(key)
        return values if values else None

    def get_int_list(key: str) -> list[int] | None:
        values = params.getlist(key)
        if not values:
            return None
        result = []
        for v in values:
            parsed_int = parse_int_param(v)
            if parsed_int is not None:
                result.append(parsed_int)
        return result if result else None

    return TransactionFilter(
        account_id=parse_int_param(get("account_id")),
        symbols=get_list("symbol"),
        symbol_mode=get("symbol_mode") or "include",
        types=get_list("type"),
        type_mode=get("type_mode") or "include",
        tag_ids=get_int_list("tag_id"),
        tag_mode=get("tag_mode") or "include",
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

**Step 5: Update TRANSACTION_FILTER_PARAMS constant**

```python
TRANSACTION_FILTER_PARAMS = [
    "account_id",
    "symbol",
    "symbol_mode",
    "type",
    "type_mode",
    "tag_id",
    "tag_mode",
    "start_date",
    "end_date",
    "search",
    "is_option",
    "option_type",
    "option_action",
]
```

**Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_filters.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add app/services/filters.py tests/test_filters.py
git commit -m "feat(filters): update parsing for multi-value params"
```

---

## Task 4: Update Transactions Router

**Files:**
- Modify: `app/routers/transactions.py:26-66`
- Test: `tests/test_transactions.py`

**Step 1: Write the failing test**

Add to `tests/test_transactions.py`:

```python
def test_transactions_page_with_multi_symbol_filter(client):
    """Transactions page accepts multiple symbol parameters."""
    response = client.get("/transactions?symbol=AAPL&symbol=MSFT&symbol_mode=include")
    assert response.status_code == 200


def test_transactions_page_with_exclude_type(client):
    """Transactions page accepts exclude mode for types."""
    response = client.get("/transactions?type=DIVIDEND&type_mode=exclude")
    assert response.status_code == 200
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_transactions.py::test_transactions_page_with_multi_symbol_filter -v`
Expected: Likely PASS (router uses build_filter_from_request which now handles lists)

**Step 3: Update build_filter_query_string**

In `app/routers/transactions.py`:

```python
def build_filter_query_string(filters: "TransactionFilter") -> str:
    """Build a URL query string from filter parameters."""
    from app.services.filters import TransactionFilter

    params: list[tuple[str, str]] = []

    if filters.symbols:
        for sym in filters.symbols:
            params.append(("symbol", sym))
        if filters.symbol_mode != "include":
            params.append(("symbol_mode", filters.symbol_mode))

    if filters.types:
        for t in filters.types:
            params.append(("type", t))
        if filters.type_mode != "include":
            params.append(("type_mode", filters.type_mode))

    if filters.tag_ids:
        for tid in filters.tag_ids:
            params.append(("tag_id", str(tid)))
        if filters.tag_mode != "include":
            params.append(("tag_mode", filters.tag_mode))

    if filters.account_id:
        params.append(("account_id", str(filters.account_id)))
    if filters.start_date:
        params.append(("start_date", str(filters.start_date)))
    if filters.end_date:
        params.append(("end_date", str(filters.end_date)))
    if filters.search:
        params.append(("search", filters.search))
    if filters.is_option is not None:
        params.append(("is_option", str(filters.is_option).lower()))
    if filters.option_type:
        params.append(("option_type", filters.option_type))
    if filters.option_action:
        params.append(("option_action", filters.option_action))
    if filters.sort_by and filters.sort_by != "trade_date":
        params.append(("sort_by", filters.sort_by))
    if filters.sort_dir and filters.sort_dir != "desc":
        params.append(("sort_dir", filters.sort_dir))

    return urlencode(params)
```

**Step 4: Update template context variables**

In `list_transactions`, update context to pass list values:

```python
context = {
    # ... existing fields ...
    # Current filter values for form (now lists)
    "current_symbols": filters.symbols or [],
    "current_symbol_mode": filters.symbol_mode,
    "current_types": filters.types or [],
    "current_type_mode": filters.type_mode,
    "current_tag_ids": filters.tag_ids or [],
    "current_tag_mode": filters.tag_mode,
    # Keep these for unchanged filters
    "current_account_id": filters.account_id,
    "current_start_date": filters.start_date,
    "current_end_date": filters.end_date,
    "current_search": filters.search,
    "current_is_option": (
        str(filters.is_option).lower() if filters.is_option is not None else None
    ),
    "current_option_type": filters.option_type,
    "current_option_action": filters.option_action,
    "current_sort_by": filters.sort_by,
    "current_sort_dir": filters.sort_dir,
    # ...
}
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_transactions.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add app/routers/transactions.py tests/test_transactions.py
git commit -m "feat(transactions): update router for multi-value filters"
```

---

## Task 5: Add Symbol Autocomplete API Endpoint

**Files:**
- Create: `app/routers/api.py`
- Modify: `app/main.py`
- Test: `tests/test_api.py` (create)

**Step 1: Write the failing test**

Create `tests/test_api.py`:

```python
def test_symbols_autocomplete(client):
    """Symbol autocomplete returns matching symbols."""
    response = client.get("/api/symbols?q=AA")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_symbols_autocomplete_empty_query(client):
    """Symbol autocomplete with no query returns all symbols."""
    response = client.get("/api/symbols")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL - 404 endpoint not found

**Step 3: Create API router**

Create `app/routers/api.py`:

```python
"""API endpoints for AJAX/autocomplete functionality."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction

router = APIRouter()


@router.get("/symbols")
def get_symbols(
    db: Session = Depends(get_db),
    q: str = Query(default="", description="Search query"),
) -> list[str]:
    """Get symbols for autocomplete, optionally filtered by query."""
    query = db.query(Transaction.symbol).filter(Transaction.symbol.isnot(None)).distinct()

    if q:
        query = query.filter(Transaction.symbol.ilike(f"{q}%"))

    query = query.order_by(Transaction.symbol).limit(20)
    results = query.all()
    return [r[0] for r in results if r[0]]


@router.get("/types")
def get_types(db: Session = Depends(get_db)) -> list[str]:
    """Get all transaction types."""
    results = db.query(Transaction.type).distinct().order_by(Transaction.type).all()
    return [r[0] for r in results if r[0]]
```

**Step 4: Register router in main.py**

Add to `app/main.py`:

```python
from app.routers import (
    # ... existing imports ...
    api,
)

# ... after other routers ...
app.include_router(api.router, prefix="/api", tags=["api"])
```

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_api.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add app/routers/api.py app/main.py tests/test_api.py
git commit -m "feat(api): add symbol/type autocomplete endpoints"
```

---

## Task 6: Create Chip Multi-Select Jinja2 Macro

**Files:**
- Create: `app/templates/macros/chip_multiselect.html`

**Step 1: Create the macro file**

Create `app/templates/macros/chip_multiselect.html`:

```html
{% macro chip_multiselect(name, label, values, selected, mode, autocomplete_url=None, options=None) %}
{#
  Chip-based multi-select component with include/exclude toggle.

  Args:
    name: Field name for form submission (e.g., "symbol")
    label: Display label (e.g., "Symbol")
    values: Currently selected values (list)
    selected: Alias for values (backward compat)
    mode: "include" or "exclude"
    autocomplete_url: URL for autocomplete (for symbol field)
    options: Static list of options (for type/tag fields)
#}
<div class="form-control flex-1 min-w-[200px]" data-multiselect="{{ name }}">
  <div class="flex justify-between items-center">
    <label class="label py-1"><span class="label-text text-xs">{{ label }}</span></label>
    <select
      name="{{ name }}_mode"
      class="select select-xs w-24 h-6 min-h-0"
      onchange="dispatchFilterChanged()"
    >
      <option value="include" {{ 'selected' if mode == 'include' else '' }}>Include</option>
      <option value="exclude" {{ 'selected' if mode == 'exclude' else '' }}>Exclude</option>
    </select>
  </div>

  <div class="flex flex-wrap gap-1 p-2 border rounded-lg border-base-300 bg-base-100 min-h-[2.5rem] items-center">
    {# Render existing chips #}
    {% for val in (values or selected or []) %}
    <span class="badge {{ 'badge-success' if mode == 'include' else 'badge-error' }} gap-1 chip" data-value="{{ val }}">
      {{ val }}
      <button type="button" onclick="removeChip(this)" class="hover:text-base-content/50">&times;</button>
      <input type="hidden" name="{{ name }}" value="{{ val }}" />
    </span>
    {% endfor %}

    {# Input for adding new chips #}
    {% if autocomplete_url %}
    <input
      type="text"
      class="flex-1 min-w-[80px] bg-transparent outline-none text-sm chip-input"
      placeholder="Add {{ label|lower }}..."
      data-autocomplete="{{ autocomplete_url }}"
      data-name="{{ name }}"
      autocomplete="off"
    />
    {% elif options %}
    <div class="dropdown dropdown-end flex-1">
      <label tabindex="0" class="text-sm text-base-content/50 cursor-pointer hover:text-base-content">
        + Add {{ label|lower }}
      </label>
      <ul tabindex="0" class="dropdown-content z-50 menu p-2 shadow bg-base-100 rounded-box w-40 max-h-60 overflow-y-auto">
        {% for opt in options %}
        <li>
          <a onclick="addChip('{{ name }}', '{{ opt.value if opt.value is defined else opt }}', '{{ opt.label if opt.label is defined else opt }}', this)">
            {{ opt.label if opt.label is defined else opt }}
          </a>
        </li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}
  </div>
</div>
{% endmacro %}
```

**Step 2: Verify template syntax**

Run: `uv run python -c "from jinja2 import Environment, FileSystemLoader; e = Environment(loader=FileSystemLoader('app/templates')); e.get_template('macros/chip_multiselect.html')"`
Expected: No errors

**Step 3: Commit**

```bash
mkdir -p app/templates/macros
git add app/templates/macros/chip_multiselect.html
git commit -m "feat(ui): add chip multi-select Jinja2 macro"
```

---

## Task 7: Update Transactions Template - Layout

**Files:**
- Modify: `app/templates/transactions.html`

**Step 1: Update the filter form structure**

Replace the filter form (lines 51-190) with the new two-row layout:

```html
<!-- Filters -->
<div class="card bg-base-100 shadow mb-6">
    <div class="card-body py-4">
        <form
            id="filter-form"
            hx-get="/transactions"
            hx-target="#transaction-table"
            hx-trigger="filterChanged from:body"
            hx-push-url="true"
            hx-indicator="#table-loading"
        >
            <!-- Row 1: Primary Filters -->
            <div class="flex flex-wrap gap-3 items-end mb-3">
                <!-- Search -->
                <div class="form-control w-48">
                    <label class="label py-1"><span class="label-text text-xs">Search</span></label>
                    <input
                        type="text"
                        name="search"
                        value="{{ current_search or '' }}"
                        placeholder="Symbol or description"
                        class="input input-bordered input-sm"
                        oninput="debouncedFilterChange()"
                    />
                </div>

                <!-- Symbol (chip multi-select with autocomplete) -->
                {% from "macros/chip_multiselect.html" import chip_multiselect %}
                {{ chip_multiselect(
                    name="symbol",
                    label="Symbol",
                    values=current_symbols,
                    mode=current_symbol_mode,
                    autocomplete_url="/api/symbols"
                ) }}

                <!-- Type (chip multi-select with dropdown) -->
                {{ chip_multiselect(
                    name="type",
                    label="Type",
                    values=current_types,
                    mode=current_type_mode,
                    options=types
                ) }}

                <!-- Account (single select) -->
                <div class="form-control w-40">
                    <label class="label py-1"><span class="label-text text-xs">Account</span></label>
                    <select name="account_id" class="select select-bordered select-sm" onchange="dispatchFilterChanged()">
                        <option value="">All</option>
                        {% for account in accounts %}
                        <option value="{{ account.id }}" {{ 'selected' if current_account_id == account.id else '' }}>
                            {{ account.name }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
            </div>

            <!-- Row 2: Refinement Filters -->
            <div class="flex flex-wrap gap-3 items-end pt-3 border-t border-base-200">
                <!-- Date Range -->
                <div class="form-control w-36">
                    <label class="label py-1"><span class="label-text text-xs">From</span></label>
                    <input
                        type="date"
                        name="start_date"
                        value="{{ current_start_date or '' }}"
                        class="input input-bordered input-sm"
                        onchange="dispatchFilterChanged()"
                    />
                </div>

                <div class="form-control w-36">
                    <label class="label py-1"><span class="label-text text-xs">To</span></label>
                    <input
                        type="date"
                        name="end_date"
                        value="{{ current_end_date or '' }}"
                        class="input input-bordered input-sm"
                        onchange="dispatchFilterChanged()"
                    />
                </div>

                <!-- Options Group -->
                <div class="flex items-end gap-2 px-3 py-2 bg-base-200 rounded-lg">
                    <span class="text-xs text-base-content/70 font-medium self-center">Options:</span>

                    <div class="form-control w-28">
                        <select name="is_option" class="select select-bordered select-sm" onchange="dispatchFilterChanged()">
                            <option value="">All</option>
                            <option value="true" {{ 'selected' if current_is_option == 'true' else '' }}>Options</option>
                            <option value="false" {{ 'selected' if current_is_option == 'false' else '' }}>Stocks</option>
                        </select>
                    </div>

                    <div class="form-control w-24">
                        <select name="option_type" class="select select-bordered select-sm" onchange="dispatchFilterChanged()">
                            <option value="">C/P</option>
                            {% for ot in option_types %}
                            <option value="{{ ot }}" {{ 'selected' if current_option_type == ot else '' }}>{{ ot }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="form-control w-36">
                        <select name="option_action" class="select select-bordered select-sm" onchange="dispatchFilterChanged()">
                            <option value="">Action</option>
                            {% for oa in option_actions %}
                            <option value="{{ oa }}" {{ 'selected' if current_option_action == oa else '' }}>{{ oa.replace('_', ' ') }}</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>

                <!-- Tag (chip multi-select) -->
                {{ chip_multiselect(
                    name="tag_id",
                    label="Tag",
                    values=current_tag_ids,
                    mode=current_tag_mode,
                    options=tags|map(attribute='id')|zip(tags|map(attribute='name'))|list
                ) }}

                <!-- Clear Filters -->
                <a href="/transactions" class="btn btn-ghost btn-sm text-error ml-auto">Clear All</a>
            </div>

            <!-- Hidden sort fields -->
            <input type="hidden" name="sort_by" value="{{ current_sort_by }}" />
            <input type="hidden" name="sort_dir" value="{{ current_sort_dir }}" />
        </form>
    </div>
</div>

<!-- Loading indicator -->
<div id="table-loading" class="htmx-indicator flex justify-center py-4">
    <span class="loading loading-spinner loading-md"></span>
</div>
```

**Step 2: Manual test**

Run: `uv run python run.py`
Navigate to: http://localhost:8000/transactions
Verify: Two-row layout renders

**Step 3: Commit**

```bash
git add app/templates/transactions.html
git commit -m "feat(ui): update transactions template with two-row layout"
```

---

## Task 8: Add JavaScript for Auto-Trigger and Chips

**Files:**
- Modify: `app/templates/transactions.html`

**Step 1: Add JavaScript block to template**

Add before `{% endblock %}`:

```html
{% block scripts %}
<script>
// Debounce helper
function debounce(fn, ms) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), ms);
    };
}

// Dispatch filter change event
function dispatchFilterChanged() {
    document.body.dispatchEvent(new CustomEvent('filterChanged'));
}

// Debounced version for text inputs
const debouncedFilterChange = debounce(dispatchFilterChanged, 300);

// Remove chip and trigger filter
function removeChip(btn) {
    btn.closest('.chip').remove();
    dispatchFilterChanged();
}

// Add chip from dropdown
function addChip(name, value, label, element) {
    const container = document.querySelector(`[data-multiselect="${name}"] .flex-wrap`);
    const mode = document.querySelector(`[name="${name}_mode"]`).value;
    const badgeClass = mode === 'include' ? 'badge-success' : 'badge-error';

    // Check if already exists
    if (container.querySelector(`[data-value="${value}"]`)) {
        return;
    }

    // Create chip
    const chip = document.createElement('span');
    chip.className = `badge ${badgeClass} gap-1 chip`;
    chip.dataset.value = value;
    chip.innerHTML = `
        ${label}
        <button type="button" onclick="removeChip(this)" class="hover:text-base-content/50">&times;</button>
        <input type="hidden" name="${name}" value="${value}" />
    `;

    // Insert before the dropdown/input
    const addButton = container.querySelector('.dropdown, .chip-input');
    container.insertBefore(chip, addButton);

    // Close dropdown
    if (element) {
        element.closest('.dropdown')?.blur();
        document.activeElement?.blur();
    }

    dispatchFilterChanged();
}

// Update chip colors when mode changes
document.querySelectorAll('[name$="_mode"]').forEach(select => {
    select.addEventListener('change', function() {
        const name = this.name.replace('_mode', '');
        const container = document.querySelector(`[data-multiselect="${name}"]`);
        const isInclude = this.value === 'include';

        container.querySelectorAll('.chip').forEach(chip => {
            chip.classList.remove('badge-success', 'badge-error');
            chip.classList.add(isInclude ? 'badge-success' : 'badge-error');
        });
    });
});

// Autocomplete for symbol input
document.querySelectorAll('.chip-input[data-autocomplete]').forEach(input => {
    let dropdown = null;

    input.addEventListener('input', debounce(async function() {
        const url = this.dataset.autocomplete;
        const name = this.dataset.name;
        const query = this.value.trim();

        if (query.length < 1) {
            if (dropdown) dropdown.remove();
            return;
        }

        const response = await fetch(`${url}?q=${encodeURIComponent(query)}`);
        const symbols = await response.json();

        // Remove existing dropdown
        if (dropdown) dropdown.remove();

        if (symbols.length === 0) return;

        // Create dropdown
        dropdown = document.createElement('ul');
        dropdown.className = 'absolute z-50 menu p-2 shadow bg-base-100 rounded-box w-40 max-h-60 overflow-y-auto';
        dropdown.style.top = '100%';
        dropdown.style.left = '0';

        // Get existing values
        const container = this.closest('[data-multiselect]');
        const existing = Array.from(container.querySelectorAll('.chip')).map(c => c.dataset.value);

        symbols.filter(s => !existing.includes(s)).forEach(symbol => {
            const li = document.createElement('li');
            li.innerHTML = `<a>${symbol}</a>`;
            li.querySelector('a').addEventListener('click', () => {
                addChip(name, symbol, symbol);
                this.value = '';
                dropdown.remove();
                dropdown = null;
            });
            dropdown.appendChild(li);
        });

        this.parentElement.style.position = 'relative';
        this.parentElement.appendChild(dropdown);
    }, 200));

    // Close dropdown on blur
    input.addEventListener('blur', () => {
        setTimeout(() => {
            if (dropdown) {
                dropdown.remove();
                dropdown = null;
            }
        }, 200);
    });

    // Handle enter key
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const value = this.value.trim().toUpperCase();
            if (value) {
                const name = this.dataset.name;
                addChip(name, value, value);
                this.value = '';
                if (dropdown) {
                    dropdown.remove();
                    dropdown = null;
                }
            }
        }
    });
});
</script>
{% endblock %}
```

**Step 2: Verify base template has scripts block**

Check `app/templates/base.html` has `{% block scripts %}{% endblock %}` before `</body>`.

**Step 3: Manual test**

Run: `uv run python run.py`
Test:
- Type in search field, wait 300ms, table updates
- Add symbol chip, table updates immediately
- Change include/exclude, chips change color, table updates
- Remove chip, table updates

**Step 4: Commit**

```bash
git add app/templates/transactions.html
git commit -m "feat(ui): add JavaScript for auto-trigger and chip management"
```

---

## Task 9: Fix Tag Multi-Select Options

**Files:**
- Modify: `app/templates/transactions.html`

**Step 1: Fix tag options format**

The tag options need value and label. Update the chip_multiselect call:

```html
<!-- Tag (chip multi-select) -->
{% set tag_options = [] %}
{% for tag in tags %}
    {% set _ = tag_options.append({'value': tag.id|string, 'label': tag.name}) %}
{% endfor %}
{{ chip_multiselect(
    name="tag_id",
    label="Tag",
    values=current_tag_ids|map('string')|list,
    mode=current_tag_mode,
    options=tag_options
) }}
```

**Step 2: Manual test**

Run: `uv run python run.py`
Verify: Tag dropdown shows tag names, adds chips correctly

**Step 3: Commit**

```bash
git add app/templates/transactions.html
git commit -m "fix(ui): correct tag options format in chip multi-select"
```

---

## Task 10: Run Full Test Suite and Type Check

**Step 1: Run all tests**

Run: `uv run pytest -v`
Expected: All tests pass

**Step 2: Run type checker**

Run: `uv run mypy app/ tests/`
Expected: No errors (or only pre-existing ones)

**Step 3: Run linter**

Run: `uv run ruff check . --fix && uv run ruff format .`
Expected: Clean

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore: lint and type fixes for filter panel redesign"
```

---

## Summary

After completing all tasks:
- TransactionFilter supports multi-value symbols, types, tag_ids with include/exclude mode
- Filter parsing handles repeated query params
- New `/api/symbols` and `/api/types` endpoints for autocomplete
- Two-row filter layout with all filters visible
- Chip-based multi-select for Symbol, Type, Tag
- Auto-trigger filtering on all field changes (debounced for text)
