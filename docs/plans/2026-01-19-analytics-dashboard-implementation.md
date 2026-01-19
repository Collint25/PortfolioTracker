# Analytics Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build MVP analytics page with P/L summary cards and cumulative P/L line chart.

**Architecture:** Extends existing `pl_calcs.py` and `lot_service.py` rather than creating parallel logic. New `metrics_service.py` orchestrates data gathering. Chart.js renders client-side.

**Tech Stack:** FastAPI, SQLAlchemy, Jinja2, HTMX, Chart.js, DaisyUI

---

## Phase 1: Backend Calculations

### Task 1.1: Add pl_over_time function to pl_calcs.py

**Files:**
- Modify: `app/calculations/pl_calcs.py`
- Test: `tests/test_calculations/test_pl_calcs.py`

**Step 1: Write the failing test**

Add to `tests/test_calculations/test_pl_calcs.py`:

```python
from datetime import date


def make_lot_with_date(realized_pl: str, is_closed: bool, close_date: date | None) -> MagicMock:
    """Create a mock TradeLot with close date for time series tests."""
    lt = MagicMock()
    lt.realized_pl = Decimal(realized_pl)
    lt.is_closed = is_closed
    # Simulate getting close date from last leg
    if close_date:
        leg = MagicMock()
        leg.trade_date = close_date
        lt.legs = [leg]
    else:
        lt.legs = []
    return lt


class TestPlOverTime:
    def test_returns_cumulative_pl_by_date(self):
        """Returns list of dicts with date and cumulative P/L."""
        lots = [
            make_lot_with_date("100", is_closed=True, close_date=date(2025, 1, 10)),
            make_lot_with_date("50", is_closed=True, close_date=date(2025, 1, 15)),
        ]

        result = pl_calcs.pl_over_time(lots)

        assert len(result) == 2
        assert result[0] == {"date": date(2025, 1, 10), "cumulative_pl": Decimal("100")}
        assert result[1] == {"date": date(2025, 1, 15), "cumulative_pl": Decimal("150")}

    def test_sorts_by_date(self):
        """Results are sorted chronologically even if input is not."""
        lots = [
            make_lot_with_date("50", is_closed=True, close_date=date(2025, 1, 20)),
            make_lot_with_date("100", is_closed=True, close_date=date(2025, 1, 5)),
        ]

        result = pl_calcs.pl_over_time(lots)

        assert result[0]["date"] == date(2025, 1, 5)
        assert result[1]["date"] == date(2025, 1, 20)

    def test_aggregates_same_day(self):
        """Multiple closes on same day are aggregated into one data point."""
        lots = [
            make_lot_with_date("100", is_closed=True, close_date=date(2025, 1, 10)),
            make_lot_with_date("50", is_closed=True, close_date=date(2025, 1, 10)),
        ]

        result = pl_calcs.pl_over_time(lots)

        assert len(result) == 1
        assert result[0]["cumulative_pl"] == Decimal("150")

    def test_excludes_open_lots(self):
        """Open lots are excluded from time series."""
        lots = [
            make_lot_with_date("100", is_closed=True, close_date=date(2025, 1, 10)),
            make_lot_with_date("999", is_closed=False, close_date=None),
        ]

        result = pl_calcs.pl_over_time(lots)

        assert len(result) == 1
        assert result[0]["cumulative_pl"] == Decimal("100")

    def test_empty_list_returns_empty(self):
        """Empty input returns empty list."""
        result = pl_calcs.pl_over_time([])
        assert result == []
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_calculations/test_pl_calcs.py::TestPlOverTime -v
```

Expected: FAIL with `AttributeError: module 'app.calculations.pl_calcs' has no attribute 'pl_over_time'`

**Step 3: Write minimal implementation**

Add to `app/calculations/pl_calcs.py`:

```python
from collections import defaultdict
from datetime import date


def pl_over_time(lots: list["TradeLot"]) -> list[dict]:
    """
    Calculate cumulative P/L over time from closed lots.

    Returns list of dicts with 'date' and 'cumulative_pl' keys,
    sorted chronologically. Same-day closes are aggregated.
    """
    # Group P/L by close date
    daily_pl: dict[date, Decimal] = defaultdict(Decimal)

    for lot in lots:
        if not lot.is_closed:
            continue
        # Get close date from last leg
        if lot.legs:
            close_date = lot.legs[-1].trade_date
            daily_pl[close_date] += lot.realized_pl

    # Sort by date and compute cumulative
    sorted_dates = sorted(daily_pl.keys())
    result = []
    cumulative = Decimal("0")

    for d in sorted_dates:
        cumulative += daily_pl[d]
        result.append({"date": d, "cumulative_pl": cumulative})

    return result
```

