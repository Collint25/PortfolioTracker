# Implementation Notes

Detailed implementation notes, file changes, and testing checklists for each phase.

---

## Phase 5: Trade Groups (Multi-leg)

**Files created:**
- `app/models/trade_group.py` - TradeGroup model + M2M association table
- `app/services/trade_group_service.py` - CRUD, P/L calc, auto-grouping logic
- `app/routers/trade_groups.py` - All endpoints under /trade-groups
- `app/templates/trade_groups.html` - Main list page
- `app/templates/trade_group_detail.html` - Detail/edit page
- `app/templates/partials/trade_group_*.html` - Various partials
- `alembic/versions/1b71213d8c1a_add_trade_groups.py` - Migration
- `tests/test_trade_groups.py` - 14 tests

**Files modified:**
- `app/models/__init__.py` - Export TradeGroup
- `app/models/transaction.py` - Added trade_groups relationship
- `app/main.py` - Registered trade_groups router
- `app/templates/base.html` - Added nav link
- `app/templates/transaction_detail.html` - Added trade groups section

**Strategy types:** vertical_spread, iron_condor, iron_butterfly, straddle, strangle, calendar_spread, diagonal_spread, covered_call, protective_put, collar, custom

---

## Phase 6: Logging & SnapTrade API Update

**Files created:**
- `app/logging_config.py` - Logging setup with stdout handler

**Files modified:**
- `app/main.py` - Import and call `configure_logging()` at startup
- `app/services/snaptrade_client.py` - Added `fetch_account_activities()` with pagination
- `app/services/sync_service.py` - Per-account activity fetching

**Key changes:**
- Replaced deprecated `get_activities()` with `account_information.get_account_activities()`
- Per-account endpoint returns `{"data": [...], "pagination": {...}}`
- Pagination handled internally with offset/limit (1000 per request)

---

## Phase 7: Positions View

**Files created:**
- `app/services/position_service.py` - Position queries and calculations
- `app/templates/account_positions.html` - Positions page with summary cards
- `app/templates/partials/position_list.html` - Positions table partial
- `tests/test_positions.py` - 8 tests

**Files modified:**
- `app/routers/accounts.py` - Added `/{account_id}/positions` route
- `app/main.py` - Changed accounts prefix from `/api/accounts` to `/accounts`

---

## Phase 7.5: Option Support

**Option data from SnapTrade:**
- `option_symbol` object: ticker, strike_price, expiration_date, option_type (CALL/PUT), underlying_symbol
- `option_type` at root level: BUY_TO_OPEN, BUY_TO_CLOSE, SELL_TO_OPEN, SELL_TO_CLOSE
- 892 option transactions identified

**Files created:**
- `alembic/versions/a7f3c2d5e8b1_add_option_support.py`
- `scripts/backfill_options.py` - Backfill script for existing transactions
- `tests/test_options.py` - 7 tests

**Files modified:**
- `app/models/transaction.py` - Added: is_option, option_type, strike_price, expiration_date, option_ticker, underlying_symbol, option_action
- `app/models/position.py` - Added same option fields
- `app/services/sync_service.py` - Added _extract_option_data(), _sync_option_position()
- `app/services/snaptrade_client.py` - Added fetch_option_holdings()
- `app/services/transaction_service.py` - Added option filters
- `app/routers/transactions.py` - Added option query params
- `app/templates/transactions.html` - Added option filter dropdowns
- `app/templates/partials/transaction_table.html` - Show option details
- `app/templates/transaction_detail.html` - Added Option Details section

---

## Phase 8: Linked Trades - Data Model

**LinkedTrade Model:**
```
id, account_id (FK)
underlying_symbol, option_type, strike_price, expiration_date
direction (LONG/SHORT)
realized_pl, is_closed
total_opened_quantity, total_closed_quantity
is_auto_matched, notes
```

**LinkedTradeLeg Model:**
```
id, linked_trade_id (FK), transaction_id (FK)
allocated_quantity (enables partial closes)
leg_type (OPEN/CLOSE)
trade_date, price_per_contract
```

**Files created:**
- `app/models/linked_trade.py`
- `app/models/linked_trade_leg.py`
- `alembic/versions/b8c4d6e9f0a2_add_linked_trades.py`

**Files modified:**
- `app/models/__init__.py` - Export new models
- `app/models/transaction.py` - Added `linked_trade_legs` relationship
- `app/models/account.py` - Added `linked_trades` relationship

---

## Phase 8.1: Linked Trades - FIFO Matching

**FIFO Algorithm:**
```
Match by contract identity: (account_id, underlying_symbol, option_type, strike_price, expiration_date)

For each unique contract:
  1. Get all opening transactions ordered by (trade_date, id)
  2. Get all closing transactions ordered by (trade_date, id)
  3. Track remaining quantity per opening transaction
  4. For each close: allocate to oldest open with remaining qty (FIFO)
  5. Calculate realized P/L = sum(close amounts) + sum(open amounts)
```

**Direction Mapping:**
- LONG: BUY_TO_OPEN → SELL_TO_CLOSE
- SHORT: SELL_TO_OPEN → BUY_TO_CLOSE

