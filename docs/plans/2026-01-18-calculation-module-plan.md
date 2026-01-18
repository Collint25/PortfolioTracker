# Calculation Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract position and P/L calculations from services into dedicated `app/calculations/` module.

**Architecture:** Create two pure-function modules (`position_calcs.py`, `pl_calcs.py`) that take model objects as input and return calculated values. Services delegate math to these modules while retaining database access.

**Tech Stack:** Python, Decimal, SQLAlchemy models (Position, LinkedTrade)

---

## Task 1: Create position_calcs.py with Tests

**Files:**
- Create: `app/calculations/__init__.py` (empty initially)
- Create: `app/calculations/position_calcs.py`
- Create: `tests/test_calculations/__init__.py`
- Create: `tests/test_calculations/test_position_calcs.py`

**Step 1: Create directory structure**

```bash
mkdir -p app/calculations tests/test_calculations
touch app/calculations/__init__.py tests/test_calculations/__init__.py
```

**Step 2: Write failing tests for position calculations**

Create `tests/test_calculations/test_position_calcs.py`:

```python
"""Tests for position calculation functions."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.calculations import position_calcs


@pytest.fixture
def position():
    """Create a mock position with typical values."""
    pos = MagicMock()
    pos.quantity = Decimal("100")
    pos.current_price = Decimal("50.00")
    pos.average_cost = Decimal("45.00")
    pos.previous_close = Decimal("48.00")
    return pos


class TestMarketValue:
    def test_calculates_quantity_times_price(self, position):
        result = position_calcs.market_value(position)
        assert result == Decimal("5000.00")

    def test_returns_none_when_price_missing(self, position):
        position.current_price = None
        assert position_calcs.market_value(position) is None


class TestCostBasis:
    def test_calculates_quantity_times_average_cost(self, position):
        result = position_calcs.cost_basis(position)
        assert result == Decimal("4500.00")

    def test_returns_none_when_average_cost_missing(self, position):
        position.average_cost = None
        assert position_calcs.cost_basis(position) is None


class TestGainLoss:
    def test_calculates_market_value_minus_cost_basis(self, position):
        result = position_calcs.gain_loss(position)
        assert result == Decimal("500.00")

    def test_returns_none_when_price_missing(self, position):
        position.current_price = None
        assert position_calcs.gain_loss(position) is None

    def test_returns_none_when_average_cost_missing(self, position):
        position.average_cost = None
        assert position_calcs.gain_loss(position) is None


class TestGainLossPercent:
    def test_calculates_percentage(self, position):
        # gain_loss = 500, cost_basis = 4500
        # 500 / 4500 * 100 = 11.111...
        result = position_calcs.gain_loss_percent(position)
        assert result is not None
        assert abs(result - Decimal("11.111")) < Decimal("0.001")

    def test_returns_none_when_cost_basis_zero(self, position):
        position.average_cost = Decimal("0")
        assert position_calcs.gain_loss_percent(position) is None

    def test_returns_none_when_values_missing(self, position):
        position.current_price = None
        assert position_calcs.gain_loss_percent(position) is None


class TestDailyChange:
    def test_calculates_price_diff_times_quantity(self, position):
        # (50 - 48) * 100 = 200
        result = position_calcs.daily_change(position)
        assert result == Decimal("200.00")

    def test_returns_none_when_current_price_missing(self, position):
        position.current_price = None
        assert position_calcs.daily_change(position) is None

    def test_returns_none_when_previous_close_missing(self, position):
        position.previous_close = None
        assert position_calcs.daily_change(position) is None


class TestDailyChangePercent:
    def test_calculates_percentage(self, position):
        # (50 - 48) / 48 * 100 = 4.166...
        result = position_calcs.daily_change_percent(position)
        assert result is not None
        assert abs(result - Decimal("4.166")) < Decimal("0.001")

    def test_returns_none_when_previous_close_zero(self, position):
        position.previous_close = Decimal("0")
        assert position_calcs.daily_change_percent(position) is None

    def test_returns_none_when_values_missing(self, position):
        position.previous_close = None
        assert position_calcs.daily_change_percent(position) is None
```

**Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/test_calculations/test_position_calcs.py -v
```

Expected: ImportError - module `app.calculations.position_calcs` not found

**Step 4: Implement position_calcs.py**

Create `app/calculations/position_calcs.py`:

```python
"""Pure calculation functions for position metrics."""

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Position


def market_value(position: "Position") -> Decimal | None:
    """Calculate market value (quantity * current_price)."""
    if position.current_price is None:
        return None
    return position.quantity * position.current_price


def cost_basis(position: "Position") -> Decimal | None:
    """Calculate total cost basis (quantity * average_cost)."""
    if position.average_cost is None:
        return None
    return position.quantity * position.average_cost


def gain_loss(position: "Position") -> Decimal | None:
    """Calculate unrealized gain/loss (market_value - cost_basis)."""
    mv = market_value(position)
    cb = cost_basis(position)
    if mv is None or cb is None:
        return None
    return mv - cb


def gain_loss_percent(position: "Position") -> Decimal | None:
    """Calculate unrealized gain/loss as percentage."""
    gl = gain_loss(position)
    cb = cost_basis(position)
    if gl is None or cb is None or cb == 0:
        return None
    return (gl / cb) * 100


def daily_change(position: "Position") -> Decimal | None:
    """Calculate daily change in dollars."""
    if position.current_price is None or position.previous_close is None:
        return None
    return (position.current_price - position.previous_close) * position.quantity


def daily_change_percent(position: "Position") -> Decimal | None:
    """Calculate daily change as percentage."""
    if position.current_price is None or position.previous_close is None:
        return None
    if position.previous_close == 0:
        return None
    return (
        (position.current_price - position.previous_close) / position.previous_close
    ) * 100
```

**Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/test_calculations/test_position_calcs.py -v
```

Expected: All tests pass

**Step 6: Run linting and type checks**

```bash
uv run ruff check app/calculations tests/test_calculations
uv run mypy app/calculations tests/test_calculations
```

**Step 7: Commit**

```bash
git add app/calculations tests/test_calculations
git commit -m "feat: add position_calcs module with tests"
```

---

## Task 2: Create pl_calcs.py with linked_trade_pl

**Files:**
- Create: `app/calculations/pl_calcs.py`
- Create: `tests/test_calculations/test_pl_calcs.py`

**Step 1: Write failing tests for linked_trade_pl**

Create `tests/test_calculations/test_pl_calcs.py`:

```python
"""Tests for P/L calculation functions."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.calculations import pl_calcs


def make_leg(allocated_qty: str, txn_qty: str, txn_amount: str) -> MagicMock:
    """Create a mock LinkedTradeLeg."""
    leg = MagicMock()
    leg.allocated_quantity = Decimal(allocated_qty)
    leg.transaction = MagicMock()
    leg.transaction.quantity = Decimal(txn_qty)
    leg.transaction.amount = Decimal(txn_amount)
    return leg


class TestLinkedTradePl:
    def test_sums_proportioned_amounts(self):
        """P/L sums transaction amounts proportioned by allocated quantity."""
        linked_trade = MagicMock()
        # Leg 1: allocated 10 of 10, amount = -500 (paid $500)
        # Leg 2: allocated 10 of 10, amount = +650 (received $650)
        # Total P/L = -500 + 650 = 150
        linked_trade.legs = [
            make_leg("10", "10", "-500"),
            make_leg("10", "10", "650"),
        ]

        result = pl_calcs.linked_trade_pl(linked_trade)
        assert result == Decimal("150")

    def test_handles_partial_allocation(self):
        """Correctly proportions when leg uses partial transaction quantity."""
        linked_trade = MagicMock()
        # Leg uses 5 of 10 contracts from a -1000 transaction
        # Proportioned amount = -1000 * (5/10) = -500
        linked_trade.legs = [make_leg("5", "10", "-1000")]

        result = pl_calcs.linked_trade_pl(linked_trade)
        assert result == Decimal("-500")

    def test_handles_missing_amount(self):
        """Skips legs where transaction has no amount."""
        linked_trade = MagicMock()
        leg = make_leg("10", "10", "100")
        leg.transaction.amount = None
        linked_trade.legs = [leg]

        result = pl_calcs.linked_trade_pl(linked_trade)
        assert result == Decimal("0")

    def test_empty_legs_returns_zero(self):
        """Returns zero for trade with no legs."""
        linked_trade = MagicMock()
        linked_trade.legs = []

        result = pl_calcs.linked_trade_pl(linked_trade)
        assert result == Decimal("0")
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_calculations/test_pl_calcs.py::TestLinkedTradePl -v
```

