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
| 9.1 | Dashboard Enhancement | ⬜ |
| 9.2 | Filter Consolidation | ⬜ |
| 9.3 | Saved Filters | ⬜ |
| 9.4 | Transaction Table Refactor | ⬜ |
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

## In Progress

### Phase 9.1: Dashboard Enhancement
Replace hero section with account cards grid, expandable positions on click.

### Phase 9.2: Filter Consolidation
Group stock/option filters, collapsible section, reduced vertical space.

### Phase 9.3: Saved Filters
Save filter combinations with names, set favorite for auto-apply on page load.

### Phase 9.4: Transaction Table Refactor
Move URL construction from template to router for cleaner code.

---

## Backlog

### Phase 10: Manual Transactions
Create/edit/delete transactions manually (without SnapTrade sync).

### Phase 11: Metrics & Dashboard
P/L tracking, performance charts, win rate, summary dashboard.
