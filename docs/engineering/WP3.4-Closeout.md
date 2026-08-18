# WP3.4 — Operational SOP Engine Closeout

## Completed

1. **SOP Engine core** (`commerceos/sop/engine.py`)
   - Deterministic, versioned, enable/disable-able SOP definitions.
   - Four built-in SOPs:
     - LOW_STOCK — inventory velocity, days of cover, lead time, PO recommendation.
     - ROAS_COLLAPSE — campaign spend, ROAS trend, traffic/conversion diagnosis, historical comparison, action recommendation.
     - REVENUE_DROP — revenue/orders/traffic/conversion/advertising/stock/price diagnosis.
     - CASH_PRESSURE — cash position, upcoming bills, inventory requirements, operational cash delta, projected balance.
   - Safe condition evaluator, SOP execution result, and concrete runners.
   - Data-honest collection: missing inputs (cash balance, price history) are reported explicitly.

2. **Persistence & auditability**
   - `SOPDefinitionRecord` and `SOPExecutionRecord` models.
   - Repository + Unit-of-Work pattern in `commerceos/sop/sqlalchemy_repositories.py`.
   - SOP executions recorded after every run.

3. **Decision Engine integration**
   - `DecisionEngine.refresh_sop_recommendations()` persists SOP recommendations as `Decision` records.
   - Deduplicates against existing open decisions by title.
   - Metadata marks source as `sop_engine`.

4. **Automation runtime integration**
   - New job `sop_engine_run` registered in `commerceos/jobs/factory.py`.
   - Handler added in `commerceos/jobs/handlers.py`.
   - Schedule hint: daily 08:15, idempotency key = date.

5. **CLI entry point**
   - `scripts/run_sop_engine.py`.

6. **Tests**
   - 14 unit tests in `tests/unit/sop/test_sop_engine.py`.
   - 2 integration tests in `tests/integration/test_sop_engine_integration.py`.
   - Covers trigger correctness, branch logic, missing data, approval flags, idempotency, and Decision Engine wiring.

7. **Migration script**
   - `commerceos/sop/migrations/001_create_sop_tables.sql`.
   - SOP models are also registered in `Base.metadata` via a soft import in `commerceos/ingestion/models.py`, so `create_all()` creates the tables automatically.

## Tests

```bash
source .venv/bin/activate
python -m pytest tests/unit/sop/test_sop_engine.py tests/integration/test_sop_engine_integration.py -q
# -> 16 passed

python -m pytest tests/unit/ -q
# -> 267 passed

python -m pytest tests/integration/ -q
# -> 29 passed
```

## Architecture Decisions

- SOP logic is **code-first** to keep business rules inspectable, deterministic, and version-controlled.
- LLMs are not used for SOP execution; they may later explain outputs, but branches and recommendations are rule-derived.
- Missing data is explicitly surfaced in `missing_inputs` rather than synthesized.
- SOPs do **not** execute marketplace mutations directly; they feed the existing Decision/Execution engine.
- Recommendations are deduplicated by title against open `Decision` records to avoid spam on repeated runs.
- SOP executions are always recorded, even when no decision is created.

## Known Issues / Trade-offs

- Cash balance is not directly available; CASH_PRESSURE SOP reports it as missing.
- Price change history is not available; REVENUE_DROP SOP reports it as missing.
- Lead time is currently a default 7-day assumption. Per-SKU lead time will be added when supplier data is modeled.
- ROAS collapse uses overall ROAS; SKU-level ad performance breakdown is a future enhancement.

## Next Step

Proceed to **WP3.5 — COO Interface**.