Expected: ImportError - module `app.calculations.pl_calcs` not found

**Step 3: Implement linked_trade_pl**

Create `app/calculations/pl_calcs.py`:

```python
"""Pure calculation functions for trade P/L metrics."""

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import LinkedTrade


def linked_trade_pl(linked_trade: "LinkedTrade") -> Decimal:
    """
    Calculate realized P/L for a linked trade.

    P/L = sum of all transaction amounts, proportioned by allocated quantity.
    Positive amount = credit (received money), negative = debit (paid money).
    """
    total_pl = Decimal("0")

    for leg in linked_trade.legs:
        txn = leg.transaction
        if txn and txn.amount:
            txn_qty = abs(txn.quantity) if txn.quantity else Decimal("1")
            if txn_qty > 0:
                proportion = leg.allocated_quantity / txn_qty
                total_pl += txn.amount * proportion

    return total_pl
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_calculations/test_pl_calcs.py::TestLinkedTradePl -v
```

Expected: All tests pass

**Step 5: Commit**

```bash
git add app/calculations/pl_calcs.py tests/test_calculations/test_pl_calcs.py
git commit -m "feat: add linked_trade_pl to pl_calcs module"
```

---

## Task 3: Add pl_summary to pl_calcs

**Files:**
- Modify: `app/calculations/pl_calcs.py`
- Modify: `tests/test_calculations/test_pl_calcs.py`

**Step 1: Write failing tests for pl_summary**

Append to `tests/test_calculations/test_pl_calcs.py`:

```python
def make_linked_trade(realized_pl: str, is_closed: bool) -> MagicMock:
    """Create a mock LinkedTrade for summary tests."""
    lt = MagicMock()
    lt.realized_pl = Decimal(realized_pl)
    lt.is_closed = is_closed
    lt.legs = []  # Not needed for summary
    return lt


class TestPlSummary:
    def test_calculates_total_pl(self):
        """Sums realized P/L from closed trades."""
        trades = [
            make_linked_trade("100", is_closed=True),
            make_linked_trade("-50", is_closed=True),
        ]

        result = pl_calcs.pl_summary(trades)
        assert result["total_pl"] == Decimal("50")

    def test_counts_winners_and_losers(self):
        """Categorizes closed trades by P/L sign."""
        trades = [
            make_linked_trade("100", is_closed=True),  # winner
            make_linked_trade("-50", is_closed=True),  # loser
            make_linked_trade("200", is_closed=True),  # winner
        ]

        result = pl_calcs.pl_summary(trades)
        assert result["winners"] == 2
        assert result["losers"] == 1

    def test_calculates_win_rate(self):
        """Win rate = winners / closed_count * 100."""
        trades = [
            make_linked_trade("100", is_closed=True),
            make_linked_trade("-50", is_closed=True),
        ]

        result = pl_calcs.pl_summary(trades)
        assert result["win_rate"] == 50.0

    def test_counts_open_and_closed(self):
        """Separately counts open and closed trades."""
        trades = [
            make_linked_trade("0", is_closed=False),  # open
            make_linked_trade("100", is_closed=True),  # closed
        ]

        result = pl_calcs.pl_summary(trades)
        assert result["open_count"] == 1
        assert result["closed_count"] == 1

    def test_excludes_open_trades_from_pl(self):
        """Open trades don't contribute to total P/L."""
        trades = [
            make_linked_trade("999", is_closed=False),  # open - ignored
            make_linked_trade("100", is_closed=True),
        ]

        result = pl_calcs.pl_summary(trades)
        assert result["total_pl"] == Decimal("100")

    def test_empty_list_returns_zeros(self):
        """Handles empty trade list gracefully."""
        result = pl_calcs.pl_summary([])

        assert result["total_pl"] == Decimal("0")
        assert result["winners"] == 0
        assert result["losers"] == 0
        assert result["win_rate"] == 0
        assert result["open_count"] == 0
        assert result["closed_count"] == 0
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_calculations/test_pl_calcs.py::TestPlSummary -v
```

