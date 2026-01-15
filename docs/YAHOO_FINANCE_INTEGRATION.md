# Yahoo Finance Integration Plan

Replace Finnhub API with a Yahoo Finance library for market data.

---

## Proxy Configuration

**Requirement:** All Yahoo Finance API calls must be routed through a configurable proxy.

### Configuration

Add to `app/config.py`:
- `yahoo_proxy_url: str = ""` - HTTP/HTTPS proxy URL (e.g., `http://proxy.example.com:8080`)

Add to `.env`:
- `YAHOO_PROXY_URL=http://your-proxy:port`

### Why Proxy?

1. **Network policy compliance** - Corporate/production environments often require proxy routing
2. **Rate limit mitigation** - Rotate IPs to avoid throttling
3. **Geographic access** - Some Yahoo endpoints have regional restrictions
4. **Monitoring** - Centralized logging of outbound API calls

### Library Support

- **yfinance:** Supports proxy via `Ticker(symbol, proxy={"http": url, "https": url})`
- **yahooquery:** Supports proxy via `Ticker(symbols, proxy=url)`

---

## Data Elements

### Stock Quotes (Immediate Need)

| Field | Source | Storage | Usage |
|-------|--------|---------|-------|
| Current Price | `fast_info.last_price` | `Position.current_price` | Market value calculation |
| Previous Close | `fast_info.previous_close` | `Position.previous_close` | Daily change % |

### Options Pricing (Phase 2)

| Field | Source | Storage | Usage |
|-------|--------|---------|-------|
| Bid | `option_chain()` | `Position.option_bid` | Current market bid |
| Ask | `option_chain()` | `Position.option_ask` | Current market ask |
| Implied Volatility | `option_chain()` | `Position.implied_vol` | Risk assessment |
| Last Price | `option_chain()` | `Position.current_price` | Mark-to-market |

**Note:** Options require fetching by underlying symbol + expiration + strike. OCC symbols (e.g., `AAPL250117C00150000`) need parsing.

### Historical Prices (Phase 3)

| Field | Source | Storage | Usage |
|-------|--------|---------|-------|
| OHLCV | `history(period="1y")` | New `PriceHistory` table | Charts, performance analysis |
| Adjusted Close | `history()` | `PriceHistory.adj_close` | Total return calculations |

**Storage Options:**
- Separate `PriceHistory` table (symbol, date, open, high, low, close, volume, adj_close)
- Or use time-series database for large datasets

---

## Data Flow

### Current Flow (Finnhub)

```
User clicks "Refresh" → Router → market_data_service.get_quote()
                                         ↓
                              Check in-memory cache
                                         ↓
                              Finnhub API (if cache miss)
                                         ↓
                              Update Position.current_price
                                         ↓
                              Render updated UI
```

### Proposed Flow (Yahoo Finance + Scheduler)

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                                │
│  Yahoo Finance API (via proxy)                                   │
│  - Stock quotes: fast_info                                       │
│  - Options: option_chain()                                       │
│  - History: history()                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MARKET DATA SERVICE                           │
│  app/services/market_data_service.py                            │
│                                                                  │
│  get_quotes_batch(symbols) → {symbol: QuoteData}                │
│  get_options_quote(underlying, expiry, strike, type)            │
│  get_price_history(symbol, period)                              │
│                                                                  │
│  In-memory cache (5-min TTL for quotes)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATABASE                                   │
│                                                                  │
│  Position table                                                  │
│  - current_price, previous_close (stocks)                       │
│  - option_bid, option_ask, implied_vol (options)                │
│                                                                  │
│  PriceHistory table (new)                                       │
│  - symbol, date, open, high, low, close, volume, adj_close      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       UI LAYER                                   │
│                                                                  │
│  Positions view: market value, daily change                     │
│  Account cards: total value, daily G/L                          │
│  Charts: historical performance (Phase 3)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Workflow Integration

### Background Scheduler (APScheduler)

**Trigger:** Periodic job during market hours

**Schedule Options:**
- Every 15 minutes during market hours (9:30 AM - 4:00 PM ET)
- Every hour outside market hours (for after-hours pricing)
- Daily historical data refresh (once per day after market close)

### Scheduler Job Flow

```
1. APScheduler triggers refresh job
         ↓
2. Query all accounts with positions
         ↓
3. Collect unique stock symbols (exclude money market)
         ↓
4. Batch fetch quotes via get_quotes_batch()
         ↓
5. Update Position.current_price, previous_close
         ↓
6. Collect option positions with valid OCC symbols
         ↓
7. Fetch options data by underlying/expiry/strike
         ↓
8. Update Position.option_bid, option_ask, implied_vol
         ↓
9. Log refresh summary (updated/failed/skipped counts)
```

### Manual Refresh (Keep Existing)

- User clicks "Refresh Prices" button
- Immediately triggers same refresh logic
- Shows result: "X updated, Y skipped, Z failed"

### Cache Strategy

