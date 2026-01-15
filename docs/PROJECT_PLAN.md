# Portfolio Tracker - Project Plan

## Status Overview

| Phase | Name | Status |
|-------|------|--------|
| 0 | Init | ✅ Complete |
| 1 | Foundation | ✅ Complete |
| 2 | Data Sync | ✅ Complete |
| 3 | Transaction UI | ✅ Complete |
| 4 | Tags & Comments | ✅ Complete |
| 5 | Trade Groups (Multi-leg) | ✅ Complete |
| 6 | Logging & SnapTrade API Update | ✅ Complete |
| 7 | Positions View | ✅ Complete |
| 7.5 | Option Support | ✅ Complete |
| 8 | Linked Trades - Data Model | ✅ Complete |
| 8.1 | Linked Trades - FIFO Matching | ✅ Complete |
| 8.2 | Linked Trades - API & UI | ✅ Complete |
| 9 | Manual Transactions | ⬜ Not Started |
| 10 | Metrics & Dashboard | ⬜ Not Started |

---

## Phase 0: Init ✅

**Goal:** Initialize git repo and create project documentation

**Deliverables:**
- [x] git init
- [x] CLAUDE.md - AI context file
- [x] docs/PROJECT_PLAN.md - this file
- [x] Minimal .gitignore (only __pycache__, *.pyc, *.db, .pytest_cache)

**Note:** Private repo - .env, .vscode/, .claude/ tracked in git

**Acceptance:**
- Repo initialized with initial commit
- Project docs in place for future sessions

---

## Phase 1: Foundation ✅

**Goal:** Project scaffolding, database, SnapTrade auth flow

**Deliverables:**
- [x] uv project init with all dependencies
- [x] Tailwind + DaisyUI configured (via CDN)
- [x] SQLAlchemy models for all tables
- [x] Alembic migrations
- [x] SnapTrade client wrapper (using pre-registered user credentials)
- [~] Settings page with "Connect Fidelity" button (N/A - using env vars)
- [~] OAuth callback handler (N/A - using pre-registered user)
- [x] Base template with nav, theme switcher

**Tests:**
- [x] DB models create/read (in-memory test DB)
- [ ] SnapTrade client mocked - auth URL generation
- [x] Settings page renders (index + health check tests passing)

**Acceptance:**
- [x] App starts, shows settings page
- [x] SnapTrade client connects (via user credentials in .env)
- [x] DB tables created via migration

---

## Phase 2: Data Sync ✅

**Goal:** Fetch all transactions from SnapTrade, store locally

**Deliverables:**
- [x] Sync service - fetch accounts
- [x] Sync service - fetch positions (holdings)
- [x] Sync service - fetch all transactions
- [x] Upsert logic (dedupe by snaptrade_id)
- [x] Manual sync button in UI
- [ ] APScheduler daily sync job
- [x] Sync status display (record counts)

**Tests:**
- [ ] Sync service with mocked API responses
- [x] Deduplication on re-sync (verified manually)
- [ ] Pagination handling

**Acceptance:**
- [x] Transactions appear in DB after sync (1650 synced)
- [x] Positions appear in DB after sync (28 synced)
- [x] Re-sync doesn't create duplicates

---

## Phase 3: Transaction UI ✅

**Goal:** View and filter transaction history

**Deliverables:**
- [x] Transaction list page (table)
- [x] Filters: date range, symbol, type, account
- [x] Search by symbol/description
- [x] Sorting by date, symbol, amount
- [x] Transaction detail page
- [x] HTMX partial updates for filters
- [x] Pagination

**Tests:**
- [x] List endpoint returns correct data
- [x] Filters work correctly
- [x] Detail page renders (404 for missing)

**Acceptance:**
- [x] Can browse all transactions
- [x] Filters narrow results correctly
- [x] Clicking row shows detail

---

## Phase 4: Tags & Comments ✅

**Goal:** Annotate trades with tags and notes

