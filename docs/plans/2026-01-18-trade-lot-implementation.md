# Trade Lot Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor LinkedTrade → TradeLot with FIFO matching for stocks AND options, lot-level granularity, proper lot creation rules.

**Architecture:** Rename models, add `instrument_type` field, update matching logic to handle stocks, only create lots when 2+ opens or any close exists.

**Tech Stack:** SQLAlchemy, Alembic migrations, FastAPI, pytest

---

## Task 1: Create Alembic Migration for Table Renames

**Files:**
- Create: `alembic/versions/xxxx_rename_linked_trade_to_trade_lot.py`

**Step 1: Generate migration**

Run: `cd /Users/collin/Projects/PortfolioTracker/.worktrees/trade-lot-redesign && uv run alembic revision -m "rename linked_trade to trade_lot"`

**Step 2: Write migration code**

```python
"""rename linked_trade to trade_lot

Revision ID: <auto>
Revises: <auto>
Create Date: <auto>
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '<auto>'
down_revision = '<auto>'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename tables
    op.rename_table('linked_trades', 'trade_lots')
    op.rename_table('linked_trade_legs', 'lot_transactions')

    # Rename columns in trade_lots
    with op.batch_alter_table('trade_lots') as batch_op:
        batch_op.alter_column('underlying_symbol', new_column_name='symbol')

    # Rename columns in lot_transactions
    with op.batch_alter_table('lot_transactions') as batch_op:
        batch_op.alter_column('linked_trade_id', new_column_name='lot_id')

    # Add instrument_type column
    with op.batch_alter_table('trade_lots') as batch_op:
        batch_op.add_column(sa.Column('instrument_type', sa.String(10), nullable=True))

    # Backfill existing records as OPTIONS
    op.execute("UPDATE trade_lots SET instrument_type = 'OPTION'")

    # Make column non-nullable
    with op.batch_alter_table('trade_lots') as batch_op:
        batch_op.alter_column('instrument_type', nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('trade_lots') as batch_op:
        batch_op.drop_column('instrument_type')
        batch_op.alter_column('symbol', new_column_name='underlying_symbol')

    with op.batch_alter_table('lot_transactions') as batch_op:
        batch_op.alter_column('lot_id', new_column_name='linked_trade_id')

    op.rename_table('trade_lots', 'linked_trades')
    op.rename_table('lot_transactions', 'linked_trade_legs')
```

**Step 3: Run migration**

Run: `uv run alembic upgrade head`
Expected: Migration succeeds

**Step 4: Commit**

```bash
git add alembic/
git commit -m "feat: add migration to rename linked_trade to trade_lot"
```

---

## Task 2: Rename LinkedTrade Model to TradeLot

**Files:**
- Rename: `app/models/linked_trade.py` → `app/models/trade_lot.py`
- Modify: `app/models/__init__.py`

**Step 1: Create trade_lot.py with renamed class**

```python
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.lot_transaction import LotTransaction


class TradeLot(Base, TimestampMixin):
    """Tracks a batch of shares/contracts through open -> close lifecycle."""

    __tablename__ = "trade_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)

    # Instrument type
    instrument_type: Mapped[str] = mapped_column(String(10))  # STOCK, OPTION

    # Symbol (ticker for stocks, underlying for options)
    symbol: Mapped[str] = mapped_column(String(20), index=True)

    # Option-specific (NULL for stocks)
    option_type: Mapped[str | None] = mapped_column(String(10))  # CALL, PUT
    strike_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    expiration_date: Mapped[date | None] = mapped_column(Date, index=True)

    # Trade direction: LONG (buy first) or SHORT (sell first)
    direction: Mapped[str] = mapped_column(String(10))

    # Calculated P/L
    realized_pl: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))

    # Status tracking
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    total_opened_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    total_closed_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 8), default=Decimal("0")
    )

    # Auto-match or manual
    is_auto_matched: Mapped[bool] = mapped_column(Boolean, default=True)

    # Optional user notes
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="trade_lots")
    legs: Mapped[list["LotTransaction"]] = relationship(
        back_populates="trade_lot",
        cascade="all, delete-orphan",
        order_by="LotTransaction.trade_date",
    )

    @property
    def contract_display(self) -> str:
        """Format contract for display."""
        if self.instrument_type == "STOCK":
            return self.symbol
        exp_str = self.expiration_date.strftime("%m/%d") if self.expiration_date else ""
        opt_char = "C" if self.option_type == "CALL" else "P"
        return f"{self.symbol} ${self.strike_price:.2f} {exp_str} {opt_char}"

    @property
    def remaining_quantity(self) -> Decimal:
        """Quantity still open (not yet closed)."""
        return self.total_opened_quantity - self.total_closed_quantity
```

