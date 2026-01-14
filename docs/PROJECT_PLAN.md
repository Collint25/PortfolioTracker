# Portfolio Tracker - Project Plan

## Phase 0: Init

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

## Phase 1: Foundation

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

## Phase 2: Data Sync

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

## Phase 3: Transaction UI

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

## Phase 4: Tags & Comments

**Goal:** Annotate trades with tags and notes

**Deliverables:**
- [ ] Tag CRUD (create, list, delete)
- [ ] Assign/remove tags on transactions
- [ ] Add comments to transactions
- [ ] Tag management in settings
- [ ] Filter transactions by tag
- [ ] Inline tag editing (HTMX)

**Tests:**
- [ ] Tag CRUD operations
- [ ] Tag assignment to transaction
- [ ] Comment creation

**Acceptance:**
- Create custom tags with colors
- Tag transactions, filter by tag
- Add notes visible on detail page

---

## Phase 5: Trade Groups (Multi-leg)

**Goal:** Group related option legs into strategies

**Deliverables:**
- [ ] Trade group model and CRUD
- [ ] Auto-suggest groups (same external_reference_id)
- [ ] Manual group creation UI
- [ ] Strategy type classification (spread, condor, etc)
- [ ] Group list view
- [ ] Combined P/L for group

**Tests:**
- [ ] Auto-grouping logic
- [ ] Manual group CRUD
- [ ] P/L calculation for group

**Acceptance:**
- Related legs grouped together
- Can manually create/edit groups
- Group shows combined P/L

---

## Phase 6: Metrics & Dashboard

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