Also fix the type hint at top of file - change:

```python
if TYPE_CHECKING:
    from app.models import LinkedTrade
```

to:

```python
if TYPE_CHECKING:
    from app.models import TradeLot
```

And update function signatures from `LinkedTrade` to `TradeLot`.

**Step 4: Update __init__.py exports**

Add to `app/calculations/__init__.py`:

```python
from app.calculations.pl_calcs import linked_trade_pl, pl_over_time, pl_summary
```

And add `"pl_over_time"` to `__all__`.

**Step 5: Run test to verify it passes**

```bash
uv run pytest tests/test_calculations/test_pl_calcs.py::TestPlOverTime -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add app/calculations/ tests/test_calculations/test_pl_calcs.py
git commit -m "feat(calculations): add pl_over_time function for time series data"
```

---

### Task 1.2: Extend lot_service.get_pl_summary with date filtering

**Files:**
- Modify: `app/services/lot_service.py`
- Test: `tests/test_lot_service.py`

**Step 1: Write the failing test**

Add to `tests/test_lot_service.py`:

```python
from datetime import date


class TestGetPlSummaryDateFiltering:
    def test_filters_by_start_date(self, db_session):
        """Only includes lots closed on or after start_date."""
        account = Account(name="Test", institution="Test")
        db_session.add(account)
        db_session.flush()

        # Create two closed lots with different close dates via legs
        lot1 = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="AAPL",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("100"),
            is_closed=True,
        )
        lot2 = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="MSFT",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("200"),
            is_closed=True,
        )
        db_session.add_all([lot1, lot2])
        db_session.flush()

        # Add closing transactions with dates
        txn1 = Transaction(
            account_id=account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 5),
            type="SELL",
            quantity=Decimal("10"),
        )
        txn2 = Transaction(
            account_id=account.id,
            symbol="MSFT",
            trade_date=date(2025, 1, 15),
            type="SELL",
            quantity=Decimal("10"),
        )
        db_session.add_all([txn1, txn2])
        db_session.flush()

        leg1 = LotTransaction(
            trade_lot_id=lot1.id,
            transaction_id=txn1.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 5),
            is_opening=False,
        )
        leg2 = LotTransaction(
            trade_lot_id=lot2.id,
            transaction_id=txn2.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 15),
            is_opening=False,
        )
        db_session.add_all([leg1, leg2])
        db_session.commit()

        # Filter: only lots closed on/after Jan 10
        result = lot_service.get_pl_summary(
            db_session, start_date=date(2025, 1, 10)
        )

        assert result["total_pl"] == Decimal("200")  # Only lot2
        assert result["closed_count"] == 1

    def test_filters_by_end_date(self, db_session):
        """Only includes lots closed on or before end_date."""
        account = Account(name="Test", institution="Test")
        db_session.add(account)
        db_session.flush()

        lot1 = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="AAPL",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("100"),
            is_closed=True,
        )
        lot2 = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="MSFT",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("200"),
            is_closed=True,
        )
        db_session.add_all([lot1, lot2])
        db_session.flush()

        txn1 = Transaction(
            account_id=account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 5),
            type="SELL",
            quantity=Decimal("10"),
        )
        txn2 = Transaction(
            account_id=account.id,
            symbol="MSFT",
            trade_date=date(2025, 1, 15),
            type="SELL",
            quantity=Decimal("10"),
        )
        db_session.add_all([txn1, txn2])
        db_session.flush()

        leg1 = LotTransaction(
            trade_lot_id=lot1.id,
            transaction_id=txn1.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 5),
            is_opening=False,
        )
        leg2 = LotTransaction(
            trade_lot_id=lot2.id,
            transaction_id=txn2.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 15),
            is_opening=False,
        )
        db_session.add_all([leg1, leg2])
        db_session.commit()

        # Filter: only lots closed on/before Jan 10
        result = lot_service.get_pl_summary(
            db_session, end_date=date(2025, 1, 10)
        )

        assert result["total_pl"] == Decimal("100")  # Only lot1
        assert result["closed_count"] == 1
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_lot_service.py::TestGetPlSummaryDateFiltering -v
```

