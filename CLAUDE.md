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

## SnapTrade notes
- Data refreshes once/day (Fidelity limitation)
- external_reference_id groups multi-leg trades
- Rate limit: 250 req/min
- Transactions paginate at 1000/request
