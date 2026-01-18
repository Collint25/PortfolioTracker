# Architecture Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove unused code and migrate to filter object pattern for cleaner, more maintainable architecture.

**Architecture:** Three-phase approach: (1) Remove trade_groups feature entirely (unused), (2) Migrate transaction filtering from inline to filter object pattern, (3) Standardize HTMX response handling. Each phase is independent and can be tested/committed separately.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Alembic (for migration)

---

## Phase 1: Remove Trade Groups Feature

Trade groups were designed for manual grouping but never used. LinkedTrades serves this purpose through auto-matching.

### Task 1.1: Remove trade_groups tests

**Files:**
- Delete: `tests/test_trade_groups.py`

**Step 1: Verify current test coverage**

Run: `uv run pytest tests/test_trade_groups.py -v`
Expected: 13 tests pass

**Step 2: Delete test file**

```bash
rm tests/test_trade_groups.py
```

**Step 3: Verify remaining tests pass**

Run: `uv run pytest -v`
Expected: 40 tests pass (53 - 13 = 40)

**Step 4: Commit**

```bash
git add tests/test_trade_groups.py
git commit -m "Remove trade_groups tests - unused feature

Preparing to remove trade_groups feature entirely.
Tests for this feature will be replaced by LinkedTrades."
```

---

### Task 1.2: Remove trade_groups router

**Files:**
- Delete: `app/routers/trade_groups.py`
- Modify: `app/main.py:13,30-31`

**Step 1: Remove router import from main.py**

In `app/main.py`, remove line 13:
```python
# DELETE THIS LINE:
    trade_groups,
```

**Step 2: Remove router registration from main.py**

In `app/main.py`, remove lines 30-31:
```python
# DELETE THESE LINES:
app.include_router(trade_groups.router, prefix="/trade-groups", tags=["trade-groups"])
```

**Step 3: Delete router file**

```bash
rm app/routers/trade_groups.py
```

**Step 4: Verify app starts without errors**

Run: `uv run python run.py &`
Expected: Server starts successfully
Run: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`
Run: `pkill -f "python run.py"`

**Step 5: Run tests**

Run: `uv run pytest -v`
Expected: All 40 tests pass

**Step 6: Commit**

```bash
git add app/main.py app/routers/trade_groups.py
git commit -m "Remove trade_groups router

Router removed, no longer registered in main app."
```

---

### Task 1.3: Remove trade_groups service

**Files:**
- Delete: `app/services/trade_group_service.py`

**Step 1: Check for imports of this service**

Run: `grep -r "trade_group_service" app/ tests/`
Expected: No matches (router already deleted)

**Step 2: Delete service file**

```bash
rm app/services/trade_group_service.py
```

**Step 3: Run tests**

Run: `uv run pytest -v`
Expected: All 40 tests pass

**Step 4: Commit**

```bash
git add app/services/trade_group_service.py
git commit -m "Remove trade_groups service

Service no longer needed, feature unused."
```

---

### Task 1.4: Remove TradeGroup model and relationships

**Files:**
- Modify: `app/models/transaction.py:15,63-65`
- Delete: `app/models/trade_group.py`

**Step 1: Remove TradeGroup import from Transaction model**

In `app/models/transaction.py`, remove line 15:
```python
# DELETE THIS LINE:
    from app.models.trade_group import TradeGroup
```

**Step 2: Remove trade_groups relationship from Transaction model**

In `app/models/transaction.py`, remove lines 63-65:
```python
# DELETE THESE LINES:
    trade_groups: Mapped[list["TradeGroup"]] = relationship(
        secondary="trade_group_transactions", back_populates="transactions"
    )
```

**Step 3: Delete TradeGroup model file**

```bash
rm app/models/trade_group.py
```

**Step 4: Run type checker**

Run: `uv run mypy app/ tests/`
Expected: No errors

**Step 5: Run tests**

Run: `uv run pytest -v`
Expected: All 40 tests pass

**Step 6: Commit**

```bash
git add app/models/transaction.py app/models/trade_group.py
git commit -m "Remove TradeGroup model and relationships