Expected: FAIL (unexpected keyword argument 'start_date')

**Step 3: Write minimal implementation**

Modify `app/services/lot_service.py` function `get_pl_summary`:

```python
def get_pl_summary(
    db: Session,
    account_id: int | None = None,
    account_ids: list[int] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    """Get P/L summary statistics with optional date filtering."""
    query = db.query(TradeLot)

    if account_id is not None:
        query = query.filter(TradeLot.account_id == account_id)
    elif account_ids:
        query = query.filter(TradeLot.account_id.in_(account_ids))

    # Date filtering requires joining to LotTransaction to find close date
    if start_date or end_date:
        # Subquery: get lot IDs with closing leg in date range
        from app.models import LotTransaction

        closing_legs = db.query(LotTransaction.trade_lot_id).filter(
            LotTransaction.is_opening == False  # noqa: E712
        )
        if start_date:
            closing_legs = closing_legs.filter(LotTransaction.trade_date >= start_date)
        if end_date:
            closing_legs = closing_legs.filter(LotTransaction.trade_date <= end_date)

        query = query.filter(TradeLot.id.in_(closing_legs.subquery()))

    return pl_calcs.pl_summary(query.all())
```

Add import at top:

```python
from datetime import date
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_lot_service.py::TestGetPlSummaryDateFiltering -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/services/lot_service.py tests/test_lot_service.py
git commit -m "feat(lot_service): add date filtering to get_pl_summary"
```

---

### Task 1.3: Create metrics_service.py with dataclasses

**Files:**
- Create: `app/services/metrics_service.py`
- Test: `tests/test_metrics_service.py`

**Step 1: Write the failing test**

Create `tests/test_metrics_service.py`:

