# Portfolio Tracker

Personal investment tracking app. Syncs from Fidelity via SnapTrade API.

## Stack
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: Jinja2 + HTMX + Tailwind/DaisyUI
- Package mgr: uv

## Commands
- `uv sync --extra dev` - sync all dependencies including dev tools (run after clone)
- `uv run python run.py` - start dev server
- `uv run pytest` - run tests
- `uv run alembic upgrade head` - run migrations

**Note:** Dev tools (ruff, mypy, pytest) require dev dependencies. Run `uv sync --extra dev` if type checking or linting fails with import errors.

## Documentation

For architectural overview and system design:
- See `/docs/onboarding.md` for architecture diagram and component descriptions
- See `/docs/codebase_analysis.json` for machine-readable architecture data

The docs provide high-level context on the "Sync-Process-Present" flow and how components like the Sync Orchestrator, Domain Logic Engine, and Transaction Manager interact.

## Code Quality

### Linting & Type Checking
- `uv run ruff check .` - check for lint issues
- `uv run ruff check . --fix` - auto-fix lint issues
- `uv run ruff format .` - format code
- `uv run mypy app/ tests/` - run type checker

### Pre-commit Hooks
- `uv run pre-commit install` - install git hooks (one-time)
- `uv run pre-commit run --all-files` - run hooks manually

Git hooks run automatically on commit and enforce:
- Code formatting (ruff format)
- Import sorting (ruff isort)
- Type checking (mypy)

To bypass hooks (rare): `git commit --no-verify`

### CI Checks
All PRs must pass:
- Ruff linting
- Ruff formatting
- Mypy type checking

See `.github/workflows/lint.yml` for details.

## Git workflow
GitHub Flow: feature branch → PR → main

- Branch from main: `git checkout -b feature/<name>`
- Push + open PR (auto-reviewed by Claude)
- Merge PR, delete branch
- Never push directly to main
- Branch naming: `feature/thing`, `fix/bug`

## Plan

When writing implementation plans:
- **Extreme concision** - sacrifice grammar for brevity
- Bullets over prose
- Omit articles (a, an, the)
- Use fragments, not sentences
- **End with unresolved questions** - list anything needing clarification

## Structure
- app/models/ - SQLAlchemy models
- app/services/ - business logic (keep thin, focused functions)
- app/routers/ - FastAPI routes (thin, delegate to services)
- app/templates/ - Jinja2 HTML
- tests/ - pytest tests

## Code style
- Small functions
- Type hints on all signatures (enforced by mypy)
- Services handle logic, routes handle HTTP
- Config values in app/config.py not hardcoded
- Formatting: Ruff (88 char line length)
- Imports: Auto-sorted by ruff isort

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
