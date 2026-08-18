# Epic 5 — Business Intelligence & Forecasting Closeout

## Completed

### WP5.1 Advanced Analytics (`commerceos/analytics/engine.py`)
- SKU-level profitability: units, gross/net revenue, marketplace fees, advertising cost, contribution margin, explicit COGS missing note.
- Campaign-level profitability: spend, revenue, ROAS, clicks, conversions, CPA.
- Revenue decomposition: orders, AOV, gross/net revenue, discounts.
- Customer repeat behavior and cohort analysis reported as unavailable because Shopee data lacks customer identity.
- 4 analytics tests passing.

### WP5.2 Demand Forecasting (`commerceos/analytics/forecasting.py`)
- `ForecastPoint` and `ForecastResult` value objects with confidence levels (none, low, medium, high).
- Naive, moving average, linear trend, and seasonal (weekly) forecast methods.
- Sales forecast, SKU-level demand forecast, ad-spend forecast, and revenue forecast.
- 3 forecasting tests passing.

### WP5.3 Inventory Intelligence (`commerceos/analytics/inventory.py`)
- Daily velocity per SKU from historical order lines.
- Days of stock remaining and stockout risk within `days_ahead`.
- Restock recommendations with projected need and explicit lead-time defaults.
- 2 inventory tests passing.

### WP5.4 Financial Forecasting (`commerceos/analytics/finance.py`)
- Actual P&L: revenue, marketplace fees, advertising, gross profit, operating profit (COGS missing).
- Cash-flow forecast with explicit opening-cash missing note.
- 2 financial tests passing.

### WP5.5 Scenario Engine (`commerceos/analytics/scenarios.py`)
- Predefined scenarios: ad-spend increase, sales decline, supplier delay, new SKU launch, price change.
- Baseline vs scenario delta computed using forecasting and inventory engines.
- Extensible `run(scenario_type, params)` dispatcher.
- 4 scenario tests passing.

### Analytics Dashboard (`commerceos/analytics/dashboard.py`)
- `AnalyticsDashboard` aggregates analytics, forecasts, inventory, finance, and scenarios into a single API.
- Suitable for Streamlit page or COO query context.

## Tests

```bash
source .venv/bin/activate
python -m pytest tests/unit/analytics/test_analytics.py -q
# -> 14 passed

python -m pytest tests/unit/ tests/integration/ -q
# -> 343 passed
```

## Architecture Decisions

- All analytics engines are deterministic and code-first; no LLM synthesis of business data.
- Missing dimensions (COGS, customer identity, opening cash balance) are reported explicitly in `notes` and `missing_inputs` rather than fabricated.
- Forecast confidence is computed from historical data length and volatility; low data returns `confidence: none`.
- Scenario engine reuses forecasting and inventory engines so deltas stay consistent with operational models.
- Ad-spend attribution is proportional to SKU revenue in analytics; marketplace fees are allocated by revenue share.

## Known Issues / Trade-offs

- COGS is not modeled in canonical tables; gross and contribution margins are before COGS.
- Customer-level data is unavailable; repeat behavior and cohorts are not computed.
- Opening cash balance is not persisted; cash forecasts require manual input or a future ledger.
- Lead time defaults to 7 days; per-supplier lead times are not yet modeled.
- No Alembic migration for analytics tables; they rely on existing canonical tables only.

## Next Step

Epic 5 is closed. The continuous WP3.4 → WP3.5 → Epic 4 → Epic 5 pipeline is complete. Reconcile ROADMAP.md and consider next priorities (e.g., operational hardening, multi-marketplace, or UI consolidation) before starting Epic 6.
