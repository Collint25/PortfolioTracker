# Portfolio Tracker

Personal investment tracking app. Syncs from Fidelity via SnapTrade API.

## Stack
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: Jinja2 + HTMX + Tailwind/DaisyUI
- Package mgr: uv

## Commands
- `uv run python run.py` - start dev server
- `uv run pytest` - run tests
- `uv run alembic upgrade head` - run migrations

## Git workflow
GitHub Flow: feature branch → PR → main

- Branch from main: `git checkout -b feature/<name>`
- Push + open PR (auto-reviewed by Claude)
- Merge PR, delete branch
- Never push directly to main
- Branch naming: `feature/thing`, `fix/bug`

## Structure
- app/models/ - SQLAlchemy models
- app/services/ - business logic (keep thin, focused functions)
- app/routers/ - FastAPI routes (thin, delegate to services)
- app/templates/ - Jinja2 HTML
- tests/ - pytest tests

## Code style
- Small functions
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
