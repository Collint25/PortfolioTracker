# Portfolio Tracker

Personal investment tracking app. Syncs from Fidelity via SnapTrade API.

## Stack
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: Jinja2 + HTMX + Tailwind/DaisyUI
- Package mgr: uv

## Quick Start
```bash
make dev     # Sync deps, migrate, and run dev server
```

## Make Commands
- `make dev` - sync deps, migrate, run server (use this to start working)
- `make setup` - sync deps and migrate (no server)
- `make migrate` - run database migrations only
- `make test` - run pytest
- `make lint` - check with ruff and mypy
- `make format` - auto-format code
- `make check` - run lint + test (before committing)
- `make clean` - remove cache files
- `make kill` - stop server running on port 8001

## Raw Commands
For reference, the underlying commands:
- `uv sync --extra dev` - sync dependencies
- `uv run python run.py` - start dev server
- `uv run pytest` - run tests
- `uv run alembic upgrade head` - run migrations

**Note:** Dev tools (ruff, mypy, pytest) require dev dependencies. Run `uv sync --extra dev` (or `make setup`) if type checking or linting fails with import errors.

## Documentation

For architectural overview and system design, see `/docs/onboarding.md` for architecture diagram and component descriptions.

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
- app/calculations/ - pure P/L and position calculation functions
- app/utils/ - request param parsing, helpers
- app/templates/ - Jinja2 HTML
- tests/ - pytest tests

### Key services
- `lot_service.py` - FIFO lot matching for stocks/options
- `saved_filter_service.py` - CRUD for saved filters
- `filters.py` - TransactionFilter dataclass + filter builders

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
- **TradeLot** - tracks share/contract batches through open→close lifecycle
- **LotTransaction** - links TradeLot to Transaction with quantity allocation
- **SavedFilter** - named filters with favorite designation

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