**Deliverables:**
- [x] Tag CRUD (create, list, delete)
- [x] Assign/remove tags on transactions
- [x] Add comments to transactions
- [x] Tag management in settings
- [x] Filter transactions by tag
- [x] Inline tag editing (HTMX)

**Tests:**
- [x] Tag CRUD operations
- [x] Tag assignment to transaction
- [x] Comment creation

**Acceptance:**
- [x] Create custom tags with colors
- [x] Tag transactions, filter by tag
- [x] Add notes visible on detail page

---

## Phase 5: Trade Groups (Multi-leg) ✅

**Goal:** Group related option legs into strategies

**Deliverables:**
- [x] Trade group model and CRUD
- [x] Auto-suggest groups (same external_reference_id)
- [x] Manual group creation UI
- [x] Strategy type classification (spread, condor, etc)
- [x] Group list view
- [x] Combined P/L for group

**Tests:**
- [x] Auto-grouping logic
- [x] Manual group CRUD
- [x] P/L calculation for group

**Acceptance:**
- [x] Related legs grouped together
- [x] Can manually create/edit groups
- [x] Group shows combined P/L

**Implementation Notes:**

Files created:
- `app/models/trade_group.py` - TradeGroup model + M2M association table
- `app/services/trade_group_service.py` - CRUD, P/L calc, auto-grouping logic
- `app/routers/trade_groups.py` - All endpoints under /trade-groups
- `app/templates/trade_groups.html` - Main list page
- `app/templates/trade_group_detail.html` - Detail/edit page
- `app/templates/partials/trade_group_list.html` - List partial
- `app/templates/partials/trade_group_suggestions.html` - Auto-suggest UI
- `app/templates/partials/trade_group_transactions.html` - Txns in group
- `app/templates/partials/trade_group_detail_content.html` - Detail partial
- `app/templates/partials/transaction_trade_groups.html` - Groups on txn detail
- `alembic/versions/1b71213d8c1a_add_trade_groups.py` - Migration
- `tests/test_trade_groups.py` - 14 tests

Files modified:
- `app/models/__init__.py` - Export TradeGroup
- `app/models/transaction.py` - Added trade_groups relationship
- `app/main.py` - Registered trade_groups router
- `app/templates/base.html` - Added nav link
- `app/templates/transaction_detail.html` - Added trade groups section

Strategy types: vertical_spread, iron_condor, iron_butterfly, straddle, strangle,
calendar_spread, diagonal_spread, covered_call, protective_put, collar, custom

**Manual Testing Checklist:**
- [ ] Navigate to Trade Groups page from nav
- [ ] Create a new trade group with name, strategy type, description
- [ ] View suggested groups (requires transactions with same external_reference_id)
- [ ] Create group from suggestion (one-click)
- [ ] Click into group detail page
- [ ] Edit group name/strategy/description
- [ ] Remove a transaction from a group
- [ ] Delete a group (confirm redirect to list)
- [ ] On transaction detail, view assigned groups
- [ ] Add transaction to existing group from dropdown
- [ ] Verify combined P/L calculates correctly (sum of transaction amounts)
- [ ] Verify group appears on all member transactions' detail pages

---

## Phase 6: Logging & SnapTrade API Update ✅

**Goal:** Add logging configuration and fix deprecated SnapTrade endpoint

**Deliverables:**
- [x] Logging configuration (capture SDK warnings in stdout)
- [x] Update SnapTrade API (replace deprecated get_activities with per-account endpoint)

**Tests:**
- [x] Logging output appears on server start
- [x] Sync completes without deprecation warning (per-account endpoint used)

**Acceptance:**
- Logging shows SDK warnings in stdout
- Sync uses new per-account endpoint without deprecation warning

**Implementation Notes:**

Files created:
- `app/logging_config.py` - Logging setup module with stdout handler, INFO level, formatted output

