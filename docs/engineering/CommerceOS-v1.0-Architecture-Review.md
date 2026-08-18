# CommerceOS v1.0 Architecture Review & Stabilisation

**Date:** 2026-07-29  
**Scope:** Epic 1–4 completed; pre-Epic-5 engineering stabilisation pass.  
**Author:** Hermes Agent (CommerceOS engineering review)

---

## Executive Summary

CommerceOS v1.0 is a local-first, event-driven operational platform for managing a Shopee store. After four epics of active development, the codebase had accumulated structural debt: a circular dependency between ingestion and connectors, inconsistent timezone handling, a large number of legacy root-level scripts, and mixed messaging in operational acceptance tests. This review stabilised the foundation without implementing new product features.

The architecture is now sound enough for Epic 5 work. Dependency direction is enforced, time handling is centralised, legacy scripts are archived, and all automated verification passes.

**Architecture Health Score: 8.2 / 10**

Rationale: bounded contexts are well separated, tests pass, and operational flows are verified. The score is not 10 because repository duplication, global settings singleton, and some legacy adapters remain intentionally in place to avoid breaking changes before Epic 5.

---

## Architecture Overview

CommerceOS follows a layered, bounded-context architecture:

```
Marketplace API
      ↓
Shopee Connector
      ↓
Ingestion / Sync Engine
      ↓
Canonical Commerce Models (orders, products, inventory, ads, campaigns)
      ↓
KPI Engine / Commerce State
      ↓
Monitoring → Intelligence → Decision → Execution → Events
      ↓
Dashboard Query Service + Domain Dashboards
      ↓
Knowledge / Reporting / Telegram / Cron
```

Key principles:
- Bounded contexts own their models and repositories.
- Streamlit pages and scripts consume only service/dashboard APIs.
- Marketplace mutations go through the execution engine after approval.
- Secrets are centralised in `token_manager.py` / `SecretManager`.
- Knowledge layer owns Obsidian generation; full content stays in Markdown files, metadata in SQLite.

---

## Bounded Context Review

| Context | Responsibility | Public API | Dependencies | Status |
|---------|---------------|------------|--------------|--------|
| `platform` | Settings, DB connection, secrets, tokens | `Settings`, `get_session`, `SecretManager` | pydantic, keyring, SQLAlchemy | ✅ Stable |
| `connectors` | Marketplace-specific adapters | `ShopeeConnector`, mappers, `ConnectorResult` | `platform`, `commerce`, `connectors.core` | ✅ Stable |
| `connectors.core` | Shared connector primitives | `MarketplaceConnector`, `Mapper`, `CanonicalEntity` | `platform` | ✅ New shared kernel |
| `ingestion` | Sync engine, raw payloads, provenance, checkpoints | `SyncEngine`, UoW repositories | `platform`, `connectors.core` | ✅ Stable |
| `commerce` | Canonical entities | `Order`, `Product`, `Campaign`, etc. | `platform` | ✅ Stable |
| `kpi` | Materialised KPIs and commerce state | `KPIEngine.refresh`, `CommerceState` | `commerce`, `ingestion`, `platform` | ✅ Stable |
| `monitoring` | Health checks, alerts, snapshots | `MonitoringService`, `MonitoringDashboard` | `commerce`, `connectors`, `ingestion`, `kpi`, `platform` | ✅ Stable |
| `intelligence` | Trends, anomalies, explainers | `IntelligenceEngine`, `IntelligenceDashboard` | `commerce`, `kpi`, `platform` | ✅ Stable |
| `decision` | Rule-based recommendations, approval | `DecisionEngine`, `ApprovalWorkflow` | `commerce`, `kpi`, `platform` | ✅ Stable |
| `execution` | Safe plan → execute → audit → rollback | `ExecutionEngine`, `ExecutionDashboard` | `decision`, `platform` | ✅ Stable |
| `events` | Event bus, workflows, locks, dead letters | `EventBus`, `LockManager`, `WorkflowEngine` | `platform` | ✅ Stable |
| `dashboard` | Stable read APIs | `DashboardQueryService` | `commerce`, `ingestion`, `kpi`, `platform` | ✅ Stable |
| `knowledge` | Notes, vault, retrieval, retention | `KnowledgeReporter`, `KnowledgeDashboard`, `RetrievalEngine` | `dashboard`, `decision`, `events`, `execution`, `intelligence`, `monitoring`, `platform` | ✅ Stable |
| `jobs` | Automation runtime | `JobRegistry`, `JobRunner`, `JobHealthReporter` | `config`, `dashboard`, `decision`, `events`, `execution`, `intelligence`, `knowledge`, `monitoring`, `platform` | ✅ Stable |
| `reporting` | Reporting inventory and router | `REPORT_INVENTORY`, `get_latest_canonical_report` | `config`, `knowledge`, `platform` | ✅ Stable |
| `telegram` | COO channel summaries | `TelegramNotifier`, `COOReporter` | `config` | ✅ Stable |
| `closed_loop` | Decision outcomes and lessons | `OutcomeTracker` | `config`, `decision`, `execution`, `knowledge`, `platform` | ✅ Stable |

