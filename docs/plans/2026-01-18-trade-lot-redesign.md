# Trade Lot Redesign

## Overview

Redesign the linking service to properly track trade lots using FIFO matching for both stocks and options.

### Problems with Current Implementation
- Only handles options, not stocks
- Creates `LinkedTrade` for single opens (confusing - nothing actually linked)
- Naming (`LinkedTrade`) doesn't reflect purpose (lot lifecycle tracking)

### Goals
- FIFO lot matching for stocks AND options
- Lot-level granularity for reporting (holding periods, per-lot P/L, tax lots)
- Only create lots when there's actual linkage (2+ opens OR any close)
- Automatic matching after sync + manual re-match option

---

## Data Model

### Renames

| Current | New |
|---------|-----|
| `LinkedTrade` | `TradeLot` |
| `LinkedTradeLeg` | `LotTransaction` |
| `linked_trades` table | `trade_lots` |
| `linked_trade_legs` table | `lot_transactions` |

### TradeLot Model

```python
class TradeLot(Base, TimestampMixin):
    """Tracks a batch of shares/contracts through open -> close lifecycle."""

    id: Mapped[int]
    account_id: Mapped[int]  # FK to accounts

    # Instrument identification
    instrument_type: Mapped[str]  # "STOCK" | "OPTION"
    symbol: Mapped[str]  # For stocks: ticker. For options: underlying

    # Option-specific (NULL for stocks)
    option_type: Mapped[str | None]  # CALL, PUT
    strike_price: Mapped[Decimal | None]
    expiration_date: Mapped[date | None]

    # Trade direction
    direction: Mapped[str]  # LONG (buy first) | SHORT (sell first)

    # Quantity tracking
    total_opened_quantity: Mapped[Decimal]
    total_closed_quantity: Mapped[Decimal]

    # Status
    is_closed: Mapped[bool]  # True when fully closed
    realized_pl: Mapped[Decimal]

    # Metadata
    is_auto_matched: Mapped[bool]
    notes: Mapped[str | None]

    # Relationships
    legs: Mapped[list["LotTransaction"]]
```

### LotTransaction Model

```python
class LotTransaction(Base, TimestampMixin):
    """Association between TradeLot and Transaction with quantity allocation."""

    id: Mapped[int]
    lot_id: Mapped[int]  # FK to trade_lots
    transaction_id: Mapped[int]  # FK to transactions

    # Partial allocation support
    allocated_quantity: Mapped[Decimal]

    # Leg type
    leg_type: Mapped[str]  # "OPEN" | "CLOSE"

    # Denormalized for display
    trade_date: Mapped[date]
    price_per_contract: Mapped[Decimal]
```

### Why Two Tables?

`LotTransaction` enables **partial allocation**. Example:

- Day 1: Buy 100 shares AAPL
- Day 2: Buy 50 shares AAPL
- Day 3: Sell 120 shares AAPL

FIFO creates:
- **Lot A:** 100 from Day 1 -> 100 closed by Day 3
- **Lot B:** 50 from Day 2 -> 20 closed by Day 3, 30 still open

Transaction #3 (sell 120) appears in BOTH lots with different `allocated_quantity` values.

---

## Matching Logic

### Position Keys

```python
# Stocks - simple
StockKey = (account_id, symbol)

# Options - full contract identifier
OptionKey = (account_id, symbol, option_type, strike_price, expiration_date)
```

### Direction Determination

| First Transaction | Direction | Opens With | Closes With |
|-------------------|-----------|------------|-------------|
| BUY (stock) | LONG | BUY | SELL |
| SELL (stock, short) | SHORT | SELL | BUY |
| BUY_TO_OPEN | LONG | BUY_TO_OPEN | SELL_TO_CLOSE |
| SELL_TO_OPEN | SHORT | SELL_TO_OPEN | BUY_TO_CLOSE |

### FIFO Algorithm (per position key)

```
1. Group all transactions by position key
2. Sort by trade_date (oldest first)
3. Separate into OPENS and CLOSES based on direction
4. Track remaining quantity per open transaction

5. For each CLOSE transaction:
   a. Find oldest OPEN with remaining quantity
   b. Allocate min(close_remaining, open_remaining)
   c. Create/update TradeLot with LotTransaction records
   d. Repeat until close fully allocated

6. For remaining OPENS (no closes yet):
   a. If 2+ opens exist for same position -> create TradeLot grouping them
   b. Single open with nothing to link -> no TradeLot created
```

### When TradeLot Gets Created

| Scenario | Create TradeLot? |
|----------|------------------|
| Single open, no close | No |
| 2+ opens for same position, no close | Yes |
| 1+ opens with any close | Yes |

---

## Integration

### Automatic After Sync

```
Sync Flow:
Sync Service -> Save new txns -> Run matching on affected positions
```

- Identify newly synced transactions
- For each new transaction's position key, re-run FIFO matching
- Only processes affected positions (not entire database)

### Manual Re-match

User triggers via UI -> deletes all existing lots -> rebuilds from scratch

Use cases:
- User manually deleted a lot and wants to fix it
- Data correction after fixing a transaction
- Reset when something looks wrong

### Service API

```python
# Called automatically after sync
def match_transactions(db: Session, transaction_ids: list[int]) -> MatchResult

# Called manually by user
def rematch_all(db: Session, account_id: int | None = None) -> MatchResult

@dataclass
class MatchResult:
    lots_created: int
    lots_updated: int
    transactions_matched: int
    transactions_unmatched: int  # single opens with nothing to link
```

---

## Migration

### Database Migration

**Step 1: Rename tables and add columns**

```sql
-- Rename tables
ALTER TABLE linked_trades RENAME TO trade_lots;
ALTER TABLE linked_trade_legs RENAME TO lot_transactions;

-- Add new column
ALTER TABLE trade_lots ADD COLUMN instrument_type VARCHAR(10);

-- Rename columns
ALTER TABLE trade_lots RENAME COLUMN underlying_symbol TO symbol;
ALTER TABLE lot_transactions RENAME COLUMN linked_trade_id TO lot_id;
```

**Step 2: Backfill**

```sql
UPDATE trade_lots SET instrument_type = 'OPTION';
```

### Code Changes

| File/Area | Changes |
|-----------|---------|
| `models/linked_trade.py` | Rename to `models/trade_lot.py` |
| `models/linked_trade_leg.py` | Rename to `models/lot_transaction.py` |
| `services/linked_trade_service.py` | Rename to `services/lot_service.py` |
| `routers/linked_trades.py` | Rename to `routers/lots.py` |
| `templates/` | Update all references |
| `services/filters.py` | Update filter classes |
| `tests/` | Update all test files |

### Data Strategy

**Full rebuild** - Delete all existing lots after migration, re-run matching from scratch. Ensures consistent FIFO across all historical data with corrected logic.

---

## Unresolved Questions

None - all design decisions validated through brainstorming session.
