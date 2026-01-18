# Architecture Review: Portfolio Tracker

**Date:** 2026-01-17
**Scope:** Comprehensive review of architecture, patterns, data strategy for scalability

## Executive Summary

Overall architecture is **solid for personal use** with good separation of concerns. Key findings:

- ✅ Clean service layer pattern
- ✅ Strong schema design with appropriate indexes
- ⚠️ Unused code (filters.py, trade_groups) adds confusion
- ⚠️ Inconsistent calculation abstraction patterns
- 💡 Good learning opportunities in filter objects, association patterns

## 1. Calculation Patterns

### Current State

Three distinct patterns in use:

**Pure functions** (position_service.py)
```python
def calculate_market_value(position: Position) -> Decimal | None:
    return position.quantity * position.current_price
```
- ✅ No DB access, highly testable
- ✅ Can be moved to separate calculation layer
- ✅ Clear input/output

**Mixed query + calculation** (linked_trade_service.py:429)
```python
def calculate_linked_trade_pl(db: Session, linked_trade_id: int) -> Decimal:
    # Loads from DB then calculates
```
- ⚠️ Couples data access with business logic
- ⚠️ Harder to test in isolation

**Property methods** (linked_trade.py:58-67)
```python
@property
def contract_display(self) -> str:
    return f"{self.underlying_symbol} ${self.strike_price}..."
```
- ⚠️ Couples formatting to model
- ✅ Convenient for templates

### Recommendation

**Standardize on pure calculation functions** for testability:

```python
# Pure calculation (testable)
def calculate_pl_from_legs(legs: list[LinkedTradeLeg]) -> Decimal:
    total = Decimal("0")
    for leg in legs:
        # calculation logic
    return total

# Service function (orchestration)
def get_linked_trade_pl(db: Session, id: int) -> Decimal:
    trade = get_linked_trade_by_id(db, id)
    return calculate_pl_from_legs(trade.legs)
```

**Benefits:**
- Test calculations without DB fixtures
- Reuse calculations in different contexts
- Clearer separation of concerns

**When to skip:** Simple property methods like `remaining_quantity` are fine—no need to over-abstract.

---

## 2. Schema & Data Strategy

### What's Stored

**Transactions** (transaction.py)
- Core: symbol, dates, type, quantity, price, amount, currency
- Options: strike, expiration, option_type, option_action, underlying_symbol
- Grouping: external_reference_id (multi-leg trades)
- Debug: _raw_json (full API response)

**Positions** (position.py)
- Core: symbol, quantity, average_cost, current_price, previous_close
- Options: same as transactions
- Debug: _raw_json

### Data Quality

**Good decisions:**
- ✅ _raw_json storage - invaluable for debugging/backfill
- ✅ Separate is_option flag + nullable option fields
- ✅ Denormalized underlying_symbol - makes queries simple

**Acceptable trade-offs:**
- ⚠️ position.previous_close staleness - updates only on sync (daily), acceptable for personal use
- ⚠️ No cost_basis history - if average_cost changes, lose historical values (not needed currently)

### Computed vs Stored

**Currently computed on-the-fly:**
- Market value (qty × current_price)
- Gain/loss
- Daily change
- P/L for linked trades (when open)

**Currently stored:**
- current_price, previous_close (from API)
- average_cost (from API)
- realized_pl (on closed linked trades - correct, immutable)

**Decision tree for future:**

**Store if:**
- Expensive to compute (many joins)
- Historical/immutable (realized P/L on closed trades)
- Performance bottleneck identified

**Compute if:**
- Simple formula (multiplication, subtraction)
- Real-time/frequently changing
- Storage/sync overhead > computation cost

**Current approach is optimal** for scale. Computing market_value is trivial; storing it creates write amplification.

---

## 3. Filtering Logic

### Current State

**Two implementations exist:**

1. **Inline filtering** (transaction_service.py) - **IN USE**
   - 15+ if statements in get_transactions()
   - Query params parsed in router, passed to service

2. **Filter objects** (filters.py) - **UNUSED / DEAD CODE**
   - Clean dataclass approach
   - apply_transaction_filters() function
   - Nothing imports it

### Recommendation: Migrate to Filter Objects

**Rationale:**
- Better abstraction - router builds filter object, service applies it
- Testable filter logic in isolation
- Clearer API contracts (dataclass vs 15 optional params)
- Good learning for larger projects

**Migration path:**

```python
# Router: Build filter object
@router.get("/transactions")
def list_transactions(
    request: Request,
    db: Session = Depends(get_db),
    # ... query params ...
):
    filters = TransactionFilter(
        account_id=parse_int_param(account_id),
        symbol=symbol,
        # ...
    )
    transactions, total = transaction_service.get_transactions(db, filters)
    # ...

# Service: Apply filters
def get_transactions(
    db: Session,
    filters: TransactionFilter,
    pagination: PaginationParams = PaginationParams(),
) -> tuple[list[Transaction], int]:
    query = db.query(Transaction)
    query = apply_transaction_filters(query, filters)
    query = apply_transaction_sorting(query, filters)

    total = query.count()

    query = apply_pagination(query, pagination)
    return query.all(), total
```

**Files to update:**
- app/routers/transactions.py - use TransactionFilter
- app/services/transaction_service.py - accept TransactionFilter
- Delete inline filter logic from service

