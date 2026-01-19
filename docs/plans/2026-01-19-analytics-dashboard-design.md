# Analytics Dashboard Design

**Issue:** [#3 - Portfolio metrics dashboard with P/L charts and analytics](https://github.com/Collint25/PortfolioTracker/issues/3)

**Scope:** MVP — summary cards + P/L over time chart, extensible foundation

## Decisions

| Decision | Choice |
|----------|--------|
| Page location | New `/analytics` route |
| Charting library | Chart.js via CDN |
| Computation | On-demand, leveraging existing `pl_calcs.py` |
| MVP chart | P/L over time (line chart) |
| Filtering | Account selector + date range with presets |

## Architecture

### Data Flow

```
/analytics request
  → analytics router
  → metrics_service.get_metrics(accounts, start_date, end_date)
    → lot_service.get_pl_summary() (extended with date params)
    → pl_calcs.pl_over_time() (new function)
    → position aggregation for unrealized P/L
  → MetricsResult returned
  → template renders cards + Chart.js
```

### Files to Modify

**`app/services/lot_service.py`**
- Add `start_date`, `end_date` params to `get_pl_summary()`
- Filter TradeLot query by close date range

**`app/calculations/pl_calcs.py`**
- Add `pl_over_time(lots) -> list[dict]` — cumulative P/L by date
- Fix type hint: `LinkedTrade` → `TradeLot`

### Files to Create

**`app/services/metrics_service.py`**
```python
@dataclass
class MetricsSummary:
    total_realized_pl: Decimal
    total_unrealized_pl: Decimal
    win_rate: float              # 0.0 to 1.0
    total_trades: int
    winning_trades: int
    losing_trades: int

@dataclass
class PLDataPoint:
    date: date
    cumulative_pl: Decimal

@dataclass
class MetricsFilter:
    account_ids: list[int] | None
    start_date: date | None
    end_date: date | None

@dataclass
class MetricsResult:
    summary: MetricsSummary
    pl_over_time: list[PLDataPoint]
    filters_applied: MetricsFilter

def get_metrics(
    db: Session,
    account_ids: list[int] | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> MetricsResult:
    ...
```

**`app/routers/analytics.py`**
- `GET /analytics` — full page or partial (HX-Request check)
- Handle filter params: `account_ids`, `start_date`, `end_date`, `preset`
- Presets: YTD, MTD, 90 days, all time

**`app/templates/analytics.html`**
- Extends base.html
- Filter panel (account dropdown, date inputs, preset buttons)
- Content area with `#analytics-content` for HTMX swaps

**`app/templates/partials/metrics_cards.html`**
- DaisyUI `stat` components in grid
- Total P/L, Win Rate, Trade Count, Unrealized P/L

**`app/templates/partials/pl_chart.html`**
- `<canvas id="pl-chart">`
- Inline `<script>` for Chart.js initialization
- Receives `pl_data_json` from router

## UI Layout

```
┌─────────────────────────────────────────────────────────┐
│  Analytics                              [Filter Panel]  │
│                                    Account: [Dropdown]  │
│                                    Date: [From] - [To]  │
│                          [YTD] [MTD] [90 Days] [All]    │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Total PL │  │ Win Rate │  │  Trades  │  │Unrealzd │ │
│  │ +$12,345 │  │   63%    │  │   142    │  │ +$2,100 │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
├─────────────────────────────────────────────────────────┤
│           P/L Over Time (Line Chart)                    │
│     $│                                    ___/          │
│      │                              ___--/              │
│      │                        __--/                     │
│      └──────────────────────────────────────────        │
│                        Time →                           │
└─────────────────────────────────────────────────────────┘
```

## Chart.js Integration

Load via CDN in analytics.html:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
```

Inline script in partial (re-runs on HTMX swap):
```javascript
const plData = {{ pl_data_json | safe }};
new Chart(document.getElementById('pl-chart'), {
  type: 'line',
  data: {
    labels: plData.map(d => d.date),
    datasets: [{
      label: 'Cumulative P/L',
      data: plData.map(d => d.cumulative_pl),
      borderColor: plData.at(-1)?.cumulative_pl >= 0 ? '#22c55e' : '#ef4444',
      fill: false
    }]
  },
  options: {
    responsive: true,
    scales: { y: { ticks: { callback: v => '$' + v.toLocaleString() } } }
  }
});
```

## HTMX Behavior

- Filter changes → `hx-get="/analytics"` with params
- `hx-target="#analytics-content"` for partial swap
- Router checks `HX-Request` header:
  - Present → return partials only
  - Absent → return full page
- URL params reflect filters (bookmarkable)

## Extensibility

Future additions require minimal changes:

| Feature | Changes |
|---------|---------|
| New metric (avg win/loss) | Add field to `MetricsSummary`, update cards partial |
| New chart (monthly bars) | Add data to `MetricsResult`, new partial template |
| P/L by symbol | Add `symbol_breakdown: list[SymbolPL]` to result |
| Caching | Swap service internals, API unchanged |

## Unresolved Questions

None — design ready for implementation.
