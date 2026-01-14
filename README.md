# Portfolio Tracker

A personal investment tracking application that syncs transaction history from Fidelity via the SnapTrade API. Built for tracking trades, analyzing performance, and organizing multi-leg options strategies.

## Features

- **Automatic Sync** - Daily synchronization with Fidelity brokerage accounts via SnapTrade
- **Transaction History** - Browse, search, and filter all trades
- **Multi-leg Grouping** - Automatically groups related options legs (spreads, condors, etc.)
- **Tags & Notes** - Annotate trades with custom tags and comments
- **P/L Tracking** - Realized and unrealized profit/loss calculations
- **Dashboard** - Portfolio summary with performance metrics

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** Jinja2 + HTMX + Tailwind CSS + DaisyUI
- **Data:** SnapTrade API (Fidelity integration)
- **Package Manager:** uv

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- SnapTrade API credentials ([sign up here](https://snaptrade.com/))

### Installation

```bash
# Clone the repository
git clone https://github.com/Collint25/PortfolioTracker.git
cd PortfolioTracker

# Install dependencies
uv sync --extra dev

# Copy environment template
cp .env.example .env

# Run database migrations
uv run alembic upgrade head

# Start the development server
uv run python run.py
```

The app will be available at `http://127.0.0.1:8000`

### Configuration

Create a `.env` file with the following variables:

```env
# SnapTrade credentials
SNAPTRADE_CLIENT_ID=your_client_id
SNAPTRADE_CONSUMER_KEY=your_consumer_key

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///./portfolio.db
```

## Usage

<!-- TODO: Add usage instructions and screenshots -->

## Development

### Running Tests

```bash
uv run pytest
```

### Database Migrations

```bash
# Create a new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head
```

### Project Structure

```
PortfolioTracker/
├── app/
│   ├── models/          # SQLAlchemy ORM models
│   ├── routers/         # FastAPI route handlers
│   ├── services/        # Business logic
│   └── templates/       # Jinja2 HTML templates
├── alembic/             # Database migrations
├── tests/               # Pytest test suite
├── docs/                # Project documentation
└── run.py               # Development server entry point
```

## Roadmap

See [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for detailed phase-by-phase deliverables.

- [x] Phase 0: Project initialization
- [ ] Phase 1: Foundation (scaffold, database, SnapTrade auth)
- [ ] Phase 2: Data sync
- [ ] Phase 3: Transaction UI
- [ ] Phase 4: Tags & comments
- [ ] Phase 5: Trade groups (multi-leg)
- [ ] Phase 6: Metrics & dashboard

## Screenshots

<!-- TODO: Add screenshots -->

## License

<!-- TODO: Add license -->

## Acknowledgments

- [SnapTrade](https://snaptrade.com/) for brokerage API access
- [DaisyUI](https://daisyui.com/) for UI components
- [HTMX](https://htmx.org/) for hypermedia-driven interactions
