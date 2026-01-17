# Portfolio Tracker - Project Plan

> Detailed implementation notes in [IMPLEMENTATION_NOTES.md](./IMPLEMENTATION_NOTES.md)

## Status Overview

| Phase | Name | Status |
|-------|------|--------|
| 0 | Init | ✅ |
| 1 | Foundation | ✅ |
| 2 | Data Sync | ✅ |
| 3 | Transaction UI | ✅ |
| 4 | Tags & Comments | ✅ |
| 5 | Trade Groups | ✅ |
| 6 | Logging & API Update | ✅ |
| 7 | Positions View | ✅ |
| 7.5 | Option Support | ✅ |
| 8 | Linked Trades - Data Model | ✅ |
| 8.1 | Linked Trades - FIFO Matching | ✅ |
| 8.2 | Linked Trades - API & UI | ✅ |
| 9 | Account Cards with Market Value | ✅ |
| 9.1 | Dashboard Enhancement | ✅ |
| 9.2 | Filter Consolidation | ✅ |
| 9.3 | Saved Filters | ✅ |
| 9.4 | Transaction Table Refactor | ✅ |
| 10 | Manual Transactions | ⬜ |
| 11 | Metrics & Dashboard | ⬜ |

---

## Completed Phases

### Phase 0-4: Foundation
Project scaffold, database, SnapTrade sync, transaction UI, tags & comments.

### Phase 5: Trade Groups
Multi-leg option strategies with auto-grouping by `external_reference_id` and combined P/L.

### Phase 6: Logging & API Update
Logging configuration, migrated to per-account SnapTrade endpoint.

### Phase 7: Positions View
Account positions page with market value, cost basis, gain/loss calculations.

### Phase 7.5: Option Support
Option fields (strike, expiration, CALL/PUT, action type), option position sync, filters.

### Phase 8-8.2: Linked Trades
FIFO matching for option open/close pairs. Links transactions to track P/L per position lifecycle.
- 472 linked trades, $5,948.86 total P/L, 51.2% win rate

### Phase 9: Account Cards with Market Value
Added `previous_close` column to positions, capture from Finnhub `pc` field. Account cards now display market value with daily $ and % change.

---

### Phase 9.1-9.4: UI/UX Improvements (Completed)

**9.1: Dashboard Enhancement**
- Replaced hero section with account cards grid showing market value and daily G/L
- Added expandable positions via HTMX with compact table view
- Portfolio-wide totals displayed at top

**9.2: Filter Consolidation**
- Reorganized filters into compact horizontal layout
- Primary filters (search, account, symbol, type, dates) always visible
- Advanced filters (options, tags) in collapsible section
- "Clear All" link for easy reset

**9.3: Saved Filters**
- SavedFilter model with name, page, query_string, is_favorite
- Save current filters with custom name
- Favorite filter can auto-apply on page load (future)
- Quick access via badge-style chips

**9.4: Transaction Table Refactor**
- Moved URL query string construction from template to router (`build_filter_query_string`)
- Template now uses single `filter_query_string` variable
- Cleaner, more maintainable template code

**Files created:**
- `app/models/saved_filter.py`
- `app/services/saved_filter_service.py`
- `app/routers/saved_filters.py`
- `app/templates/partials/saved_filter_list.html`
- `app/templates/partials/position_list_compact.html`
- `alembic/versions/5990bd38093f_add_saved_filters.py`

**Files modified:**
- `app/routers/pages.py` - Added accounts_with_totals, portfolio_totals, positions-inline route
- `app/routers/transactions.py` - Added build_filter_query_string, saved_filters
- `app/templates/index.html` - Account cards grid with expandable positions
- `app/templates/transactions.html` - Consolidated filters, saved filters UI
- `app/templates/partials/transaction_table.html` - Uses filter_query_string
- `app/main.py` - Registered saved_filters router
- `app/models/__init__.py` - Export SavedFilter

---

## Backlog

### Phase 10: Manual Transactions
Create/edit/delete transactions manually (without SnapTrade sync).

### Phase 11: Metrics & Dashboard
P/L tracking, performance charts, win rate, summary dashboard.
