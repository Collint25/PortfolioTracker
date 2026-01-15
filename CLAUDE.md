# Portfolio Tracker

Personal investment tracking app. Syncs from Fidelity via SnapTrade API.

> **Note:** Keep project status updated as features are completed:
> - **This file (CLAUDE.md):** Update the Project Status section with high-level progress
> - **docs/PROJECT_PLAN.md:** Update with granular deliverables and acceptance criteria per phase

## Stack
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: Jinja2 + HTMX + Tailwind/DaisyUI
- Package mgr: uv

## Commands
- `uv run python run.py` - start dev server
- `uv run pytest` - run tests
- `uv run alembic upgrade head` - run migrations

## Structure
- app/models/ - SQLAlchemy models
- app/services/ - business logic (keep thin, focused functions)
- app/routers/ - FastAPI routes (thin, delegate to services)
- app/templates/ - Jinja2 HTML
- tests/ - pytest tests

## Code style
- Small functions (<40 lines)
- Type hints on all signatures
- Services handle logic, routes handle HTTP
- Config values in app/config.py not hardcoded

## Architecture

### Data flow
```
SnapTrade API → sync service → SQLite → services → routes → HTMX partials
```

### Domain models
- **Account** - Fidelity account (brokerage, IRA, etc.)
- **Position** - Current holding (symbol, quantity, cost basis)
- **Transaction** - Trade history (buy, sell, dividend, etc.)
- **SecurityInfo** - Cached ticker metadata

### Sync strategy
- Daily cron triggers full sync
- Transactions use `external_reference_id` to group multi-leg options
- Upsert by SnapTrade's unique IDs to avoid duplicates
- Store raw API response in `_raw_json` column for debugging

### HTMX patterns
- Full page loads return base template
- HX-Request header triggers partial responses
- Use `hx-swap="innerHTML"` for in-place updates
- Loading states via `hx-indicator`

## SnapTrade notes
- Data refreshes once/day (Fidelity limitation)
- external_reference_id groups multi-leg trades
- Rate limit: 250 req/min
- Transactions paginate at 1000/request
- Auth: user_id + user_secret per connection

## Project Status

### Completed
- [x] Project scaffold (models, routers, services, templates)
- [x] Database layer (SQLAlchemy + Alembic)
- [x] Base UI (DaisyUI + HTMX)
- [x] Initial migration + dependency install
- [x] Tests passing
- [x] SnapTrade client wrapper
- [x] Full sync service (accounts, positions, transactions)
- [x] Manual sync button with status display
- [x] Transaction list with filters, search, sort, pagination
- [x] Transaction detail page with related trades
- [x] Tags & comments system (create tags with colors, assign to transactions, filter by tag, inline editing)
- [x] Trade groups (multi-leg strategies with auto-grouping, combined P/L)
- [x] Logging configuration (stdout with formatted output)
- [x] SnapTrade API update (per-account endpoint, no deprecation warnings)
- [x] Positions view (market value, cost basis, gain/loss with percentages)

### In Progress
- [ ] Manual Transactions

### Backlog
- [ ] Metrics & Dashboard
- [ ] Position detail views
- [ ] Daily sync cron job (APScheduler)