---

## 4. Custom Utilities

### Assessment

**query_params.py** (parse_int_param, parse_bool_param, parse_date_param)
- ✅ **Keep** - FastAPI Query() params are strings, need parsing
- ✅ Clear naming, simple implementation
- Alternative: Pydantic models (more FastAPI-native), but current approach is explicit

**htmx.py** (is_htmx_request, htmx_response)
- ✅ **Keep** - DRY for HTMX detection
- ⚠️ htmx_response() under-utilized (transactions.py:175 does it manually)
- Recommendation: Use htmx_response() consistently

**Verdict:** Keep all utilities. They're domain-specific adapters that would cost more to replace with a library than the 40 lines they occupy.

---

## 5. Database Design Patterns

### Patterns in Use

**1. One-to-Many (Foreign Key)**
```python
# Transaction belongs to one Account
transaction.account_id → accounts.id
```
Use when: Clear ownership, no relationship attributes needed

**2. Many-to-Many (Association Table)**
```python
# Tag ↔ Transaction
transaction_tags = Table("transaction_tags", ...)
```
Use when: Multiple entities relate to multiple others, no extra data on relationship

**3. Association Object (Rich Join Table)**
```python
class LinkedTradeLeg(Base):
    linked_trade_id: int
    transaction_id: int
    allocated_quantity: Decimal  # Extra attribute
    leg_type: str  # Extra attribute
```
Use when: Many-to-many needs extra data (quantity allocation, leg type)

### Denormalization Decisions

**LinkedTradeLeg denormalizes:**
- trade_date (from transaction)
- price_per_contract (from transaction)

**Rationale:** Avoid joins when displaying linked trade lists

**Cost:** Extra storage + sync logic
**Benefit:** Faster queries for common view

**Verdict:** Premature optimization for current scale, but harmless and good learning.

### Table Design Choices

| Relationship | Pattern | Why |
|--------------|---------|-----|
| Account → Transaction | Foreign key | Clear ownership |
| Account → Position | Foreign key | Clear ownership |
| Tag ↔ Transaction | Association table | Many-to-many, no extra data |
| TradeGroup ↔ Transaction | Association table | Many-to-many, no extra data |
| LinkedTrade ↔ Transaction | Association object | Many-to-many WITH allocated_quantity |

**All choices are correct** for their use cases.

---

## 6. Recommendations

### High Priority (Do Next)

**1. Remove unused code**
- ❌ Delete TradeGroup model, router, service (unused feature)
- ❌ Delete trade_group_transactions association table
- ❌ Remove trade_groups relationship from Transaction model
- ✅ Reduces maintenance burden, clarifies codebase intent

**2. Migrate to filter objects**
- ✅ Refactor transaction_service.py to use TransactionFilter from filters.py
- ✅ Update routers/transactions.py to build filter objects
- ✅ Good learning opportunity for clean service APIs

**3. Standardize HTMX response handling**
- Use htmx_response() helper in transactions.py:175 for consistency
- Minor cleanup, improves readability

### Medium Priority (Consider)

**4. Refactor calculation patterns**
- Extract pure calculation functions from linked_trade_service.py
- Example: calculate_pl_from_legs(legs) separate from get_linked_trade_pl(db, id)
- Benefit: Better testability

**5. Add LinkedTradeFilter usage**
- Currently exists in filters.py but not used by linked_trade_service.py
- Apply same pattern as TransactionFilter migration

### Low Priority (Nice to Have)

**6. Consider calculation module**
- Create app/calculations/ package
- Move all pure calculation functions there
- Benefit: Clear separation, but YAGNI for current scale

**7. Document denormalization**
- Add comments to LinkedTradeLeg explaining why trade_date/price are denormalized
- Helps future maintainers understand trade-off

---

## Learning Outcomes

### Patterns Demonstrated

✅ **Service layer architecture** - Clean separation of routes (HTTP) from business logic
✅ **Repository pattern** (implicit) - Services encapsulate data access
✅ **Association object pattern** - LinkedTradeLeg as rich join table
✅ **Intentional denormalization** - Performance trade-offs documented
✅ **Query builder pattern** - Filter functions in filters.py

### Anti-patterns Avoided

✅ Fat models (business logic stays in services)
✅ Fat controllers (routes delegate to services)
✅ Premature abstraction (utilities are minimal)

### Anti-patterns Present

⚠️ Dead code (filters.py unused, trade_groups unused)
⚠️ Inconsistent patterns (inline vs object filters)

---

## Scalability Notes

**Current architecture scales well to:**
- ✅ 1-10 users
- ✅ 10K-100K transactions
- ✅ Daily data refresh cycles

**Would need changes for:**
- Real-time price updates → Add caching layer
- 100+ concurrent users → Connection pooling, read replicas
- Multi-tenancy → Row-level security, tenant_id on all tables
- Microservices → API versioning, event-driven sync

**For personal/small team use: Current design is appropriate and well-architected.**

---

## Next Steps

1. ✅ Review this document
2. Delete trade_groups feature (models, routers, services)
3. Migrate to TransactionFilter pattern
4. Standardize HTMX response handling
5. Consider calculation pattern refactor

## Questions Unresolved

None - all initial questions addressed.