**Step 2: Delete old file**

Run: `rm app/models/linked_trade.py`

**Step 3: Verify no import errors**

Run: `uv run python -c "from app.models.trade_lot import TradeLot; print('OK')"`
Expected: OK

**Step 4: Commit**

```bash
git add app/models/trade_lot.py
git rm app/models/linked_trade.py
git commit -m "feat: rename LinkedTrade model to TradeLot"
```

---

## Task 3: Rename LinkedTradeLeg Model to LotTransaction

**Files:**
- Rename: `app/models/linked_trade_leg.py` → `app/models/lot_transaction.py`

**Step 1: Create lot_transaction.py with renamed class**

```python
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.trade_lot import TradeLot
    from app.models.transaction import Transaction


class LotTransaction(Base, TimestampMixin):
    """Association between TradeLot and Transaction with quantity allocation."""

    __tablename__ = "lot_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lot_id: Mapped[int] = mapped_column(
        ForeignKey("trade_lots.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"), index=True
    )

    # How many shares/contracts from this transaction allocated to this lot
    allocated_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8))

    # Leg type
    leg_type: Mapped[str] = mapped_column(String(10))  # OPEN or CLOSE

    # Denormalized for display
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    price_per_contract: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    # Relationships
    trade_lot: Mapped["TradeLot"] = relationship(back_populates="legs")
    transaction: Mapped["Transaction"] = relationship(
        back_populates="lot_transactions"
    )

    @property
    def cash_impact(self) -> Decimal:
        """Calculate cash impact for this leg."""
        return self.allocated_quantity * self.price_per_contract * Decimal("100")
```

**Step 2: Delete old file**

Run: `rm app/models/linked_trade_leg.py`

**Step 3: Commit**

```bash
git add app/models/lot_transaction.py
git rm app/models/linked_trade_leg.py
git commit -m "feat: rename LinkedTradeLeg model to LotTransaction"
```

---

## Task 4: Update Model Exports and Related Models

**Files:**
- Modify: `app/models/__init__.py`
- Modify: `app/models/account.py`
- Modify: `app/models/transaction.py`

**Step 1: Update __init__.py**

```python
from app.models.account import Account
from app.models.base import Base
from app.models.comment import Comment
from app.models.lot_transaction import LotTransaction
from app.models.position import Position
from app.models.saved_filter import SavedFilter
from app.models.security import SecurityInfo
from app.models.tag import Tag, transaction_tags
from app.models.trade_lot import TradeLot
from app.models.transaction import Transaction

__all__ = [
    "Base",
    "Account",
    "Position",
    "Transaction",
    "SecurityInfo",
    "Tag",
    "Comment",
    "TradeLot",
    "LotTransaction",
    "SavedFilter",
    "transaction_tags",
]
```

**Step 2: Update account.py relationship**

Change `back_populates="linked_trades"` to `back_populates="trade_lots"` and update type hint.

**Step 3: Update transaction.py relationship**

Change `linked_trade_legs` relationship to `lot_transactions`.

**Step 4: Verify imports work**

Run: `uv run python -c "from app.models import TradeLot, LotTransaction; print('OK')"`
Expected: OK

**Step 5: Commit**

```bash
git add app/models/__init__.py app/models/account.py app/models/transaction.py
git commit -m "feat: update model exports and relationships for TradeLot"
```

---

## Task 5: Write Failing Tests for Stock Matching

**Files:**
- Modify: `tests/test_linked_trades.py` → rename to `tests/test_lot_service.py`

**Step 1: Create test for stock FIFO matching**

