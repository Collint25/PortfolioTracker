# Calculation Module Extraction

## Overview

Extract calculations from services into dedicated `app/calculations/` module. Improves testability and separation of concerns.

## Structure

```
app/
  calculations/
    __init__.py          # Re-exports
    position_calcs.py    # Position metrics
    pl_calcs.py          # P/L calculations
```

## Functions

### position_calcs.py

All take `Position`, return `Decimal | None`:

- `market_value(position)` — quantity × current_price
- `cost_basis(position)` — quantity × average_cost
- `gain_loss(position)` — market_value - cost_basis
- `gain_loss_percent(position)` — (gain_loss / cost_basis) × 100
- `daily_change(position)` — (current_price - previous_close) × quantity
- `daily_change_percent(position)` — ((current - prev) / prev) × 100

### pl_calcs.py

- `linked_trade_pl(linked_trade: LinkedTrade) -> Decimal` — sum of proportioned transaction amounts
- `pl_summary(linked_trades: list[LinkedTrade]) -> dict` — aggregate stats (total_pl, winners, losers, win_rate, open_count, closed_count)

## Design Decisions

- **Two modules** — Position calcs and P/L calcs are separate domains with different input types
- **Pure functions** — No database access, no shared state. All inputs via parameters.
- **Model objects as input** — Functions receive `Position` or `LinkedTrade`, not primitives. Caller handles data loading.
- **No `calculate_` prefix** — Module name (`calculations`) conveys intent; keeps call sites clean

## Service Changes

### position_service.py

```python
from app.calculations import position_calcs

def get_position_summary(position: Position) -> dict:
    return {
        "position": position,
        "market_value": position_calcs.market_value(position),
        "cost_basis": position_calcs.cost_basis(position),
        # ...
    }
```

Delete 6 `calculate_*` functions from this file.

### linked_trade_service.py

```python
from app.calculations import pl_calcs

def calculate_linked_trade_pl(db: Session, linked_trade_id: int) -> Decimal:
    linked_trade = get_linked_trade_by_id(db, linked_trade_id)
    if not linked_trade:
        return Decimal("0")
    return pl_calcs.linked_trade_pl(linked_trade)

def get_pl_summary(db: Session, account_id: int | None = None) -> dict:
    query = db.query(LinkedTrade)
    if account_id is not None:
        query = query.filter(LinkedTrade.account_id == account_id)
    return pl_calcs.pl_summary(query.all())
```

## Testing

```
tests/
  test_calculations/
    __init__.py
    test_position_calcs.py
    test_pl_calcs.py
```

Unit tests require no database — create model objects in memory:

```python
def test_market_value():
    position = Position(quantity=Decimal("10"), current_price=Decimal("50"))
    assert position_calcs.market_value(position) == Decimal("500")

def test_linked_trade_pl():
    linked_trade = LinkedTrade(legs=[...])
    assert pl_calcs.linked_trade_pl(linked_trade) == Decimal("150.00")
```

## Implementation Order

1. **Create calculation modules** (additive)
   - Create `app/calculations/` directory
   - Add `position_calcs.py`, `pl_calcs.py`, `__init__.py`
   - Write unit tests

2. **Update services** (swap)
   - Import and call calculation functions
   - Delete duplicated functions from services

3. **Verify**
   - Run existing tests
   - Run new calculation tests
