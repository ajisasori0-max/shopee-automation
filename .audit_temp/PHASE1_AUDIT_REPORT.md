# Phase 1 Structural Audit — CommerceOS v1.0

**Repository:** `/Users/gerard/.openclaw/workspace/shopee-api-onboarding`  
**Date:** 2026-07-30  
**Scope:** Structural audit only — no fixes applied.

---

## 1. Bounded Contexts vs ARCHITECTURE.md

ARCHITECTURE.md (`docs/ARCHITECTURE.md`) lists **10 core bounded contexts**:

- platform, ingestion, commerce, monitoring, intelligence, decision, execution, events, dashboard, connectors

The actual `commerceos/` tree contains **28 top-level contexts**:

- advertising, agents, api, application, cli, closed_loop, commerce, config, connectors, dashboard, decision, events, execution, finance, ingestion, intelligence, jobs, knowledge, kpi, monitoring, platform, reporting, rules, shared, state, sync, telegram, workflows

### Findings

- All 10 documented contexts are present.
- **18 extra contexts exist** that are not in ARCHITECTURE.md. Likely intentional growth, but undocumented.
- **11 contexts are `__init__.py`-only shells** (no non-init Python files):
  - `commerceos/advertising/`
  - `commerceos/agents/`
  - `commerceos/api/`
  - `commerceos/application/`
  - `commerceos/cli/`
  - `commerceos/commerce/`
  - `commerceos/finance/`
  - `commerceos/rules/`
  - `commerceos/state/`
  - `commerceos/sync/`
  - `commerceos/workflows/`

### Root cause

Several planned contexts appear reserved but unimplemented. `commerceos/commerce/` is particularly notable: `commerceos/commerce/models/__init__.py` has the full canonical entity model, but the top-level package is empty.

---

## 2. Circular Dependencies & Dead Imports

### Circular imports

- **No Python circular import cycles detected** by static import-graph analysis.
- However, runtime import of individual modules in isolation reveals **SQLAlchemy duplicate-table / duplicate-model warnings** because the same modules are imported multiple times in the audit runner. This is an artifact of isolated reloading, not necessarily a production bug, but it indicates models are loaded eagerly by many modules.
- One real runtime error observed:
  - `commerceos/monitoring/service.py` raises `KeyError: 'commerceos.monitoring'` when imported standalone. This should be investigated; likely due to a registry lookup that assumes package import order.

### Dead imports

Many imports flagged as "possibly dead" by static name-usage analysis. The most operationally relevant are:

- `commerceos/dashboard/query_service.py:24` — imports `Ad`, `Campaign`, `CommerceState`, `OrderItem`, `Product`, `Store` from `commerceos.commerce.models` but does not appear to reference those names directly.
- `commerceos/ingestion/__init__.py` re-exports many symbols that may be dead package re-exports.
- `pages/mission_control.py` imports many dashboard helpers that appear unused.
- `scripts/wp2_6_verify.py` imports event symbols that are unused.
- Multiple `__init__.py` files re-export classes for public API convenience, which registers as dead by naive static analysis. These are **not** necessarily bugs but indicate broad public surface areas.

The full list is in the script output at `.audit_temp/phase1_audit_v2.py` output.

---

## 3. Active Imports from `archive/legacy_scripts/`

Active production code that imports from the archive:

- `commerceos/dashboard/query_service.py:465`
  ```python
  from archive.legacy_scripts.financial_engine import ShopeeFinancialEngine
  ```

This is inside `LegacyFinancialAdapter`, which is explicitly marked for removal, but it means the dashboard package still depends on archived code. ARCHITECTURE.md constraint #4 says `token_manager.py` is the only production token path, yet the legacy financial engine has its own auth/client logic.

---

## 4. Duplicated Classes / Functions Across Contexts

### Exact duplicates (same name, different contexts)

1. **`Mapper`**
   - `commerceos/connectors/core/mapper.py:31`
   - `commerceos/ingestion/sync_engine.py:84`
   - Root cause: `sync_engine.py` redefines its own abstract `Mapper` instead of importing from `connectors.core.mapper`. Creates two different base classes for the same concept.

2. **`TelegramNotifier`**
   - `commerceos/monitoring/notifiers/telegram.py:20`
   - `commerceos/telegram/notifier.py:41`
   - Root cause: two separate Telegram notifier implementations exist. `monitoring` context has one; standalone `telegram` context has another. Risk of divergence and configuration conflicts.

3. **`get_access_token`**
   - `commerceos/connectors/shopee/auth.py:65`
   - `commerceos/platform/tokens.py:30`
   - Root cause: token retrieval exists both in the connector-specific auth module and in the central platform module. ARCHITECTURE.md says `token_manager.py` (root) / `platform.tokens` should be the only supported path.

### Other notable name collisions