| Data Type | Cache TTL | Rationale |
|-----------|-----------|-----------|
| Stock quotes | 5 minutes | Balance freshness vs rate limits |
| Options pricing | 5 minutes | Same as stocks |
| Historical data | 24 hours | Only changes once per day |

---

## Library Comparison

| Feature | **yfinance** | **yahooquery** | **market_prices** |
|---------|-------------|----------------|-------------------|
| GitHub Stars | 20,800 | 893 | 93 |
| Projects Using | 85,600+ | ~1,400 | minimal |
| Contributors | 138 | 8 | 2 |
| Latest Release | v1.0 (Dec 2025) | v2.4.1 (May 2025) | v0.12.11 (Oct 2025) |
| Proxy Support | Yes | Yes | Via yahooquery |
| Options Data | Yes | Yes | No |
| Historical Data | Yes | Yes | Yes |
| Batch Queries | Yes | Yes | No |

### yfinance (Recommended)

**Repository:** https://github.com/ranaroussi/yfinance

**Pros:**
- Most popular (85k+ projects), fast bug fixes
- Full feature set: quotes, options chains, history
- Native proxy support
- Lightweight dependencies

**Cons:**
- Unofficial API - could break
- Rate limiting under heavy use

### yahooquery

**Repository:** https://github.com/dpguthrie/yahooquery

**Pros:**
- Clean API, built-in async
- Direct API access (not scraping)

**Cons:**
- Smaller community
- Less documentation

### market_prices

**Repository:** https://github.com/maread99/market_prices

**Pros:**
- Excellent OHLCV handling
- Multi-exchange support

**Cons:**
- Tiny community (2 contributors)
- Heavyweight, no async

---

## Recommendation: yfinance

1. **Full feature coverage** - quotes, options, history all in one library
2. **Proxy support** - Native configuration for corporate environments
3. **Battle-tested** - 85k+ projects, mature v1.0 release
4. **Options chains** - Can price option positions via `option_chain()`
5. **Lightweight** - Minimal dependencies

---

## Database Schema Changes

### Position Table Updates

Add columns for options pricing:
- `option_bid: Decimal(18,4)` - Current bid price
- `option_ask: Decimal(18,4)` - Current ask price
- `implied_vol: Decimal(8,4)` - Implied volatility (e.g., 0.3250 = 32.5%)

### New Table: PriceHistory

For historical price data (charts/performance):
- `id: int` (PK)
- `symbol: str` (indexed)
- `date: date` (indexed)
- `open: Decimal`
- `high: Decimal`
- `low: Decimal`
- `close: Decimal`
- `adj_close: Decimal`
- `volume: int`

Unique constraint on (symbol, date).

---

## Files to Modify

| File | Changes |
|------|---------|
| `app/config.py` | Add `yahoo_proxy_url` setting |
| `app/services/market_data_service.py` | Replace Finnhub with yfinance, add proxy, batch, options |
| `app/models/position.py` | Add `option_bid`, `option_ask`, `implied_vol` columns |
| `app/models/price_history.py` | New model for historical data |
| `app/services/scheduler_service.py` | New service for APScheduler jobs |
| `app/routers/accounts.py` | Update docstrings |
| `.env.example` | Replace `MARKET_DATA_API_KEY` with `YAHOO_PROXY_URL` |
| `alembic/versions/` | Migration for new columns/table |

---

## Risk Mitigation

### Yahoo API Risks

- Unofficial API - could change/break
- Rate limiting under heavy use
- Regional restrictions

### Mitigation

1. **Proxy configuration** - Route through controlled infrastructure
2. **Abstraction layer** - `get_quote()` isolates provider details
3. **Graceful degradation** - Failed quotes don't crash the app
4. **Error logging** - Monitor API failures
5. **Fallback option** - Keep Finnhub code for emergency rollback

---

## Implementation Phases

### Phase 1: Core Migration
- [ ] Add yfinance dependency
- [ ] Add `yahoo_proxy_url` to config
- [ ] Replace `get_quote()` with yfinance + proxy
- [ ] Add `get_quotes_batch()` function
- [ ] Update `refresh_position_prices()` to use batch
- [ ] Update docs and `.env.example`

### Phase 2: Options Pricing
- [ ] Add `option_bid`, `option_ask`, `implied_vol` to Position model
- [ ] Create migration
- [ ] Add `get_options_quote()` function
- [ ] Update refresh to include option positions
- [ ] Display options pricing in UI

### Phase 3: Historical Data
- [ ] Create `PriceHistory` model and migration
- [ ] Add `get_price_history()` function
- [ ] Add daily history refresh job
- [ ] Build chart components for UI

### Phase 4: Background Scheduler
- [ ] Add APScheduler dependency
- [ ] Create `scheduler_service.py`
- [ ] Configure periodic refresh jobs
- [ ] Add market hours awareness
- [ ] Add scheduler status to admin UI

---

## Testing Plan

1. Unit tests with mocked yfinance responses
2. Test proxy configuration handling
3. Test batch fetch with multiple symbols
4. Test options chain parsing
5. Test historical data retrieval and storage
6. Test scheduler job execution
7. Manual UI testing
8. Test with invalid/delisted symbols