Model deleted, relationships removed from Transaction."
```

---

### Task 1.5: Create migration to drop trade_groups tables

**Files:**
- Create: `alembic/versions/YYYY_drop_trade_groups.py` (auto-generated)

**Step 1: Generate migration**

Run: `uv run alembic revision --autogenerate -m "drop trade_groups tables"`
Expected: Creates new migration file in `alembic/versions/`

**Step 2: Review migration**

Check migration contains:
- `op.drop_table('trade_group_transactions')`
- `op.drop_table('trade_groups')`

**Step 3: Apply migration**

Run: `uv run alembic upgrade head`
Expected: Migration applies successfully

**Step 4: Verify tables dropped**

Run: `uv run python -c "from app.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"`
Expected: No 'trade_groups' or 'trade_group_transactions' in output

**Step 5: Run tests**

Run: `uv run pytest -v`
Expected: All 40 tests pass

**Step 6: Commit**

```bash
git add alembic/versions/*.py
git commit -m "Migration: drop trade_groups tables

Tables no longer needed after feature removal."
```

---

## Phase 2: Migrate to Filter Object Pattern

Filters.py exists but isn't used. Migrate transaction_service to use it.

### Task 2.1: Add tests for filter functions

**Files:**
- Create: `tests/test_filters.py`

**Step 1: Write test for TransactionFilter**

Create `tests/test_filters.py`:
```python
"""Tests for filter objects and query builders."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models import Account, Transaction
from app.services.filters import (
    PaginationParams,
    TransactionFilter,
    apply_pagination,
    apply_transaction_filters,
    apply_transaction_sorting,
)


@pytest.fixture
def sample_transactions(db: Session) -> list[Transaction]:
    """Create sample transactions for testing."""
    account = Account(
        snaptrade_id="test_account",
        name="Test Account",
        account_number="12345",
        institution_name="Test Bank",
    )
    db.add(account)
    db.flush()

    transactions = [
        Transaction(
            snaptrade_id="txn1",
            account_id=account.id,
            symbol="AAPL",
            trade_date=date(2024, 1, 1),
            type="BUY",
            quantity=Decimal("10"),
            price=Decimal("150"),
            amount=Decimal("-1500"),
            is_option=False,
        ),
        Transaction(
            snaptrade_id="txn2",
            account_id=account.id,
            symbol="MSFT",
            trade_date=date(2024, 1, 2),
            type="SELL",
            quantity=Decimal("5"),
            price=Decimal("200"),
            amount=Decimal("1000"),
            is_option=False,
        ),
        Transaction(
            snaptrade_id="txn3",
            account_id=account.id,
            symbol="TSLA",
            underlying_symbol="TSLA",
            trade_date=date(2024, 1, 3),
            type="BUY",
            quantity=Decimal("1"),
            price=Decimal("5.00"),
            amount=Decimal("-500"),
            is_option=True,
            option_type="CALL",
            option_action="BUY_TO_OPEN",
            strike_price=Decimal("250"),
            expiration_date=date(2024, 2, 1),
        ),
    ]
    for txn in transactions:
        db.add(txn)
    db.commit()

    return transactions


def test_filter_by_account_id(db: Session, sample_transactions: list[Transaction]):
    """Test filtering by account_id."""
    filters = TransactionFilter(account_id=sample_transactions[0].account_id)
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 3
    assert all(t.account_id == sample_transactions[0].account_id for t in results)


def test_filter_by_symbol(db: Session, sample_transactions: list[Transaction]):
    """Test filtering by symbol."""
    filters = TransactionFilter(symbol="AAPL")
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].symbol == "AAPL"


def test_filter_by_underlying_symbol(db: Session, sample_transactions: list[Transaction]):
    """Test filtering by underlying_symbol for options."""
    filters = TransactionFilter(symbol="TSLA")
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].underlying_symbol == "TSLA"


def test_filter_by_transaction_type(db: Session, sample_transactions: list[Transaction]):
    """Test filtering by transaction type."""
    filters = TransactionFilter(transaction_type="BUY")
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 2
    assert all(t.type == "BUY" for t in results)


def test_filter_by_date_range(db: Session, sample_transactions: list[Transaction]):
    """Test filtering by date range."""
    filters = TransactionFilter(
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 2),
    )
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].trade_date == date(2024, 1, 2)


def test_filter_by_is_option(db: Session, sample_transactions: list[Transaction]):
    """Test filtering by is_option flag."""
    filters = TransactionFilter(is_option=True)
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].is_option is True


def test_filter_by_option_type(db: Session, sample_transactions: list[Transaction]):
    """Test filtering by option_type."""
    filters = TransactionFilter(option_type="CALL")
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].option_type == "CALL"


def test_sorting_asc(db: Session, sample_transactions: list[Transaction]):
    """Test sorting ascending."""
    filters = TransactionFilter(sort_by="trade_date", sort_dir="asc")
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)
    query = apply_transaction_sorting(query, filters)

    results = query.all()
    assert results[0].trade_date == date(2024, 1, 1)
    assert results[-1].trade_date == date(2024, 1, 3)


def test_sorting_desc(db: Session, sample_transactions: list[Transaction]):
    """Test sorting descending."""
    filters = TransactionFilter(sort_by="trade_date", sort_dir="desc")
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)
    query = apply_transaction_sorting(query, filters)

    results = query.all()
    assert results[0].trade_date == date(2024, 1, 3)
    assert results[-1].trade_date == date(2024, 1, 1)


def test_pagination(db: Session, sample_transactions: list[Transaction]):
    """Test pagination."""
    pagination = PaginationParams(page=1, per_page=2)
    query = db.query(Transaction)
    query = apply_pagination(query, pagination)

    results = query.all()
    assert len(results) == 2


def test_pagination_offset(db: Session, sample_transactions: list[Transaction]):
    """Test pagination offset."""
    pagination = PaginationParams(page=2, per_page=2)
    query = db.query(Transaction)
    query = apply_pagination(query, pagination)

    results = query.all()
    assert len(results) == 1


def test_combined_filters(db: Session, sample_transactions: list[Transaction]):
    """Test combining multiple filters."""
    filters = TransactionFilter(
        transaction_type="BUY",
        is_option=False,
    )
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)

    results = query.all()
    assert len(results) == 1
    assert results[0].symbol == "AAPL"
```

**Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_filters.py -v`
Expected: All filter tests pass

**Step 3: Commit**

```bash
git add tests/test_filters.py
git commit -m "Add tests for filter functions

Tests verify TransactionFilter, sorting, and pagination work correctly."
```

---

### Task 2.2: Refactor transaction_service to use filters

**Files:**
- Modify: `app/services/transaction_service.py:1-86`

**Step 1: Update imports**

In `app/services/transaction_service.py`, update imports:
```python
from datetime import date

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models import Transaction
from app.models.tag import transaction_tags
from app.services.filters import (
    PaginationParams,
    TransactionFilter,
    apply_pagination,
    apply_transaction_filters,
    apply_transaction_sorting,
)
```

**Step 2: Refactor get_transactions signature**

Replace lines 10-86 with:
```python
def get_transactions(
    db: Session,
    filters: TransactionFilter,
    pagination: PaginationParams = PaginationParams(),
) -> tuple[list[Transaction], int]:
    """
    Get filtered, sorted, paginated transactions.

    Returns (transactions, total_count).
    """
    query = db.query(Transaction)

    # Apply filters
    query = apply_transaction_filters(query, filters)

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    query = apply_transaction_sorting(query, filters)

    # Apply pagination
    query = apply_pagination(query, pagination)

    transactions = query.all()
    return transactions, total
```

**Step 3: Run tests**

Run: `uv run pytest tests/test_transactions.py -v`
Expected: Tests may fail (router not updated yet)

**Step 4: Run filter tests**

Run: `uv run pytest tests/test_filters.py -v`
Expected: All filter tests pass

**Step 5: Commit**

```bash
git add app/services/transaction_service.py
git commit -m "Refactor transaction_service to use filter objects

Service now accepts TransactionFilter instead of individual parameters.
Router not yet updated - tests may fail."
```

---

### Task 2.3: Update transactions router to use filters

**Files:**
- Modify: `app/routers/transactions.py:1-217`

**Step 1: Update imports**

In `app/routers/transactions.py`, add filter imports after line 14:
```python
from app.services.filters import PaginationParams, TransactionFilter
```

**Step 2: Refactor list_transactions to build filter object**

Replace lines 64-186 with:
```python
@router.get("/", response_class=HTMLResponse)
def list_transactions(
    request: Request,
    db: Session = Depends(get_db),
    account_id: str | None = Query(None),
    symbol: str | None = Query(None),
    type: str | None = Query(None),
    tag_id: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    search: str | None = Query(None),
    is_option: str | None = Query(None),
    option_type: str | None = Query(None),
    option_action: str | None = Query(None),
    sort_by: str = "trade_date",
    sort_dir: str = "desc",
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    """List transactions with filtering, sorting, and pagination."""
    per_page = 50

    # Parse query params
    account_id_int = parse_int_param(account_id)
    tag_id_int = parse_int_param(tag_id)
    is_option_val = parse_bool_param(is_option)
    start_date_val = parse_date_param(start_date)
    end_date_val = parse_date_param(end_date)

    # Build filter object
    filters = TransactionFilter(
        account_id=account_id_int,
        symbol=symbol or None,
        transaction_type=type or None,
        tag_id=tag_id_int,
        start_date=start_date_val,
        end_date=end_date_val,
        search=search or None,
        is_option=is_option_val,
        option_type=option_type or None,
        option_action=option_action or None,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

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
        search=search,
        account_id=account_id_int,
        symbol=symbol,
        type=type,
        tag_id=tag_id_int,
        start_date=start_date,
        end_date=end_date,
        is_option=is_option,
        option_type=option_type,
        option_action=option_action,
        sort_by=sort_by,
        sort_dir=sort_dir,
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
        # Current filter values
        "current_account_id": account_id_int,
        "current_symbol": symbol,
        "current_type": type,
        "current_tag_id": tag_id_int,
        "current_start_date": start_date_val,
        "current_end_date": end_date_val,
        "current_search": search,
        "current_is_option": is_option,
        "current_option_type": option_type,
        "current_option_action": option_action,
        "current_sort_by": sort_by,
        "current_sort_dir": sort_dir,
        "title": "Transactions",
    }

    # Return partial for HTMX requests
    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(
            request=request,
            name="partials/transaction_table.html",
            context=context,
        )

    return templates.TemplateResponse(
        request=request,
        name="transactions.html",
        context=context,
    )
```

**Step 3: Run tests**

Run: `uv run pytest tests/test_transactions.py -v`
Expected: All transaction tests pass

**Step 4: Run all tests**

Run: `uv run pytest -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add app/routers/transactions.py
git commit -m "Update transactions router to use filter objects

Router builds TransactionFilter and PaginationParams objects.
Cleaner API, easier to test."
```

---

### Task 2.4: Add LinkedTradeFilter usage (optional enhancement)

**Files:**
- Modify: `app/services/linked_trade_service.py:25-52`

**Step 1: Update imports**

Add at top of file:
```python
from app.services.filters import LinkedTradeFilter, PaginationParams, apply_linked_trade_filters, apply_pagination
```

**Step 2: Refactor get_all_linked_trades**

Replace lines 25-52 with:
```python
def get_all_linked_trades(
    db: Session,
    filters: LinkedTradeFilter = LinkedTradeFilter(),
    pagination: PaginationParams = PaginationParams(),
) -> tuple[list[LinkedTrade], int]:
    """Get filtered, paginated linked trades."""
    query = db.query(LinkedTrade)

    # Apply filters
    query = apply_linked_trade_filters(query, filters)

    # Get total
    total = query.count()

    # Sort
    query = query.order_by(LinkedTrade.expiration_date.desc(), LinkedTrade.id.desc())

    # Paginate
    query = apply_pagination(query, pagination)

    linked_trades = query.all()
    return linked_trades, total
```

**Step 3: Update router calls (if any)**

Check `app/routers/linked_trades.py` for calls to `get_all_linked_trades` and update to use filter objects.

**Step 4: Run tests**

Run: `uv run pytest tests/test_linked_trades.py -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add app/services/linked_trade_service.py app/routers/linked_trades.py
git commit -m "Migrate linked_trade_service to use filter objects

Consistent pattern across all service layer filtering."
```

---

## Phase 3: Standardize HTMX Response Handling

The htmx.py utility exists but isn't used consistently. Standardize usage.

### Task 3.1: Use htmx_response helper in transactions router

**Files:**
- Modify: `app/routers/transactions.py:175-186`

**Step 1: Import htmx_response helper**

Already imported from line 15, verify it's there.

**Step 2: Replace manual HTMX check with helper**

Replace lines 175-186 with:
```python
    # Use helper for HTMX response
    return htmx_response(
        templates=templates,
        request=request,
        full_template="transactions.html",
        partial_template="partials/transaction_table.html",
        context=context,
    )
```

**Step 3: Run tests**

Run: `uv run pytest tests/test_transactions.py -v`
Expected: All tests pass

**Step 4: Start app and test manually**

Run: `uv run python run.py &`
Visit: `http://localhost:8000/transactions`
Expected: Page loads correctly
Run: `pkill -f "python run.py"`

**Step 5: Commit**

```bash
git add app/routers/transactions.py
git commit -m "Use htmx_response helper in transactions router

Consistent HTMX handling across routers."
```

---

### Task 3.2: Apply htmx_response to other routers (optional)

**Files:**
- Check: `app/routers/linked_trades.py`, `app/routers/accounts.py`, etc.

**Step 1: Search for manual HTMX checks**

Run: `grep -n 'HX-Request.*true' app/routers/*.py`
Expected: List of files with manual checks

**Step 2: For each file, replace with htmx_response helper**

Follow same pattern as Task 3.1

**Step 3: Run tests after each change**

Run: `uv run pytest -v`
Expected: All tests pass

**Step 4: Commit each router separately**

Example:
```bash
git add app/routers/linked_trades.py
git commit -m "Use htmx_response helper in linked_trades router"
```

---

## Testing & Verification

### Final Verification Steps

**Step 1: Run full test suite**

Run: `uv run pytest -v --tb=short`
Expected: All 40+ tests pass

**Step 2: Run type checker**

Run: `uv run mypy app/ tests/`
Expected: No type errors

**Step 3: Run linter**

Run: `uv run ruff check .`
Expected: No lint errors

**Step 4: Start application and smoke test**

Run: `uv run python run.py &`

Test these endpoints:
- `http://localhost:8000/health` → `{"status":"ok"}`
- `http://localhost:8000/transactions` → Transactions page loads
- `http://localhost:8000/transactions?symbol=AAPL` → Filtered correctly
- `http://localhost:8000/accounts` → Accounts page loads

Run: `pkill -f "python run.py"`

**Step 5: Check no dead imports**

Run: `grep -r "trade_group" app/ tests/`
Expected: No matches

---

## Summary

**Files Created:**
- `tests/test_filters.py` - Filter function tests
- `alembic/versions/YYYY_drop_trade_groups.py` - Migration

**Files Modified:**
- `app/main.py` - Remove trade_groups router
- `app/models/transaction.py` - Remove trade_groups relationship
- `app/services/transaction_service.py` - Use filter objects
- `app/services/linked_trade_service.py` - Use filter objects
- `app/routers/transactions.py` - Build filter objects, use htmx_response
- `app/routers/linked_trades.py` - Use filter objects
- Various routers - Use htmx_response helper

**Files Deleted:**
- `tests/test_trade_groups.py`
- `app/routers/trade_groups.py`
- `app/services/trade_group_service.py`
- `app/models/trade_group.py`

**Lines of Code:**
- Removed: ~400 lines (trade_groups feature)
- Modified: ~150 lines (filter migration)
- Added: ~250 lines (filter tests)
- Net: ~-200 lines (cleaner codebase)

**Benefits:**
- Cleaner codebase (no dead code)
- Better testability (filter objects)
- Consistent patterns (htmx_response)
- Easier maintenance going forward