```python
"""Tests for metrics service."""

from datetime import date
from decimal import Decimal

import pytest

from app.models import Account, LotTransaction, Position, TradeLot, Transaction
from app.services import metrics_service


class TestGetMetrics:
    def test_returns_metrics_result(self, db_session):
        """Returns MetricsResult with summary and time series."""
        account = Account(name="Test", institution="Test")
        db_session.add(account)
        db_session.flush()

        # Create a closed lot
        lot = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="AAPL",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("150"),
            is_closed=True,
        )
        db_session.add(lot)
        db_session.flush()

        txn = Transaction(
            account_id=account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 15),
            type="SELL",
            quantity=Decimal("10"),
        )
        db_session.add(txn)
        db_session.flush()

        leg = LotTransaction(
            trade_lot_id=lot.id,
            transaction_id=txn.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 15),
            is_opening=False,
        )
        db_session.add(leg)
        db_session.commit()

        result = metrics_service.get_metrics(db_session)

        assert isinstance(result, metrics_service.MetricsResult)
        assert result.summary.total_realized_pl == Decimal("150")
        assert result.summary.total_trades == 1
        assert result.summary.winning_trades == 1
        assert result.summary.win_rate == 1.0
        assert len(result.pl_over_time) == 1
        assert result.pl_over_time[0].cumulative_pl == Decimal("150")

    def test_filters_by_account_ids(self, db_session):
        """Respects account_ids filter."""
        account1 = Account(name="Account1", institution="Test")
        account2 = Account(name="Account2", institution="Test")
        db_session.add_all([account1, account2])
        db_session.flush()

        lot1 = TradeLot(
            account_id=account1.id,
            instrument_type="STOCK",
            symbol="AAPL",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("100"),
            is_closed=True,
        )
        lot2 = TradeLot(
            account_id=account2.id,
            instrument_type="STOCK",
            symbol="MSFT",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("200"),
            is_closed=True,
        )
        db_session.add_all([lot1, lot2])
        db_session.flush()

        txn1 = Transaction(
            account_id=account1.id, symbol="AAPL",
            trade_date=date(2025, 1, 10), type="SELL", quantity=Decimal("10")
        )
        txn2 = Transaction(
            account_id=account2.id, symbol="MSFT",
            trade_date=date(2025, 1, 10), type="SELL", quantity=Decimal("10")
        )
        db_session.add_all([txn1, txn2])
        db_session.flush()

        leg1 = LotTransaction(
            trade_lot_id=lot1.id, transaction_id=txn1.id,
            allocated_quantity=Decimal("10"), trade_date=date(2025, 1, 10), is_opening=False
        )
        leg2 = LotTransaction(
            trade_lot_id=lot2.id, transaction_id=txn2.id,
            allocated_quantity=Decimal("10"), trade_date=date(2025, 1, 10), is_opening=False
        )
        db_session.add_all([leg1, leg2])
        db_session.commit()

        result = metrics_service.get_metrics(
            db_session, account_ids=[account1.id]
        )

        assert result.summary.total_realized_pl == Decimal("100")

    def test_includes_unrealized_pl(self, db_session):
        """Calculates unrealized P/L from open positions."""
        account = Account(name="Test", institution="Test")
        db_session.add(account)
        db_session.flush()

        # Position with unrealized gain
        position = Position(
            account_id=account.id,
            symbol="AAPL",
            quantity=Decimal("10"),
            average_cost=Decimal("100"),
            current_price=Decimal("120"),
        )
        db_session.add(position)
        db_session.commit()

        result = metrics_service.get_metrics(db_session)

        # Unrealized = (120 - 100) * 10 = 200
        assert result.summary.total_unrealized_pl == Decimal("200")

    def test_echoes_filters_applied(self, db_session):
        """Returns filters_applied in result."""
        account = Account(name="Test", institution="Test")
        db_session.add(account)
        db_session.commit()

        result = metrics_service.get_metrics(
            db_session,
            account_ids=[account.id],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )

        assert result.filters_applied.account_ids == [account.id]
        assert result.filters_applied.start_date == date(2025, 1, 1)
        assert result.filters_applied.end_date == date(2025, 12, 31)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_metrics_service.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

Create `app/services/metrics_service.py`:

```python
"""Metrics aggregation service for analytics dashboard."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.calculations import gain_loss, pl_over_time
from app.models import Position, TradeLot
from app.services import lot_service


@dataclass
class MetricsSummary:
    """Summary statistics for portfolio performance."""

    total_realized_pl: Decimal
    total_unrealized_pl: Decimal
    win_rate: float  # 0.0 to 1.0
    total_trades: int
    winning_trades: int
    losing_trades: int


@dataclass
class PLDataPoint:
    """Single data point for P/L time series."""

    date: date
    cumulative_pl: Decimal


@dataclass
class MetricsFilter:
    """Filter parameters applied to metrics query."""

    account_ids: list[int] | None
    start_date: date | None
    end_date: date | None


@dataclass
class MetricsResult:
    """Complete metrics response with summary and time series."""

    summary: MetricsSummary
    pl_over_time: list[PLDataPoint]
    filters_applied: MetricsFilter


def get_metrics(
    db: Session,
    account_ids: list[int] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> MetricsResult:
    """
    Get portfolio metrics with optional filtering.

    Args:
        db: Database session
        account_ids: Filter to specific accounts (None = all)
        start_date: Include lots closed on/after this date
        end_date: Include lots closed on/before this date

    Returns:
        MetricsResult with summary stats and P/L time series
    """
    # Get P/L summary from lot_service (already has date filtering)
    pl_summary = lot_service.get_pl_summary(
        db,
        account_ids=account_ids,
        start_date=start_date,
        end_date=end_date,
    )

    # Get lots for time series
    query = db.query(TradeLot).filter(TradeLot.is_closed == True)  # noqa: E712
    if account_ids:
        query = query.filter(TradeLot.account_id.in_(account_ids))
    # Note: date filtering for time series would need same subquery logic
    # For MVP, we show all closed lots in time series
    lots = query.all()
    time_series = pl_over_time(lots)

    # Calculate unrealized P/L from positions
    position_query = db.query(Position)
    if account_ids:
        position_query = position_query.filter(Position.account_id.in_(account_ids))
    positions = position_query.all()

    total_unrealized = Decimal("0")
    for pos in positions:
        gl = gain_loss(pos)
        if gl is not None:
            total_unrealized += gl

    # Build result
    summary = MetricsSummary(
        total_realized_pl=pl_summary["total_pl"],
        total_unrealized_pl=total_unrealized,
        win_rate=pl_summary["win_rate"] / 100,  # Convert to 0-1 range
        total_trades=pl_summary["closed_count"],
        winning_trades=pl_summary["winners"],
        losing_trades=pl_summary["losers"],
    )

    pl_data_points = [
        PLDataPoint(date=dp["date"], cumulative_pl=dp["cumulative_pl"])
        for dp in time_series
    ]

    filters = MetricsFilter(
        account_ids=account_ids,
        start_date=start_date,
        end_date=end_date,
    )

    return MetricsResult(
        summary=summary,
        pl_over_time=pl_data_points,
        filters_applied=filters,
    )
```

**Step 4: Add to services __init__.py**

Add to `app/services/__init__.py`:

```python
from app.services import metrics_service
```

**Step 5: Run test to verify it passes**

```bash
uv run pytest tests/test_metrics_service.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add app/services/metrics_service.py tests/test_metrics_service.py app/services/__init__.py
git commit -m "feat(services): add metrics_service for analytics aggregation"
```

---

## Phase 2: Router & Navigation

### Task 2.1: Create analytics router

**Files:**
- Create: `app/routers/analytics.py`
- Modify: `app/main.py`
- Test: `tests/test_analytics.py`

**Step 1: Write the failing test**

Create `tests/test_analytics.py`:

```python
"""Tests for analytics router."""

from datetime import date
from decimal import Decimal

from app.models import Account, LotTransaction, TradeLot, Transaction


class TestAnalyticsPage:
    def test_returns_200(self, client):
        """Analytics page loads successfully."""
        response = client.get("/analytics")
        assert response.status_code == 200

    def test_shows_summary_metrics(self, client, db_session):
        """Page displays P/L summary cards."""
        account = Account(name="Test", institution="Test")
        db_session.add(account)
        db_session.flush()

        lot = TradeLot(
            account_id=account.id,
            instrument_type="STOCK",
            symbol="AAPL",
            direction="LONG",
            total_opened_quantity=Decimal("10"),
            realized_pl=Decimal("500"),
            is_closed=True,
        )
        db_session.add(lot)
        db_session.flush()

        txn = Transaction(
            account_id=account.id,
            symbol="AAPL",
            trade_date=date(2025, 1, 15),
            type="SELL",
            quantity=Decimal("10"),
        )
        db_session.add(txn)
        db_session.flush()

        leg = LotTransaction(
            trade_lot_id=lot.id,
            transaction_id=txn.id,
            allocated_quantity=Decimal("10"),
            trade_date=date(2025, 1, 15),
            is_opening=False,
        )
        db_session.add(leg)
        db_session.commit()

        response = client.get("/analytics")

        assert response.status_code == 200
        assert b"500" in response.content  # P/L value appears
        assert b"100%" in response.content  # Win rate (1/1 = 100%)

    def test_htmx_returns_partial(self, client):
        """HTMX request returns partial content only."""
        response = client.get(
            "/analytics",
            headers={"HX-Request": "true"}
        )

        assert response.status_code == 200
        # Partial should not include full HTML structure
        assert b"<!DOCTYPE html>" not in response.content
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_analytics.py -v
```

Expected: FAIL with 404

**Step 3: Create the router**

Create `app/routers/analytics.py`:

```python
"""Analytics dashboard router."""

import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.database import get_db
from app.services import account_service, metrics_service
from app.utils.htmx import htmx_response

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def parse_preset(preset: str | None) -> tuple[date | None, date | None]:
    """Convert preset name to start/end dates."""
    if not preset or preset == "all":
        return None, None

    today = date.today()

    if preset == "ytd":
        return date(today.year, 1, 1), today
    elif preset == "mtd":
        return today.replace(day=1), today
    elif preset == "90d":
        return today - timedelta(days=90), today

    return None, None


@router.get("/")
def analytics_page(
    request: Request,
    db: Session = Depends(get_db),
    account_ids: list[int] | None = Query(None, alias="account_id"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    preset: str | None = Query(None),
) -> Response:
    """Render analytics dashboard."""
    # Handle preset dates
    if preset:
        start_date, end_date = parse_preset(preset)

    # Get metrics
    metrics = metrics_service.get_metrics(
        db,
        account_ids=account_ids,
        start_date=start_date,
        end_date=end_date,
    )

    # Get accounts for filter dropdown
    accounts = account_service.get_all_accounts(db)

    # Prepare chart data as JSON
    pl_data_json = json.dumps([
        {"date": str(dp.date), "cumulative_pl": float(dp.cumulative_pl)}
        for dp in metrics.pl_over_time
    ])

    context = {
        "metrics": metrics,
        "accounts": accounts,
        "selected_account_ids": account_ids or [],
        "start_date": start_date,
        "end_date": end_date,
        "preset": preset,
        "pl_data_json": pl_data_json,
    }

    return htmx_response(
        templates=templates,
        request=request,
        full_template="analytics.html",
        partial_template="partials/analytics_content.html",
        context=context,
    )
```

**Step 4: Register router in main.py**

Add to `app/main.py`:

```python
from app.routers import analytics

app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
```

**Step 5: Run test to verify it passes**

First we need the templates (Task 3.1), so tests will fail until then. Mark this as WIP.

```bash
uv run pytest tests/test_analytics.py::TestAnalyticsPage::test_returns_200 -v
```

Expected: FAIL (template not found) - will pass after Phase 3

**Step 6: Commit router (without templates)**

```bash
git add app/routers/analytics.py app/main.py tests/test_analytics.py
git commit -m "feat(router): add analytics router skeleton"
```

---

### Task 2.2: Add navigation link

**Files:**
- Modify: `app/templates/base.html`

**Step 1: Add nav link**

In `app/templates/base.html`, add to the nav menu (after "Lots"):

```html
<li><a href="/analytics">Analytics</a></li>
```

**Step 2: Commit**

```bash
git add app/templates/base.html
git commit -m "feat(ui): add Analytics link to navigation"
```

---

## Phase 3: Templates & UI

### Task 3.1: Create analytics.html template

**Files:**
- Create: `app/templates/analytics.html`

**Step 1: Create template**

Create `app/templates/analytics.html`:

```html
{% extends "base.html" %}

{% block content %}
<div class="flex justify-between items-start mb-6">
    <h1 class="text-2xl font-bold">Analytics</h1>

    <!-- Filter Panel -->
    <div class="flex gap-4 items-center">
        <!-- Account Selector -->
        <select name="account_id" multiple
                class="select select-bordered select-sm"
                hx-get="/analytics"
                hx-target="#analytics-content"
                hx-include="[name='start_date'], [name='end_date']"
                hx-trigger="change">
            <option value="" disabled>All Accounts</option>
            {% for account in accounts %}
            <option value="{{ account.id }}"
                    {{ 'selected' if account.id in selected_account_ids }}>
                {{ account.name }}
            </option>
            {% endfor %}
        </select>

        <!-- Date Range -->
        <div class="flex gap-2 items-center">
            <input type="date" name="start_date"
                   value="{{ start_date or '' }}"
                   class="input input-bordered input-sm"
                   hx-get="/analytics"
                   hx-target="#analytics-content"
                   hx-include="[name='account_id'], [name='end_date']"
                   hx-trigger="change">
            <span class="text-sm">to</span>
            <input type="date" name="end_date"
                   value="{{ end_date or '' }}"
                   class="input input-bordered input-sm"
                   hx-get="/analytics"
                   hx-target="#analytics-content"
                   hx-include="[name='account_id'], [name='start_date']"
                   hx-trigger="change">
        </div>

        <!-- Presets -->
        <div class="btn-group">
            <button class="btn btn-sm {{ 'btn-active' if preset == 'ytd' }}"
                    hx-get="/analytics?preset=ytd"
                    hx-target="#analytics-content">YTD</button>
            <button class="btn btn-sm {{ 'btn-active' if preset == 'mtd' }}"
                    hx-get="/analytics?preset=mtd"
                    hx-target="#analytics-content">MTD</button>
            <button class="btn btn-sm {{ 'btn-active' if preset == '90d' }}"
                    hx-get="/analytics?preset=90d"
                    hx-target="#analytics-content">90 Days</button>
            <button class="btn btn-sm {{ 'btn-active' if not preset or preset == 'all' }}"
                    hx-get="/analytics?preset=all"
                    hx-target="#analytics-content">All Time</button>
        </div>
    </div>
</div>

<div id="analytics-content">
    {% include "partials/analytics_content.html" %}
</div>
{% endblock %}

{% block scripts %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
{% endblock %}
```

**Step 2: Commit**

```bash
git add app/templates/analytics.html
git commit -m "feat(templates): create analytics.html page template"
```

---

### Task 3.2: Create analytics_content.html partial

**Files:**
- Create: `app/templates/partials/analytics_content.html`

**Step 1: Create partial**

Create `app/templates/partials/analytics_content.html`:

```html
<!-- Summary Cards -->
<div class="stats shadow mb-6 w-full">
    <div class="stat">
        <div class="stat-title">Total P/L</div>
        <div class="stat-value {{ 'text-success' if metrics.summary.total_realized_pl >= 0 else 'text-error' }}">
            {{ "${:,.2f}".format(metrics.summary.total_realized_pl) }}
        </div>
        <div class="stat-desc">Realized gains/losses</div>
    </div>

    <div class="stat">
        <div class="stat-title">Win Rate</div>
        <div class="stat-value">{{ "{:.0%}".format(metrics.summary.win_rate) }}</div>
        <div class="stat-desc">
            {{ metrics.summary.winning_trades }} wins / {{ metrics.summary.losing_trades }} losses
        </div>
    </div>

    <div class="stat">
        <div class="stat-title">Total Trades</div>
        <div class="stat-value">{{ metrics.summary.total_trades }}</div>
        <div class="stat-desc">Closed positions</div>
    </div>

    <div class="stat">
        <div class="stat-title">Unrealized P/L</div>
        <div class="stat-value {{ 'text-success' if metrics.summary.total_unrealized_pl >= 0 else 'text-error' }}">
            {{ "${:,.2f}".format(metrics.summary.total_unrealized_pl) }}
        </div>
        <div class="stat-desc">Open positions</div>
    </div>
</div>

<!-- P/L Chart -->
<div class="card bg-base-100 shadow">
    <div class="card-body">
        <h2 class="card-title">P/L Over Time</h2>
        {% if metrics.pl_over_time %}
        <div class="h-80">
            <canvas id="pl-chart"></canvas>
        </div>
        <script>
            // Destroy existing chart if it exists (for HTMX swaps)
            if (window.plChart) {
                window.plChart.destroy();
            }

            const plData = {{ pl_data_json | safe }};

            if (plData.length > 0) {
                const ctx = document.getElementById('pl-chart').getContext('2d');
                const finalPL = plData[plData.length - 1].cumulative_pl;

                window.plChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: plData.map(d => d.date),
                        datasets: [{
                            label: 'Cumulative P/L',
                            data: plData.map(d => d.cumulative_pl),
                            borderColor: finalPL >= 0 ? '#22c55e' : '#ef4444',
                            backgroundColor: finalPL >= 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                            fill: true,
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                ticks: {
                                    callback: function(value) {
                                        return '$' + value.toLocaleString();
                                    }
                                }
                            }
                        }
                    }
                });
            }
        </script>
        {% else %}
        <div class="text-center py-12 text-base-content/60">
            <p>No closed trades yet. Complete some trades to see your P/L chart.</p>
        </div>
        {% endif %}
    </div>
</div>
```

**Step 2: Commit**

```bash
git add app/templates/partials/analytics_content.html
git commit -m "feat(templates): create analytics_content partial with cards and chart"
```

---

## Phase 4: Integration & Testing

### Task 4.1: Run full test suite

**Step 1: Run all tests**

```bash
uv run pytest -v
```

**Step 2: Fix any failures**

Address any test failures that arise from integration issues.

**Step 3: Run type checker**

```bash
uv run mypy app/ tests/
```

**Step 4: Run linter**

```bash
uv run ruff check . --fix
uv run ruff format .
```

**Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test and lint issues"
```

---

### Task 4.2: Manual testing

**Step 1: Start dev server**

```bash
make dev
```

**Step 2: Test scenarios**

1. Navigate to `/analytics` - verify page loads
2. Check summary cards show correct values
3. Verify chart renders with data
4. Test account filter dropdown
5. Test date range inputs
6. Test preset buttons (YTD, MTD, 90 Days, All)
7. Verify HTMX partial updates work (no full page reload)

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(analytics): complete MVP analytics dashboard

- Summary cards: Total P/L, Win Rate, Trade Count, Unrealized P/L
- P/L over time line chart with Chart.js
- Account and date range filtering
- Date presets (YTD, MTD, 90 Days, All Time)
- HTMX partial updates for smooth UX

Closes #3 (MVP scope)"
```

---

## Summary

| Phase | Tasks | Est. Steps |
|-------|-------|------------|
| Phase 1: Backend | 3 tasks | 18 steps |
| Phase 2: Router | 2 tasks | 7 steps |
| Phase 3: Templates | 2 tasks | 4 steps |
| Phase 4: Integration | 2 tasks | 10 steps |
| **Total** | **9 tasks** | **39 steps** |