- `SyncEngine` exists only in `commerceos/ingestion/sync_engine.py` — not duplicated, but ingestion code also imports from connectors.
- `ShopeeApiClient` only in `commerceos/connectors/shopee/client.py`.

---

## 5. Root Directory Scripts

48 Python files live directly in the repository root. Categorized:

### Debug scratch scripts (18)

- `auth_debug.py`
- `debug_ads.py`
- `debug_api.py`
- `debug_api_call.py`
- `debug_api_response.py`
- `debug_campaign_details.py`
- `debug_campaigns.py`
- `debug_check.py`
- `debug_evening.py`
- `debug_evening_check.py`
- `debug_monitor.py`
- `debug_resp.py`
- `debug_response.py`
- `debug_seller_token.py`
- `evening_check_debug.py`
- `evening_debug.py`
- `midday_check_debug.py`
- `midday_debug.py`

### Test / validation scripts (9)

- `check_ads.py`
- `check_token.py`
- `test_ads_api.py`
- `test_api.py`
- `test_boost.py`
- `test_connection.py`
- `test_financial_engine.py`
- `test_order_create.py`
- `test_orders_simulated.py`

### Auth setup / helper scripts (5)

- `auth_helper.py`
- `auth_multi.py`
- `auth_sandbox.py`
- `auth_webhook.py`
- `generate_auth_url.py`

### Demo / one-off (1)

- `demo.py`

### Production-ish operational scripts (15)

- `ads_app.py`
- `app.py` (main Streamlit app, 1,076 lines, 45 KB)
- `automation.py` (461 lines, legacy automation)
- `competitor_scraper.py`
- `dashboard.py`
- `diag_api.py`
- `generate_fallback_report.py`
- `midday_check_final.py`
- `midday_check_run.py`
- `midday_prod.py`
- `pause_non_hero_campaigns.py`
- `shopee_monitor.py`
- `streamlit_app.py`
- `token_manager.py` (438 lines, production token manager)
- `update_roas_targets.py`

### Root cause

The root directory is a dumping ground for legacy and scratch scripts. ARCHITECTURE.md notes: *“Old scripts in the root (`daily_monitor.py`, `full_automation.py`, etc.) are legacy and being retired.”* The audit shows many debug/test/auth scripts are still present and executable.

---

## 6. Summary of Issues

| # | Issue | File(s) / Line(s) | Severity |
|---|-------|---------------------|----------|
| 1 | 11 bounded contexts are empty `__init__.py` shells | `commerceos/{advertising,agents,api,application,cli,commerce,finance,rules,state,sync,workflows}/__init__.py` | Medium |
| 2 | 18 undocumented extra contexts not in ARCHITECTURE.md | `commerceos/*` | Low |
| 3 | Active archive import in production dashboard code | `commerceos/dashboard/query_service.py:465` | High |
| 4 | Two `Mapper` abstractions | `commerceos/connectors/core/mapper.py:31`, `commerceos/ingestion/sync_engine.py:84` | Medium |
| 5 | Two `TelegramNotifier` classes | `commerceos/monitoring/notifiers/telegram.py:20`, `commerceos/telegram/notifier.py:41` | Medium |
| 6 | Two `get_access_token` functions | `commerceos/connectors/shopee/auth.py:65`, `commerceos/platform/tokens.py:30` | Medium |
| 7 | 48 root-level scripts, including 18 debug scratch files and 14 test/auth scripts | repository root | Low-Medium |
| 8 | `MonitoringService` standalone import failure (`KeyError`) | `commerceos/monitoring/service.py` | Medium |
| 9 | Broad dead-import surface in `__init__.py` re-exports and dashboard pages | many | Low |
| 10 | SQLAlchemy duplicate Base class warnings under isolated import | all model modules | Low (investigate) |

---

## Files Created / Modified

- Created `.audit_temp/phase1_audit.py` (static-only version)
- Created `.audit_temp/phase1_audit_v2.py` (runtime import + static version)
- Created `.audit_temp/PHASE1_AUDIT_REPORT.md` (this report)

No source files in the repository were modified.

---

## Recommendations (for Phase 2)

1. Remove or relocate root debug/test/auth scripts to `archive/` or `tests/manual/`.
2. Resolve `LegacyFinancialAdapter` → archive dependency; either migrate P&L logic into CommerceOS canonical services or isolate the adapter behind a feature flag.
3. Consolidate `Mapper` abstractions: have `ingestion` import from `connectors.core.mapper`.
4. Consolidate `TelegramNotifier` into a single notifier in `commerceos/telegram/` used by all contexts.
5. Route all token retrieval through `commerceos/platform/tokens.py`; deprecate `ShopeeAuth.get_access_token`.
6. Decide whether empty contexts should be implemented, removed, or documented as planned.
7. Investigate `MonitoringService` `KeyError: 'commerceos.monitoring'` on standalone import.