**Files created:**
- `app/services/linked_trade_service.py`
- `tests/test_linked_trades.py` - 7 tests

**Results from real data:**
- 472 linked trades from 298 unique contracts
- Total P/L: $5,948.86
- Win Rate: 51.2% (216 winners, 206 losers)

---

## Phase 8.2: Linked Trades - API & UI

**API Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/linked-trades` | List with filters |
| GET | `/linked-trades/{id}` | Detail view |
| POST | `/linked-trades/auto-match` | Run FIFO matching |
| DELETE | `/linked-trades/{id}` | Unlink trade |
| GET | `/linked-trades/transaction/{id}` | Linked trades for a transaction |

**Files created:**
- `app/routers/linked_trades.py`
- `app/templates/linked_trades.html`
- `app/templates/linked_trade_detail.html`
- `app/templates/partials/linked_trade_list.html`
- `app/templates/partials/transaction_linked_trades.html`

**Files modified:**
- `app/main.py` - Register router
- `app/templates/base.html` - Add nav link
- `app/templates/transaction_detail.html` - Add linked trades section

---

## Phase 9: Account Cards with Market Value

**Files created:**
- `alembic/versions/c9d5e7f1a3b4_add_previous_close.py` - Migration for previous_close column
- `app/templates/partials/account_card.html` - Account card with market value and daily change

**Files modified:**
- `app/models/position.py` - Added `previous_close` column
- `app/services/market_data_service.py` - Updated `get_quote()` to return (current_price, previous_close) tuple, updated `refresh_position_prices()` to store both values
- `app/services/position_service.py` - Added `calculate_daily_change()`, `calculate_daily_change_percent()`, updated summaries to include daily change totals
- `app/services/account_service.py` - Added `get_all_accounts_with_totals()` function
- `app/routers/accounts.py` - Updated `list_accounts()` to use accounts_with_totals
- `app/templates/partials/account_list.html` - Updated to iterate over `item` dicts and include account_card partial

**Key changes:**
- Finnhub `pc` field now captured as `previous_close` on Position model
- Account cards display: market value, daily $ change, daily % change
- Position summaries include daily change calculations at individual and aggregate level

---

## Phase 9.1: Dashboard Enhancement

**Files created:**
- `app/templates/partials/position_list_compact.html` - Compact position table for inline expansion

**Files modified:**
- `app/routers/pages.py` - Added `get_all_accounts_with_totals()`, portfolio totals calculation, `/accounts/{id}/positions-inline` route
- `app/templates/index.html` - Replaced hero section with account cards grid, portfolio summary, expandable positions

**Key changes:**
- Account cards display market value and daily G/L with % change
- Portfolio-wide totals at top of page
- Click "Positions" to expand inline position table via HTMX
- "Details" button links to full positions page

---

## Phase 9.2: Filter Consolidation

**Files modified:**
- `app/templates/transactions.html` - Reorganized filter UI with:
  - Compact horizontal layout with flex-wrap
  - Primary filters always visible (search, account, symbol, type, dates)
  - "More" button to toggle advanced filters
  - Advanced section with options group (is_option, call/put, action) and tags
  - "Clear All" link to reset filters

---

## Phase 9.3: Saved Filters

**SavedFilter Model:**
```
id, name, page, filter_json (stores query string), is_favorite
```

**Files created:**
- `app/models/saved_filter.py` - SavedFilter SQLAlchemy model
- `app/services/saved_filter_service.py` - CRUD operations, favorite toggle
- `app/routers/saved_filters.py` - API endpoints for saved filters
- `app/templates/partials/saved_filter_list.html` - Saved filter badges UI
- `alembic/versions/5990bd38093f_add_saved_filters.py` - Migration

**Files modified:**
- `app/models/__init__.py` - Export SavedFilter
- `app/main.py` - Register saved_filters router
- `app/templates/transactions.html` - Added saved filters section with save modal
- `app/routers/transactions.py` - Added saved_filters to context

**Key features:**
- Save current filter combination with custom name
- Set one filter as "favorite" per page
- Quick apply by clicking saved filter badge
- Delete saved filters with confirmation

---

## Phase 9.4: Transaction Table Refactor

**Files modified:**
- `app/routers/transactions.py` - Added `build_filter_query_string()` helper function
- `app/templates/partials/transaction_table.html` - Uses `filter_query_string` instead of building inline

**Key changes:**
- URL query string construction moved from template to router
- Template receives single `filter_query_string` variable
- Cleaner, more maintainable template code
- Sort and pagination links use the pre-built query string

---

## Phase 10: Manual Transactions

**Files to create:**
- `app/templates/transaction_form.html`
- `alembic/versions/xxxx_make_snaptrade_id_optional.py`

**Files to modify:**
- `app/models/transaction.py` - snaptrade_id nullable, add is_manual
- `app/services/transaction_service.py` - Add manual transaction CRUD
- `app/routers/transactions.py` - Add create/edit/delete routes
- `app/templates/transactions.html` - Add "New Transaction" button
- `app/templates/transaction_detail.html` - Add edit/delete for manual