```python
def create_stock_transaction(
    db_session,
    account,
    symbol: str,
    txn_type: str,  # BUY or SELL
    quantity: Decimal,
    price: Decimal,
    amount: Decimal,
    trade_date: date,
    txn_id: int,
) -> Transaction:
    """Helper to create stock transaction."""
    txn = Transaction(
        snaptrade_id=f"txn-{txn_id}",
        account_id=account.id,
        symbol=symbol,
        trade_date=trade_date,
        type=txn_type,
        quantity=quantity,
        price=price,
        amount=amount,
        is_option=False,
    )
    db_session.add(txn)
    db_session.commit()
    return txn


class TestStockFIFOMatching:
    """Test FIFO matching for stocks."""

    def test_stock_buy_sell_creates_lot(self, db_session, account):
        """Buy then sell stock should create closed lot."""
        create_stock_transaction(
            db_session, account,
            symbol="AAPL",
            txn_type="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            amount=Decimal("-15000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        create_stock_transaction(
            db_session, account,
            symbol="AAPL",
            txn_type="SELL",
            quantity=Decimal("-100"),
            price=Decimal("160.00"),
            amount=Decimal("16000"),
            trade_date=date(2025, 2, 15),
            txn_id=2,
        )

        result = lot_service.match_all(db_session, account.id)
        db_session.commit()

        lots, _ = lot_service.get_all_lots(db_session)
        assert len(lots) == 1
        lot = lots[0]
        assert lot.instrument_type == "STOCK"
        assert lot.symbol == "AAPL"
        assert lot.is_closed
        assert lot.total_opened_quantity == Decimal("100")
        assert lot.total_closed_quantity == Decimal("100")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_lot_service.py::TestStockFIFOMatching::test_stock_buy_sell_creates_lot -v`
