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
| 7 | Positions View | ⬜ Not Started |
| 8 | Manual Transactions | ⬜ Not Started |
| 9 | Metrics & Dashboard | ⬜ Not Started |

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

## Phase 7: Positions View ⬜

**Goal:** Fix 404 error when viewing account positions

**Deliverables:**
- [ ] Account positions route and view
- [ ] Position list with market value and gain/loss

**Tests:**
- [ ] Position view renders with valid account
- [ ] Position view returns 404 for invalid account

**Acceptance:**
- Can view account positions without 404 error
- Position list shows symbol, quantity, cost, current price, gain/loss

**Implementation Notes:**

Files created:
- `app/services/position_service.py` - Position queries
- `app/templates/account_positions.html` - Positions page
- `app/templates/partials/position_list.html` - Positions partial

Files modified:
- `app/routers/accounts.py` - Add `/{account_id}/positions` route
- `app/main.py` - Change accounts prefix from `/api/accounts` to `/accounts`
- `app/templates/base.html` - Fix accounts nav link

**Manual Testing Checklist:**
- [ ] Navigate to Accounts page
- [ ] Click "View Positions" on an account
- [ ] Verify positions load without 404
- [ ] Verify market value and gain/loss display correctly

---

## Phase 8: Manual Transactions ⬜

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

## Phase 9: Metrics & Dashboard ⬜

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