---

## Dependency Analysis

### Direction

Dependencies flow from infrastructure → data → intelligence → decision → execution → knowledge → reporting/interfaces. No domain layer depends on UI or reporting.

### Circular Dependency Resolved

- **Issue:** `connectors/shopee/mappers.py` imported `CanonicalEntity` and `Mapper` from `ingestion.sync_engine`, while `ingestion.sync_engine` imported `MarketplaceConnector` from `connectors.core.interfaces`.
- **Fix:** Moved `CanonicalEntity` and `Mapper` to `connectors.core.mapper` as a shared kernel. Both ingestion and connector mappers now import from the shared kernel.
- **Result:** No circular pairs detected in the import graph.

### Hidden Dependencies

None discovered that would break architecture. `LegacyFinancialAdapter` still imports the archived `financial_engine.py` but is explicitly documented as a removal candidate.

---

## Technical Debt Classification

### HIGH — Fixed

1. **Circular dependency connectors ↔ ingestion**  
   - Impact: could block module import ordering and test isolation.  
   - Action: created `connectors.core.mapper` shared kernel.

2. **Inconsistent UTC timestamp creation**  
   - Impact: 162 inline `datetime.now(timezone.utc)` calls; risk of naive/offset bugs.  
   - Action: replaced with `utc_now()` from `shared.value_objects.primitives` across `commerceos/`, `scripts/`, `pages/`.

3. **Legacy root-level scripts competing with canonical paths**  
   - Impact: 15 deprecated scripts (`daily_monitor.py`, `growth_engine.py`, `auto_optimizer.py`, etc.) confused the operational surface.  
   - Action: archived into `archive/legacy_scripts/`. Updated reporting inventory and secret regression tests.

### MEDIUM — Documented

1. **Global settings singleton** (`settings = Settings()` in `config.settings`)  
   - Impact: makes isolated configuration in tests and multi-tenant runs harder.  
   - Action: not changed; replace with a factory when multi-tenancy or stricter test isolation is needed.

2. **Duplicate reporter implementations** (`write_daily_report`, `format_daily_report` across `intelligence/`, `execution/`, `decision/`, `events/`, `monitoring/` reporters)  
   - Impact: similar Markdown formatting logic repeated.  
   - Action: not changed; consolidate into a shared Markdown formatter when the next reporter is added.

3. **Duplicate severity helpers** (`severity_rank`, `worst_severity` in `monitoring`, `intelligence`, `decision`)  
   - Impact: same logic pattern repeated for different enum types.  
   - Action: not changed; each is type-specific. Could be unified with a generic helper later.

### LOW — Documented

1. **`LegacyFinancialAdapter` in `dashboard.query_service`** still imports archived financial engine.  
   - Removal criterion: `DashboardQueryService` PL metrics match legacy output within ±0.5% for 3 consecutive days.

2. **No Alembic migrations**; standalone migration scripts under `commerceos/knowledge/migrations/` and `commerceos/closed_loop/migrations/`.  
   - Acceptable for single-tenant SQLite; revisit before PostgreSQL or multi-node deployment.

3. **Streamlit `app.py` and legacy pages** not fully migrated to Mission Control.  
   - Functional but not maintained; planned retirement in Epic 5 or a dedicated UI work package.

4. **`KnowledgeMemory._derive_lessons` and `_derive_follow_ups`** are placeholders.  
   - Pending richer decision/execution history and AI assistance (Epic 5+).

---

## API Consistency Review

| Area | Observation | Action |
|------|-------------|--------|
| Repository interfaces | Abstract `Repository` + `UnitOfWork` pattern is consistent across all bounded contexts. | ✅ None |
| Service return types | Services return domain models or dicts; dashboards return dicts. | ✅ None |
| Exceptions | Custom exceptions in `platform.exceptions` and `connectors.core.errors`; no broad silent swallowing. | ✅ None |
| Timestamps | Centralised to `utc_now()` for new code. Legacy data remains in tables. | ✅ Fixed |
| Timezone handling | `DashboardQueryService.get_freshness()` already handles offset-naive timestamps. | ✅ Stable |
| DTOs | `ConnectorResult`, `TelegramDelivery`, and `Money`/`Percentage`/`DateRange` are typed. | ✅ Stable |
| Settings | `Settings` is global; `get_settings()` is used everywhere. | ⚠️ Documented as MEDIUM debt |

---

## Operational Readiness Review

### Scheduler and Automation Runtime