Files modified:
- `app/main.py` - Import and call `configure_logging()` at startup
- `app/services/snaptrade_client.py` - Added `fetch_account_activities()` using `account_information.get_account_activities()` with pagination support
- `app/services/sync_service.py` - `sync_transactions()` now loops through accounts and fetches per-account activities

Key changes:
- Replaced `transactions_and_reporting.get_activities()` (deprecated) with `account_information.get_account_activities()` (per-account)
- Per-account endpoint returns `{"data": [...], "pagination": {...}}` - extract activities from `data` key
- Pagination handled internally with offset/limit (1000 per request)
- Account ID now resolved from loop context instead of parsing response (per-account response doesn't include `account` field)
- Added `logger.exception()` to sync router for error visibility

**Manual Testing Checklist:**
- [x] Start server and verify logging output appears in stdout
- [x] Run sync from UI
- [x] Verify no deprecation warning in logs
- [x] Verify transactions still sync correctly (1656 transactions synced)

---

## Phase 7: Positions View ✅

**Goal:** Fix 404 error when viewing account positions

**Deliverables:**
- [x] Account positions route and view
- [x] Position list with market value and gain/loss

**Tests:**
- [x] Position view renders with valid account
- [x] Position view returns 404 for invalid account
- [x] Gain/loss calculations
- [x] Account positions summary with totals

**Acceptance:**
- Can view account positions without 404 error
- Position list shows symbol, quantity, cost, current price, gain/loss

**Implementation Notes:**

Files created:
- `app/services/position_service.py` - Position queries and calculations (market value, cost basis, gain/loss, percentages)
- `app/templates/account_positions.html` - Positions page with summary cards
- `app/templates/partials/position_list.html` - Positions table partial
- `tests/test_positions.py` - 8 tests

Files modified:
- `app/routers/accounts.py` - Added `/{account_id}/positions` route
- `app/main.py` - Changed accounts prefix from `/api/accounts` to `/accounts`
- `app/templates/base.html` - Fixed accounts nav link
- `app/templates/accounts.html` - Fixed HTMX endpoint

**Manual Testing Checklist:**
- [x] Navigate to Accounts page
- [x] Click "View Positions" on an account
- [x] Verify positions load without 404
- [x] Verify market value and gain/loss display correctly

---

## Phase 7.5: Option Support ✅

**Goal:** Extract option fields from transactions and sync option positions

**Deliverables:**
- [x] Add option columns to Transaction model (option_type, strike_price, expiration_date, option_ticker, is_option)
- [x] Add option_action column to Transaction model (BUY_TO_OPEN, SELL_TO_CLOSE, etc.)
- [x] Add option columns to Position model (same fields + underlying_symbol)
- [x] Extract option data during transaction sync
- [x] Sync option holdings via `list_option_holdings` endpoint
- [x] Display option details in UI (strike, expiration, CALL/PUT, action)
- [x] Add option filters to transaction list (option type, action, is_option)

**Tests:**
- [x] Option field extraction from raw JSON
- [x] Option position sync
- [x] UI displays option details correctly

**Acceptance:**
- [x] Transactions show option details (e.g., "AAPL $250 01/17 C" instead of just "AAPL")
- [x] Transactions show action type (BUY TO OPEN, SELL TO CLOSE, etc.)
- [x] Option positions appear on positions page
- [x] Can filter transactions by option type (CALL/PUT), action (BUY_TO_OPEN, etc.), is_option

**Note on bid/ask spread:** Not available in transaction history (executed trades). Would require real-time quote API calls. Deferred to future enhancement if needed.

**Implementation Notes:**

Option data available from SnapTrade:
- `option_symbol` object contains: ticker, strike_price, expiration_date, option_type (CALL/PUT), underlying_symbol
- `option_type` at root level contains action: BUY_TO_OPEN, BUY_TO_CLOSE, SELL_TO_OPEN, SELL_TO_CLOSE
- 892 option transactions identified in database

Files created:
- `alembic/versions/a7f3c2d5e8b1_add_option_support.py` - Migration for both models
- `scripts/backfill_options.py` - Backfill script for existing transactions
- `tests/test_options.py` - 7 option-specific tests

Files modified:
- `app/models/transaction.py` - Added: is_option, option_type, strike_price, expiration_date, option_ticker, underlying_symbol, option_action
- `app/models/position.py` - Added: is_option, option_type, strike_price, expiration_date, option_ticker, underlying_symbol
- `app/services/sync_service.py` - Added _extract_option_data(), _sync_option_position(), updated sync_transactions/sync_positions
- `app/services/snaptrade_client.py` - Added fetch_option_holdings()
- `app/services/market_data_service.py` - Skip option positions using is_option flag
- `app/services/transaction_service.py` - Added is_option, option_type, option_action filters + helper functions
- `app/routers/transactions.py` - Added is_option, option_type, option_action query params
- `app/templates/transactions.html` - Added 3 new option filter dropdowns
- `app/templates/partials/transaction_table.html` - Show option details in symbol column, option action in type column
- `app/templates/partials/position_list.html` - Show option details in symbol column
- `app/templates/transaction_detail.html` - Added Option Details section

**SnapTrade API Notes:**
- Transaction option data: `option_symbol` field in activity response
- Transaction action type: `option_type` field at root level (BUY_TO_OPEN, etc.)
- Option positions: `options.list_option_holdings(account_id, user_id, user_secret)`
- Option holdings structure: `symbol.option_symbol` contains option details (not at root level)

**Manual Testing Checklist:**
- [x] Run migration (`uv run alembic upgrade head`)
- [x] Run backfill for existing transactions (`uv run python scripts/backfill_options.py`)
- [ ] Check transactions page shows option details
- [ ] Check positions page shows option holdings
- [ ] Verify "Refresh Prices" skips options gracefully
- [ ] Filter transactions by CALL/PUT

---

## Phase 8: Linked Trades - Data Model ✅

**Goal:** Create database models for linking opening and closing option trades

**Background:**
- No linking ID exists from Fidelity/SnapTrade between open/close trades
- `external_reference_id` only groups same-day multi-leg trades (spreads)
- Must match by contract identity: (account_id, underlying_symbol, option_type, strike_price, expiration_date)
- 892 option transactions to process

**Deliverables:**
- [x] LinkedTrade model (tracks a single option position lifecycle)
- [x] LinkedTradeLeg model (M2M with quantity allocation for partial closes)
- [x] Update Transaction model with relationship
- [x] Update Account model with relationship
- [x] Alembic migration

**LinkedTrade Model Fields:**
```
id, account_id (FK)
underlying_symbol, option_type, strike_price, expiration_date
direction (LONG/SHORT)
realized_pl, is_closed
total_opened_quantity, total_closed_quantity
is_auto_matched, notes
```

**LinkedTradeLeg Model Fields:**
```
id, linked_trade_id (FK), transaction_id (FK)
allocated_quantity (enables partial closes)
leg_type (OPEN/CLOSE)
trade_date, price_per_contract (denormalized for display)
```

**Key Difference from TradeGroup:** LinkedTradeLeg stores `allocated_quantity` per leg, enabling one transaction to be split across multiple linked trades (partial closes).

**Files to Create:**
- `app/models/linked_trade.py`
- `app/models/linked_trade_leg.py`
- `alembic/versions/xxxx_add_linked_trades.py`

**Files to Modify:**
- `app/models/__init__.py` - Export new models
- `app/models/transaction.py` - Add `linked_trade_legs` relationship
- `app/models/account.py` - Add `linked_trades` relationship

**Tests:**
- [x] LinkedTrade model CRUD
- [x] LinkedTradeLeg with quantity allocation
- [x] Relationships work correctly

**Acceptance:**
- [x] Migration runs successfully
- [x] Can create LinkedTrade with legs in test
- [x] Partial allocation works (one transaction split across multiple links)

**Implementation Notes:**

Files created:
- `app/models/linked_trade.py` - LinkedTrade model with contract fields, P/L, status
- `app/models/linked_trade_leg.py` - LinkedTradeLeg model with quantity allocation
- `alembic/versions/b8c4d6e9f0a2_add_linked_trades.py` - Migration

Files modified:
- `app/models/__init__.py` - Export new models
- `app/models/transaction.py` - Added `linked_trade_legs` relationship
- `app/models/account.py` - Added `linked_trades` relationship

---

## Phase 8.1: Linked Trades - FIFO Matching ✅

**Goal:** Implement FIFO algorithm to auto-match opening/closing trades

**FIFO Algorithm:**
```
Match by contract identity: (account_id, underlying_symbol, option_type, strike_price, expiration_date)

For each unique contract:
  1. Get all opening transactions ordered by (trade_date, id)
  2. Get all closing transactions ordered by (trade_date, id)
  3. Track remaining quantity per opening transaction
  4. For each close:
     - Allocate to oldest open with remaining qty (FIFO)
     - Create/extend LinkedTrade with legs
     - Mark closed when total_closed >= total_opened
  5. Calculate realized P/L = sum(close amounts) + sum(open amounts)
```

**Direction Mapping:**
- LONG: BUY_TO_OPEN → SELL_TO_CLOSE
- SHORT: SELL_TO_OPEN → BUY_TO_CLOSE

**Scenarios to Handle:**
1. Simple: Open 5, close 5 (full match)
2. Partial: Open 5, close 3, close 2 later
3. Multiple opens: Open 3 day 1, open 2 day 2, close 5
4. Short selling: SELL_TO_OPEN → BUY_TO_CLOSE
5. Orphans: Opens without closes (position still open)
6. Cross-account: Must NOT link across accounts

**Deliverables:**
- [x] ContractKey named tuple for contract identity
- [x] `find_unique_contracts(db)` - Find all unique option contracts
- [x] `auto_match_contract(db, contract_key)` - FIFO match single contract
- [x] `auto_match_all(db)` - Match all unlinked transactions
- [x] `calculate_linked_trade_pl(db, link_id)` - P/L calculation
- [x] `get_unlinked_option_transactions(db)` - Find orphans

**Files Created:**
- `app/services/linked_trade_service.py` - Full FIFO matching service
- `tests/test_linked_trades.py` - 7 unit tests

**Tests:**
- [x] FIFO simple match (open 5, close 5)
- [x] FIFO partial close (open 5, close 3, close 2)
- [x] FIFO multiple opens (open 3, open 2, close 5)
- [x] SHORT direction (SELL_TO_OPEN → BUY_TO_CLOSE)
- [x] Cross-account no match
- [x] P/L calculation accuracy
- [x] Orphan handling

**Acceptance:**
- [x] `auto_match_all()` creates correct LinkedTrades
- [x] FIFO order respected
- [x] P/L calculations correct
- [x] No cross-account linking

**Results from Real Data:**
- 472 linked trades created from 298 unique contracts
- Total P/L: $5,948.86
- Win Rate: 51.2% (216 winners, 206 losers)
- 422 closed positions, 50 open

---

## Phase 8.2: Linked Trades - API & UI ✅

**Goal:** API endpoints, UI pages, and manual override capability

**API Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/linked-trades` | List with filters (account, symbol, status) |
| GET | `/linked-trades/{id}` | Detail view with legs |
| GET | `/linked-trades/open-positions` | Open positions only |
| GET | `/linked-trades/unlinked` | Unlinked option transactions |
| POST | `/linked-trades/auto-match` | Run FIFO matching |
| POST | `/linked-trades` | Manual create |
| POST | `/linked-trades/{id}/legs` | Add leg |
| DELETE | `/linked-trades/{id}/legs/{leg_id}` | Remove leg |
| DELETE | `/linked-trades/{id}` | Unlink trade |

**Manual Override Functions:**
- `create_linked_trade_manual(db, account_id, txn_ids, allocations)`
- `add_transaction_to_linked_trade(db, link_id, txn_id, qty)`
- `remove_leg_from_linked_trade(db, leg_id)`
- `unlink_trade(db, link_id)` - Delete link, free transactions for re-matching

**UI Pages:**
- `/linked-trades` - List with P/L summary, "Run Auto-Match" button
- `/linked-trades/{id}` - Detail with legs table, add/remove legs

**Transaction Detail Update:**
- Add "Linked Trades" card for option transactions
- Show which linked trades include this transaction
- Display allocated quantity and P/L contribution

**Files to Create:**
- `app/routers/linked_trades.py`
- `app/templates/linked_trades.html`
- `app/templates/linked_trade_detail.html`
- `app/templates/partials/linked_trade_list.html`
- `app/templates/partials/linked_trade_legs.html`
- `app/templates/partials/transaction_linked_trades.html`

**Files to Modify:**
- `app/main.py` - Register router
- `app/templates/base.html` - Add nav link
- `app/templates/transaction_detail.html` - Add linked trades section

**Tests:**
- [ ] List endpoint with filters
- [ ] Detail endpoint
- [ ] Auto-match endpoint
- [ ] Manual create/edit/delete

**Acceptance:**
- [ ] Can view all linked trades with P/L
- [ ] Can run auto-match from UI
- [ ] Can manually create/edit links
- [ ] Transaction detail shows linked trades for options

**Manual Testing Checklist:**
- [ ] Navigate to Linked Trades page
- [ ] Click "Run Auto-Match"
- [ ] Verify linked trades created
- [ ] Check P/L calculations
- [ ] Click into linked trade detail
- [ ] Remove a leg, add it back
- [ ] Unlink a trade entirely
- [ ] Go to transaction detail, verify linked trades section appears

---

## Phase 9: Manual Transactions ⬜

**Goal:** Allow creating, editing, and deleting transactions manually (without SnapTrade)

**Deliverables:**
- [ ] Database migration (make snaptrade_id nullable, add is_manual flag)
- [ ] Manual transaction create/edit/delete
- [ ] Manual transactions support tags, comments, trade groups (full feature parity)

**Tests:**
- [ ] Manual transaction CRUD
- [ ] Cannot edit/delete synced transactions

**Acceptance:**
- Can create manual transactions with full feature parity
- Can edit and delete manual transactions
- Synced transactions are protected from edit/delete

**Implementation Notes:**

Files created:
- `app/templates/transaction_form.html` - Manual transaction form
- `app/templates/partials/transaction_form_content.html` - Form partial
- `alembic/versions/xxxx_make_snaptrade_id_optional.py` - Migration

Files modified:
- `app/models/transaction.py` - snaptrade_id nullable, add is_manual
- `app/services/transaction_service.py` - Add manual transaction CRUD
- `app/routers/transactions.py` - Add create/edit/delete routes
- `app/templates/transactions.html` - Add "New Transaction" button
- `app/templates/transaction_detail.html` - Add edit/delete for manual transactions

**Manual Testing Checklist:**
- [ ] Go to Transactions page
- [ ] Click "New Transaction" button
- [ ] Fill out form and submit
- [ ] Verify new transaction appears in list
- [ ] Click into manual transaction detail
- [ ] Add tags and comments
- [ ] Edit the transaction
- [ ] Delete the transaction
- [ ] Verify synced transactions have no edit/delete buttons

---

## Phase 10: Metrics & Dashboard ⬜

**Goal:** P/L tracking and performance overview

**Deliverables:**
- [ ] Realized P/L calculation per transaction
- [ ] P/L by symbol rollup
- [ ] Dashboard home page with summary cards
- [ ] P/L chart (simple bar or line)
- [ ] Holdings sync from SnapTrade (for unrealized)
- [ ] Win rate calculation

**Tests:**
- [ ] P/L calculation accuracy
- [ ] Rollup aggregations

**Acceptance:**
- Dashboard shows total P/L
- Can see P/L breakdown by symbol
- Win rate displayed