Expected: AttributeError - `pl_calcs` has no attribute `pl_summary`

**Step 3: Implement pl_summary**

Add to `app/calculations/pl_calcs.py`:

```python
def pl_summary(linked_trades: list["LinkedTrade"]) -> dict:
    """
    Calculate P/L summary statistics from a list of linked trades.

    Returns dict with: total_pl, winners, losers, win_rate, open_count, closed_count
    """
    total_pl = Decimal("0")
    winners = 0
    losers = 0
    open_count = 0
    closed_count = 0

    for lt in linked_trades:
        if lt.is_closed:
            closed_count += 1
            total_pl += lt.realized_pl
            if lt.realized_pl > 0:
                winners += 1
            elif lt.realized_pl < 0:
                losers += 1
        else:
            open_count += 1

    win_rate = (winners / closed_count * 100) if closed_count > 0 else 0

    return {
        "total_pl": total_pl,
        "winners": winners,
        "losers": losers,
        "win_rate": win_rate,
        "open_count": open_count,
        "closed_count": closed_count,
    }
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_calculations/test_pl_calcs.py -v
```

Expected: All tests pass

**Step 5: Run linting and type checks**

```bash
uv run ruff check app/calculations tests/test_calculations
uv run mypy app/calculations
```

**Step 6: Commit**

```bash
git add app/calculations/pl_calcs.py tests/test_calculations/test_pl_calcs.py
git commit -m "feat: add pl_summary to pl_calcs module"
```

---

## Task 4: Create __init__.py with Re-exports

**Files:**
- Modify: `app/calculations/__init__.py`

**Step 1: Add re-exports**

Update `app/calculations/__init__.py`:

```python
"""Calculation modules for position metrics and P/L analysis."""

from app.calculations.pl_calcs import linked_trade_pl, pl_summary
from app.calculations.position_calcs import (
    cost_basis,
    daily_change,
    daily_change_percent,
    gain_loss,
    gain_loss_percent,
    market_value,
)

__all__ = [
    # Position calculations
    "market_value",
    "cost_basis",
    "gain_loss",
    "gain_loss_percent",
    "daily_change",
    "daily_change_percent",
    # P/L calculations
    "linked_trade_pl",
    "pl_summary",
]
```

**Step 2: Verify imports work**

```bash
uv run python -c "from app.calculations import market_value, linked_trade_pl; print('OK')"
```

Expected: prints `OK`

**Step 3: Commit**

```bash
git add app/calculations/__init__.py
git commit -m "feat: add re-exports to calculations __init__.py"
```

---

## Task 5: Update position_service.py

**Files:**
- Modify: `app/services/position_service.py`

**Step 1: Update imports and delegate to calculations module**

Replace `app/services/position_service.py` contents:

```python
"""Position service for querying and aggregating position data."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.calculations import position_calcs
from app.models import Position


def get_positions_by_account(db: Session, account_id: int) -> list[Position]:
    """Get all positions for an account, ordered by symbol."""
    return (
        db.query(Position)
        .filter(Position.account_id == account_id)
        .order_by(Position.symbol)
        .all()
    )


def get_position_summary(position: Position) -> dict:
    """Get position with calculated fields."""
    return {
        "position": position,
        "market_value": position_calcs.market_value(position),
        "cost_basis": position_calcs.cost_basis(position),
        "gain_loss": position_calcs.gain_loss(position),
        "gain_loss_percent": position_calcs.gain_loss_percent(position),
        "daily_change": position_calcs.daily_change(position),
        "daily_change_percent": position_calcs.daily_change_percent(position),
    }


def get_account_positions_summary(
    db: Session, account_id: int
) -> tuple[list[dict], dict]:
    """
    Get all positions for an account with calculated fields.

    Returns:
        Tuple of (positions list, totals dict)
    """
    positions = get_positions_by_account(db, account_id)
    summaries = [get_position_summary(p) for p in positions]

    # Calculate totals
    total_market_value = Decimal("0")
    total_cost_basis = Decimal("0")
    total_daily_change = Decimal("0")
    total_previous_value = Decimal("0")
    has_daily_data = False

    for s in summaries:
        if s["market_value"] is not None:
            total_market_value += s["market_value"]
        if s["cost_basis"] is not None:
            total_cost_basis += s["cost_basis"]
        if s["daily_change"] is not None:
            total_daily_change += s["daily_change"]
            has_daily_data = True
        # Track previous value for accurate percent calculation
        if s["position"].previous_close is not None and s["position"].quantity:
            total_previous_value += (
                s["position"].previous_close * s["position"].quantity
            )

    total_gain_loss = total_market_value - total_cost_basis
    total_gain_loss_percent = (
        (total_gain_loss / total_cost_basis) * 100 if total_cost_basis != 0 else None
    )

    # Daily change percent based on previous value
    total_daily_change_percent = (
        (total_daily_change / total_previous_value) * 100
        if has_daily_data and total_previous_value != 0
        else None
    )

    totals = {
        "market_value": total_market_value,
        "cost_basis": total_cost_basis,
        "gain_loss": total_gain_loss,
        "gain_loss_percent": total_gain_loss_percent,
        "daily_change": total_daily_change if has_daily_data else None,
        "daily_change_percent": total_daily_change_percent,
    }

    return summaries, totals
```