- `JobRegistry` + `JobRunner` execute registered jobs and record `JobExecution` history.
- `JobRunner.run()` rolls back only on failure so the job log can still be committed.
- Handlers are idempotent: daily/weekly/monthly briefs update existing metadata rather than duplicating.
- `run_scheduled_jobs.py` is the cron entrypoint.
- `JobHealthReporter` detects overdue jobs and recent failures.

### Telegram Integration

- `TelegramNotifier` is disabled when `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` is missing.
- Returns a failed `TelegramDelivery` record instead of crashing.
- `COOReporter` builds concise morning/evening summaries; full detail remains in Obsidian.

### Operational Acceptance Testing

- `scripts/oat_verification.py` now distinguishes:
  - `operational_flow.monitoring_active` — snapshot exists.
  - `operational_flow.monitoring_healthy` — overall status is `healthy`.
- Reports PASS/FAIL with actionable findings.
- On empty database, correctly reports FAIL with clear reasons.

### Closed-Loop Learning

- `OutcomeTracker` records decision outcomes, execution feedback, and promotes successful outcomes to knowledge lesson notes.
- Verified by `scripts/closed_loop_smoke.py`.

### Idempotency and Recovery

- No in-memory state required; cron re-invocation naturally resumes.
- Sync checkpoints are resume-safe.
- Knowledge note metadata is idempotent by deterministic note IDs.

---

## Refactors Performed

1. Created `commerceos/connectors/core/mapper.py` with `CanonicalEntity` and `Mapper`.
2. Updated `connectors/shopee/mappers.py` and `ingestion/sync_engine.py` to import from shared kernel.
3. Replaced ~162 inline `datetime.now(timezone.utc)` calls with `utc_now()` in 72 files across `commerceos/`, `scripts/`, `pages/`.
4. Archived 15 legacy root-level scripts to `archive/legacy_scripts/`.
5. Updated `commerceos/reporting/consolidation.py` paths to reference archived scripts.
6. Updated `tests/unit/test_secrets_regression.py` active file list.
7. Updated `commerceos/dashboard/query_service.py` `LegacyFinancialAdapter` import to archived path.
8. Improved `scripts/oat_verification.py` messaging and added `operational_flow.monitoring_healthy` check.
9. Updated `tests/unit/oat/test_oat_verification.py` to assert new check exists.

---

## Remaining Technical Debt

See "Technical Debt Classification" above. The main items are:

- Global settings singleton.
- Duplicate reporter helpers.
- `LegacyFinancialAdapter` still depends on archived engine.
- No Alembic migrations.
- Legacy Streamlit pages.
- Placeholder lesson derivation in `KnowledgeMemory`.

---

## Risks Before Epic 5

| Risk | Severity | Mitigation |
|------|----------|------------|
| Legacy scripts still in `archive/legacy_scripts/` could be re-run by old cron entries or muscle memory. | MEDIUM | Update `CRON_SETUP.md`; run `crontab -l` to remove old entries. |
| Global settings singleton complicates multi-tenant or isolated test runs. | MEDIUM | Use `monkeypatch` in tests; introduce settings factory when needed. |
| `LegacyFinancialAdapter` may drift from canonical P&L logic. | LOW | Validate against canonical output for 3 days before removing. |
| No Alembic migration tooling. | LOW | Current SQLite single-tenant model is fine; add Alembic before PostgreSQL. |
| Telegram disabled by default; COO may not notice if notifications stop working. | LOW | OAT and job logs surface disabled state; add a heartbeat check if needed. |

---

## Recommendations

1. **Before Epic 5 begins:** audit the host crontab and remove any entries pointing to archived scripts.
2. **Next technical debt sprint:** introduce a settings factory and remove the global `settings` singleton.
3. **After 3 days of validated P&L:** remove `LegacyFinancialAdapter` and the archived financial engine.
4. **When adding a new reporter:** consolidate Markdown formatting into a shared helper.
5. **Before production PostgreSQL:** add Alembic migrations and replace standalone migration scripts.
6. **Epic 5 focus:** marketplace growth execution (campaign budget scaling, product boosts) with human approval still required.

---

## Architecture Health Score

**8.2 / 10**

### Breakdown

- Bounded context separation: 9/10
- Dependency direction: 9/10 (circular dependency resolved)
- Repository / UoW consistency: 9/10
- Test coverage / regression: 9/10 (276 tests passing)
- Operational readiness: 8/10 (OAT, job runtime, Telegram verified)
- Configuration hygiene: 6/10 (global singleton remains)
- Legacy surface cleanliness: 7/10 (scripts archived, adapter remains)
- Documentation currency: 8/10 (review document created, docs updated)

---

## Final Recommendation

**CommerceOS v1.0 Approved for Epic 5.**

The foundation is stable: dependency direction is correct, timezone handling is centralised, legacy clutter is archived, and all verification passes. The remaining technical debt is documented and does not block marketplace growth execution work. No additional broad refactoring should be undertaken before Epic 5 begins.