Expected: FAIL (lot_service doesn't exist yet)

**Step 3: Commit failing test**

```bash
git add tests/test_lot_service.py
git commit -m "test: add failing test for stock FIFO matching"
```

---

## Task 6: Write Failing Test for Lot Creation Rules

**Files:**
- Modify: `tests/test_lot_service.py`

**Step 1: Add test that single open does NOT create lot**

```python
class TestLotCreationRules:
    """Test when lots should/shouldn't be created."""

    def test_single_open_no_lot(self, db_session, account):
        """Single open transaction should NOT create a lot."""
        create_stock_transaction(
            db_session, account,
            symbol="AAPL",
            txn_type="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            amount=Decimal("-15000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )

        result = lot_service.match_all(db_session, account.id)
        db_session.commit()

        lots, _ = lot_service.get_all_lots(db_session)
        assert len(lots) == 0  # No lot created for single open

    def test_two_opens_creates_lot(self, db_session, account):
        """Two opens for same position should create a lot."""
        create_stock_transaction(
            db_session, account,
            symbol="AAPL",
            txn_type="BUY",
            quantity=Decimal("100"),
            price=Decimal("150.00"),
            amount=Decimal("-15000"),
            trade_date=date(2025, 1, 15),
            txn_id=1,
        )
        create_stock_transaction(
            db_session, account,
            symbol="AAPL",
            txn_type="BUY",
            quantity=Decimal("50"),
            price=Decimal("155.00"),
            amount=Decimal("-7750"),
            trade_date=date(2025, 1, 20),
            txn_id=2,
        )

        result = lot_service.match_all(db_session, account.id)
        db_session.commit()

        lots, _ = lot_service.get_all_lots(db_session)
        assert len(lots) == 1
        lot = lots[0]
        assert not lot.is_closed  # Still open
        assert lot.total_opened_quantity == Decimal("150")
        assert len(lot.legs) == 2  # Both opens linked
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_lot_service.py::TestLotCreationRules -v`
Expected: FAIL

**Step 3: Commit**

```bash
git add tests/test_lot_service.py
git commit -m "test: add failing tests for lot creation rules"
```

---

## Task 7: Rename and Refactor Lot Service

**Files:**
- Rename: `app/services/linked_trade_service.py` → `app/services/lot_service.py`

**Step 1: Create lot_service.py with updated code**

Key changes:
- Rename `LinkedTrade` → `TradeLot`, `LinkedTradeLeg` → `LotTransaction`
- Add `StockKey` alongside `ContractKey` (now `OptionKey`)
- Add `instrument_type` to lot creation
- Update lot creation logic: only create when 2+ opens OR any close

```python
"""Service for FIFO lot matching for stocks and options."""

from datetime import date
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.calculations import pl_calcs
from app.models import LotTransaction, TradeLot, Transaction
from app.services.filters import (
    LotFilter,
    PaginationParams,
    apply_lot_filters,
    apply_pagination,
)


class StockKey(NamedTuple):
    """Position key for stocks."""
    account_id: int
    symbol: str


class OptionKey(NamedTuple):
    """Position key for options."""
    account_id: int
    symbol: str
    option_type: str
    strike_price: Decimal
    expiration_date: date


# ... (full implementation follows same pattern as current linked_trade_service.py
# but with stock support and updated lot creation rules)
```

**Step 2: Delete old file**

Run: `rm app/services/linked_trade_service.py`

**Step 3: Run tests**

Run: `uv run pytest tests/test_lot_service.py -v`
Expected: Tests pass

**Step 4: Commit**

```bash
git add app/services/lot_service.py
git rm app/services/linked_trade_service.py
git commit -m "feat: rename and refactor lot_service with stock support"
```

---

## Task 8: Update Filters

**Files:**
- Modify: `app/services/filters.py`

**Step 1: Rename LinkedTradeFilter to LotFilter**

```python
@dataclass
class LotFilter:
    """Filter criteria for lot queries."""

    account_id: int | None = None
    symbol: str | None = None
    instrument_type: str | None = None  # STOCK, OPTION
    is_closed: bool | None = None


def apply_lot_filters(query: Query, filters: LotFilter) -> Query:
    """Apply LotFilter criteria to a query."""
    if filters.account_id is not None:
        query = query.filter(TradeLot.account_id == filters.account_id)

    if filters.symbol is not None:
        query = query.filter(TradeLot.symbol == filters.symbol)

    if filters.instrument_type is not None:
        query = query.filter(TradeLot.instrument_type == filters.instrument_type)

    if filters.is_closed is not None:
        query = query.filter(TradeLot.is_closed == filters.is_closed)

    return query
```

**Step 2: Run type checker**

Run: `uv run mypy app/services/filters.py`
Expected: No errors

**Step 3: Commit**

```bash
git add app/services/filters.py
git commit -m "feat: rename LinkedTradeFilter to LotFilter"
```

---

## Task 9: Update Router

**Files:**
- Rename: `app/routers/linked_trades.py` → `app/routers/lots.py`
- Modify: `app/main.py`

**Step 1: Update router with new names**

- Change service import to `lot_service`
- Change filter class to `LotFilter`
- Update template names (linked_trades.html → lots.html)
- Update variable names

**Step 2: Update main.py router registration**

Change:
```python
from app.routers import linked_trades
app.include_router(linked_trades.router, prefix="/linked-trades", tags=["linked-trades"])
```
To:
```python
from app.routers import lots
app.include_router(lots.router, prefix="/lots", tags=["lots"])
```

**Step 3: Run server to verify routes work**

Run: `uv run python run.py &`
Then: `curl http://localhost:8000/lots/`
Expected: HTML response (or redirect)

**Step 4: Commit**

```bash
git add app/routers/lots.py app/main.py
git rm app/routers/linked_trades.py
git commit -m "feat: rename linked_trades router to lots"
```

---

## Task 10: Update Templates

**Files:**
- Rename: `app/templates/linked_trades.html` → `app/templates/lots.html`
- Rename: `app/templates/linked_trade_detail.html` → `app/templates/lot_detail.html`
- Rename: `app/templates/partials/linked_trade_list.html` → `app/templates/partials/lot_list.html`
- Rename: `app/templates/partials/linked_trade_detail_content.html` → `app/templates/partials/lot_detail_content.html`
- Rename: `app/templates/partials/transaction_linked_trades.html` → `app/templates/partials/transaction_lots.html`

**Step 1: Rename files**

```bash
mv app/templates/linked_trades.html app/templates/lots.html
mv app/templates/linked_trade_detail.html app/templates/lot_detail.html
mv app/templates/partials/linked_trade_list.html app/templates/partials/lot_list.html
mv app/templates/partials/linked_trade_detail_content.html app/templates/partials/lot_detail_content.html
mv app/templates/partials/transaction_linked_trades.html app/templates/partials/transaction_lots.html
```

**Step 2: Update variable names in templates**

Replace `linked_trade` → `lot`, `linked_trades` → `lots` throughout templates.

**Step 3: Commit**

```bash
git add app/templates/
git commit -m "feat: rename linked_trade templates to lot"
```

---

## Task 11: Update Remaining Tests

**Files:**
- Modify: `tests/test_lot_service.py` (already renamed)
- Update imports and class names throughout

**Step 1: Update all test imports**

Change:
```python
from app.services import linked_trade_service
from app.services.linked_trade_service import ContractKey
```
To:
```python
from app.services import lot_service
from app.services.lot_service import OptionKey, StockKey
```

**Step 2: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add tests/
git commit -m "test: update tests for lot service rename"
```

---

## Task 12: Add Re-match Endpoint

**Files:**
- Modify: `app/routers/lots.py`
- Modify: `app/services/lot_service.py`

**Step 1: Add full rematch function to service**

```python
def rematch_all(db: Session, account_id: int | None = None) -> MatchResult:
    """Delete all lots and rebuild from scratch."""
    # Delete existing lots
    query = db.query(TradeLot)
    if account_id:
        query = query.filter(TradeLot.account_id == account_id)
    query.delete(synchronize_session=False)
    db.commit()

    # Re-run matching
    return match_all(db, account_id)
```

**Step 2: Add endpoint to router**

```python
@router.post("/rematch", response_class=HTMLResponse)
def run_full_rematch(
    request: Request,
    db: Session = Depends(get_db),
    account_id: int | None = Form(None),
):
    """Delete all lots and rebuild from scratch."""
    result = lot_service.rematch_all(db, account_id)
    # Return updated lot list...
```

**Step 3: Commit**

```bash
git add app/routers/lots.py app/services/lot_service.py
git commit -m "feat: add full rematch endpoint for lot rebuilding"
```

---

## Task 13: Integration with Sync Service

**Files:**
- Modify: `app/services/sync_service.py`

**Step 1: Call lot matching after transaction sync**

Add at end of `sync_transactions`:
```python
from app.services import lot_service

# After syncing transactions, run lot matching on affected positions
if new_transaction_ids:
    lot_service.match_transactions(db, new_transaction_ids)
```

**Step 2: Write integration test**

```python
def test_sync_triggers_lot_matching(db_session, account):
    """Syncing new transactions should auto-match lots."""
    # Mock sync that adds transactions
    # Verify lots are created automatically
```

**Step 3: Commit**

```bash
git add app/services/sync_service.py tests/
git commit -m "feat: auto-run lot matching after transaction sync"
```

---

## Task 14: Full Test Suite Verification

**Step 1: Run all tests**

Run: `uv run pytest -v`
Expected: All pass

**Step 2: Run type checker**

Run: `uv run mypy app/ tests/`
Expected: No errors

**Step 3: Run linter**

Run: `uv run ruff check .`
Expected: No errors

**Step 4: Format code**

Run: `uv run ruff format .`

**Step 5: Final commit**

```bash
git add .
git commit -m "chore: final cleanup and formatting"
```

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Alembic migration (rename tables, add instrument_type) |
| 2 | Rename LinkedTrade model → TradeLot |
| 3 | Rename LinkedTradeLeg model → LotTransaction |
| 4 | Update model exports and relationships |
| 5 | Write failing tests for stock matching |
| 6 | Write failing tests for lot creation rules |
| 7 | Rename/refactor lot_service with stock support |
| 8 | Update filters (LotFilter) |
| 9 | Update router |
| 10 | Update templates |
| 11 | Update remaining tests |
| 12 | Add rematch endpoint |
| 13 | Integration with sync service |
| 14 | Full test suite verification |