**Step 2: Run existing tests**

```bash
uv run pytest tests/ -v -k "position"
```

Expected: All tests pass

**Step 3: Run linting and type checks**

```bash
uv run ruff check app/services/position_service.py
uv run mypy app/services/position_service.py
```

**Step 4: Commit**

```bash
git add app/services/position_service.py
git commit -m "refactor: delegate position calcs to calculations module"
```

---

## Task 6: Update linked_trade_service.py

**Files:**
- Modify: `app/services/linked_trade_service.py`

**Step 1: Update P/L functions to use calculations module**

In `app/services/linked_trade_service.py`, make these changes:

Add import at top (after existing imports):

```python
from app.calculations import pl_calcs
```

Replace `calculate_linked_trade_pl` function (around line 429):

```python
def calculate_linked_trade_pl(db: Session, linked_trade_id: int) -> Decimal:
    """
    Calculate realized P/L for a linked trade.

    Loads the trade and delegates to pl_calcs module.
    """
    linked_trade = get_linked_trade_by_id(db, linked_trade_id)
    if not linked_trade:
        return Decimal("0")
    return pl_calcs.linked_trade_pl(linked_trade)
```

Replace `get_pl_summary` function (around line 472):

```python
def get_pl_summary(db: Session, account_id: int | None = None) -> dict:
    """Get P/L summary statistics."""
    query = db.query(LinkedTrade)

    if account_id is not None:
        query = query.filter(LinkedTrade.account_id == account_id)

    return pl_calcs.pl_summary(query.all())
```

**Step 2: Run existing tests**

```bash
uv run pytest tests/ -v -k "linked"
```

Expected: All tests pass

**Step 3: Run linting and type checks**

```bash
uv run ruff check app/services/linked_trade_service.py
uv run mypy app/services/linked_trade_service.py
```

**Step 4: Commit**

```bash
git add app/services/linked_trade_service.py
git commit -m "refactor: delegate P/L calcs to calculations module"
```

---

## Task 7: Final Verification

**Step 1: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: All tests pass

**Step 2: Run all linting and type checks**

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app/ tests/
```

Expected: No errors

**Step 3: Start dev server and smoke test**

```bash
uv run python run.py
```

- Open browser to positions page - verify calculations display
- Open browser to linked trades page - verify P/L displays

**Step 4: Final commit if any fixes needed**

```bash
git status
# If clean, proceed to PR
```

---

## Summary

| Task | Files Changed | Purpose |
|------|---------------|---------|
| 1 | +position_calcs.py, +test_position_calcs.py | Core position calculations |
| 2 | +pl_calcs.py, +test_pl_calcs.py | linked_trade_pl function |
| 3 | pl_calcs.py, test_pl_calcs.py | pl_summary function |
| 4 | __init__.py | Clean imports |
| 5 | position_service.py | Delegate to calculations |
| 6 | linked_trade_service.py | Delegate to calculations |
| 7 | - | Verification |
