# Filter Panel Redesign

## Overview

Redesign the transactions filter panel to show all filters at once, support multi-select with include/exclude modes, and auto-trigger on field changes.

## Requirements

- Consolidate filters — no hidden "Advanced" section
- Multi-select with include/exclude for Symbol, Type, Tag
- Chip/tag UI pattern for multi-select fields
- Auto-trigger on every change (debounced for text inputs)
- Autocomplete for Symbol, dropdown for Type/Tag

## Layout

Two-row grouped layout:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Row 1: Primary Filters                                                  │
│ ┌──────────┐ ┌─────────────────────┐ ┌──────────────────┐ ┌──────────┐ │
│ │ Search   │ │ Symbol [+] [incl ▼] │ │ Type [+] [incl▼] │ │ Account  │ │
│ │ [______] │ │ [AAPL ×] [MSFT ×]   │ │ [BUY ×] [SELL ×] │ │ [All  ▼] │ │
│ └──────────┘ └─────────────────────┘ └──────────────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ Row 2: Refinement Filters                                               │
│ ┌────────────┐ ┌────────────┐ ┌─────────────────┐ ┌──────────────────┐ │
│ │ From       │ │ To         │ │ Options Group   │ │ Tag [+] [incl ▼] │ │
│ │ [date    ] │ │ [date    ] │ │ [All▼][C/P▼][A▼]│ │ [Wheel ×]        │ │
│ └────────────┘ └────────────┘ └─────────────────┘ └──────────────────┘ │
│                                                          [Clear All]   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Chip Multi-Select Component

Structure per filter:
- Label + include/exclude dropdown toggle
- Chip container with inline input
- Chips colored by mode (green=include, red=exclude)

Adding chips:
- Symbol: autocomplete input, fetches from `/api/symbols?q=`
- Type/Tag: click shows dropdown of available options

Removing chips: click × on chip

Query string format:
```
symbol=AAPL&symbol=MSFT&symbol_mode=include
type=BUY&type=SELL&type_mode=exclude
```

## Auto-Trigger Behavior

| Input | Event | Debounce |
|-------|-------|----------|
| Search text | `input` | 300ms |
| Symbol autocomplete | `input` | 300ms |
| Chip add/remove | immediate | none |
| Include/Exclude toggle | `change` | none |
| Account dropdown | `change` | none |
| Date inputs | `change` | none |
| Options dropdowns | `change` | none |

Implementation:
- Inputs dispatch custom `filterChanged` event to `document.body`
- Form uses `hx-trigger="filterChanged from:body"`
- Text inputs use debounce helper before dispatching

## Backend Changes

Update `TransactionFilter`:
```python
# Multi-value with mode
symbols: list[str] | None = None
symbol_mode: Literal["include", "exclude"] = "include"

types: list[str] | None = None
type_mode: Literal["include", "exclude"] = "include"

tag_ids: list[int] | None = None
tag_mode: Literal["include", "exclude"] = "include"
```

Query building:
```python
if filters.symbols and filters.symbol_mode == "include":
    query = query.filter(Transaction.symbol.in_(filters.symbols))
elif filters.symbols and filters.symbol_mode == "exclude":
    query = query.filter(Transaction.symbol.notin_(filters.symbols))
```

Backward compatibility: single `symbol=X` treated as `symbols=[X]` with include mode.

## Files to Modify

| File | Changes |
|------|---------|
| `app/templates/transactions.html` | New two-row layout, chip components, HTMX triggers |
| `app/templates/partials/chip_multiselect.html` | New reusable component |
| `app/services/filters.py` | Update `TransactionFilter` for multi-value fields |
| `app/routers/transactions.py` | Parse list params, update query string builder |
| `app/services/transaction_service.py` | Update query building for IN/NOT IN |
| `app/routers/api.py` | Add `/api/symbols` autocomplete endpoint |

## Testing

- Update existing filter tests for new param format
- Add tests for include/exclude modes
- Add tests for multi-value combinations
- Manual test saved filter backward compatibility
