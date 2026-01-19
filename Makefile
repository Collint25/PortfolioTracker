.PHONY: help setup dev run test lint format check migrate clean kill

# Default target
help:
	@echo "Portfolio Tracker Development Commands"
	@echo ""
	@echo "  make dev      - Sync deps, migrate, and run dev server"
	@echo "  make run      - Start dev server only (no setup)"
	@echo "  make setup    - Sync deps and run migrations"
	@echo "  make migrate  - Run database migrations only"
	@echo "  make test     - Run pytest"
	@echo "  make lint     - Check code with ruff and mypy"
	@echo "  make format   - Auto-format code with ruff"
	@echo "  make check    - Run all checks (lint + test)"
	@echo "  make clean    - Remove cache files"
	@echo "  make kill     - Stop server running on port 8001"

# Sync dependencies and run migrations
setup:
	uv sync --extra dev
	uv run alembic upgrade head

# Run dev server (with setup)
dev: setup
	uv run python run.py

# Run dev server only (no setup)
run:
	uv run python run.py

# Run tests
test:
	uv run pytest

# Run migrations only
migrate:
	uv run alembic upgrade head

# Lint and type check
lint:
	uv run ruff check .
	uv run mypy app/ tests/

# Auto-format code
format:
	uv run ruff format .
	uv run ruff check . --fix

# Run all checks (useful before committing)
check: lint test

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

# Kill any server running on port 8001
kill:
	@pid=$$(lsof -ti :8001) && kill $$pid && echo "Killed server (PID $$pid)" || echo "No server running on port 8001"
