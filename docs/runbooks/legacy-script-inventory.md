# Legacy Script Inventory — Token Governance Consolidation

**Date:** 2026-07-24  
**Goal:** Identify every executable script that touches Shopee tokens, classify it, and record the consolidation action.

---

## Classification Legend

- **Active** — currently used in cron or daily ops; must be migrated to the central token provider.
- **Read-only compatibility** — debug/utility scripts that only read token files; keep but must not refresh/write.
- **Archive** — historical scripts with no active use; move to `archive/` for reference.
- **Delete** — dangerous duplicates (independent refreshers) that directly conflict with token governance.

---

## Migration Matrix

| File | Lines | Class | Owner/Purpose | Token Action | Consolidation Action | Replacement / Notes |
|------|-------|-------|---------------|--------------|----------------------|---------------------|
| `token_manager.py` | 413 | **Authority** | Central token authority | read, refresh, write | Keep as single source of truth | `commerceos.platform.tokens` is the public API |
| `commerceos/platform/tokens.py` | 52 | **Provider** | Public token provider for all other code | read (delegated) | Keep; newly created | `get_access_token(app_name)` |
| `scripts/live_resync.py` | 125 | Active | E1.3/E1.4 live full sync | read | Already migrated to central provider | Force-refreshes via `token_manager` before sync |
| `daily_monitor.py` | 444 | Active | 8 AM daily monitor cron | read + self-refresh | **Migrated** today | `ShopeeAPI` now calls central provider |
| `growth_engine.py` | 930 | Active | 9 AM growth engine cron | read + self-refresh | **Migrated** today | `ShopeeAPI` now calls central provider |
| `daily_growth_run.sh` | — | Active | Cron wrapper for growth_engine | none | **Migrated** today | Uses `.venv`; no independent refresh |
| `auto_optimizer.py` | 443 | Active | Ad campaign auto-optimizer | read + self-refresh/write | **Migrate** — patch `ShopeeAPI` to use central provider | To be deprecated by commerceos advertising module |
| `semi_auto_optimizer.py` | 261 | Active | Semi-automatic campaign optimizer | read + self-refresh/write | **Migrate** — patch `ShopeeAPI` to use central provider | To be deprecated by commerceos advertising module |
| `simple_optimizer.py` | 180 | Active | Simple campaign optimizer | read + self-refresh/write | **Migrate** — patch `ShopeeAPI` to use central provider | To be deprecated by commerceos advertising module |
| `full_automation.py` | 417 | Active | Combined seller + ads automation | read + self-refresh | **Migrate** — patch token helper to use central provider | Replace with commerceos workflow engine |
| `shopee_client.py` | 345 | Active | Legacy generic API client | read + self-refresh | **Migrate** — add deprecation warning and delegate refresh to central provider | Used by many scripts; keep wrapper, remove refresh |
| `app.py` | 1171 | Active | Streamlit auth/helper UI | read + exchange + self-refresh/write | **Migrate** — make exchange button call `token_manager.py --exchange` and remove direct writes | Keep UI, delegate token logic |
| `pause_non_hero_campaigns.py` | 35 | Active | Campaign pause helper | read only | **Read-only compatibility** | Safe once `shopee_client.py` is migrated |
| `update_roas_targets.py` | 40 | Active | ROAS target updater | read only | **Read-only compatibility** | Safe once `shopee_client.py` is migrated |
| `apply_approved.py` | 119 | Active | Apply approved automation actions | read only | **Read-only compatibility** | Safe once `shopee_client.py` is migrated |
| `financial_engine.py` | 744 | Active | Financial reporting engine | read only | **Read-only compatibility** | Will be replaced by commerceos finance module |
| `monthly_report.py` | — | Active | Monthly report generator | read only | **Read-only compatibility** | Will be replaced by commerceos reporting module |
| `competitor_scraper.py` | — | Active | Competitor scraper (no tokens) | none | **Read-only compatibility** | No token impact |
| `exchange_auth_codes.py` | 75 | Utility | Manual auth-code exchange | read | **Delete** after documenting equivalent CLI | Superseded by `token_manager.py --exchange` |
| `generate_auth_url.py` | — | Utility | Generate OAuth URLs | none | **Keep as utility** but centralize under `commerceos` CLI | Safe; only signs URLs |
| `get_production_token.py` | — | Utility | Get production token | read + exchange/write | **Delete** | Superseded by `token_manager.py` |
| `get_token.py` | — | Utility | Generic token getter/exchanger | read + exchange/write | **Delete** | Superseded by `token_manager.py` |
| `refresh_token.py` | 33 | **Danger** | Standalone ads token refresher | read + refresh + write | **Delete** | Directly conflicts with token governance |
| `refresh_tokens.py` | 35 | **Danger** | Standalone ads token refresher | read + refresh + write | **Delete** | Directly conflicts with token governance |
| `refresh_prod.py` | 34 | **Danger** | Standalone production token refresher | read + refresh | **Delete** | Directly conflicts with token governance |
| `refresh_ads_token.py` | 34 | **Danger** | Standalone ads token refresher | read + refresh + write | **Delete** | Directly conflicts with token governance |
| `refresh_and_check.py` | 67 | **Danger** | Refresh + check script | read + refresh + write | **Delete** | Directly conflicts with token governance |
| `update_tokens.py` | 31 | **Danger** | Updates token file manually | read + write | **Delete** | Directly conflicts with token governance |
| `evening_check_full.py` | 75 | **Danger** | Evening check with self-refresh | read + refresh + write | **Delete** | Superseded by commerceos + token_manager |
| `midday_check_full.py` | 61 | **Danger** | Midday check with self-refresh | read + refresh + write | **Delete** | Superseded by commerceos + token_manager |
| `auth_debug.py` | — | Debug | OAuth debug | none | **Archive** | Not used in production |
| `auth_helper.py` | — | Debug | OAuth helper | none | **Archive** | Not used in production |
| `auth_multi.py` | — | Debug | Multi-auth experiments | none | **Archive** | Not used in production |
| `auth_sandbox.py` | — | Debug | Sandbox auth | none | **Archive** | Not used in production |
| `auth_webhook.py` | — | Debug | Webhook auth | none | **Archive** | Not used in production |
| `check_ads.py` | 50 | Debug | Quick ads token check | read | **Archive** | Superseded by `token_manager.py --health` |
| `check_token.py` | 7 | Debug | Quick token check | read | **Archive** | Superseded by `token_manager.py --health` |
| `debug_ads.py` | 28 | Debug | Debug ads API | read | **Archive** | Superseded by commerceos tools |
| `debug_api.py` | 27 | Debug | Debug API | read | **Archive** | Superseded by commerceos tools |
| `debug_api_call.py` | 32 | Debug | Debug API call | read | **Archive** | Superseded by commerceos tools |
| `debug_api_response.py` | 27 | Debug | Debug API response | read | **Archive** | Superseded by commerceos tools |
| `debug_campaign_details.py` | 35 | Debug | Debug campaign details | read | **Archive** | Superseded by commerceos tools |
| `debug_campaigns.py` | 24 | Debug | Debug campaigns | read | **Archive** | Superseded by commerceos tools |
| `debug_check.py` | 27 | Debug | Debug check | read | **Archive** | Superseded by commerceos tools |
| `debug_evening.py` | 27 | Debug | Debug evening | read | **Archive** | Superseded by commerceos tools |
| `debug_evening_check.py` | 27 | Debug | Debug evening check | read | **Archive** | Superseded by commerceos tools |
| `debug_freshness.py` | 21 | Debug | Debug freshness | read | **Archive** | Superseded by `scripts/verify_kpis.py` |
| `debug_monitor.py` | 31 | Debug | Debug monitor | read | **Archive** | Superseded by commerceos tools |
| `debug_refresh.py` | 26 | Debug | Debug refresh | read + refresh | **Delete** | Directly conflicts with token governance |
| `debug_resp.py` | 28 | Debug | Debug response | read | **Archive** | Superseded by commerceos tools |
| `debug_response.py` | 27 | Debug | Debug response | read | **Archive** | Superseded by commerceos tools |
| `debug_seller_token.py` | 23 | Debug | Debug seller token | read | **Archive** | Superseded by `token_manager.py --health` |
| `diag_api.py` | 36 | Debug | Diagnose API | read | **Archive** | Superseded by commerceos tools |
| `evening_check.py` | — | Debug | Evening check stub | read | **Archive** | Superseded by commerceos tools |
| `evening_check_debug.py` | 28 | Debug | Evening check debug | read | **Archive** | Superseded by commerceos tools |
| `evening_debug.py` | 27 | Debug | Evening debug | read | **Archive** | Superseded by commerceos tools |
| `midday_check.py` | — | Debug | Midday check stub | read | **Archive** | Superseded by commerceos tools |
| `midday_check_debug.py` | 21 | Debug | Midday check debug | read | **Archive** | Superseded by commerceos tools |
| `midday_check_final.py` | 46 | Debug | Midday check final | read | **Archive** | Superseded by commerceos tools |
| `midday_check_run.py` | 40 | Debug | Midday check run wrapper | read | **Archive** | Superseded by commerceos tools |
| `midday_debug.py` | 28 | Debug | Midday debug | read | **Archive** | Superseded by commerceos tools |
| `midday_prod.py` | 26 | Debug | Midday prod check | read | **Archive** | Superseded by commerceos tools |
| `send_evening_check.py` | — | Debug | Send evening check | read | **Archive** | Superseded by commerceos tools |
| `send_growth_report.py` | — | Debug | Send growth report | read | **Archive** | Superseded by commerceos reporting |
| `send_midday_check.py` | — | Debug | Send midday check | read | **Archive** | Superseded by commerceos tools |
| `test_ads_api.py` | — | Test | Manual ads API test | read | **Archive** | Superseded by unit/integration tests |
| `test_all_apis.py` | — | Test | Manual API test | read | **Archive** | Superseded by unit/integration tests |
| `test_api.py` | — | Test | Manual API test | read | **Archive** | Superseded by unit/integration tests |
| `test_boost.py` | — | Test | Manual boost test | read | **Archive** | Superseded by tests |
| `test_connection.py` | — | Test | Manual connection test | read | **Archive** | Superseded by tests |
| `test_financial_engine.py` | — | Test | Manual financial engine test | read | **Archive** | Superseded by tests |
| `test_order_create.py` | — | Test | Manual order create test | read | **Archive** | Superseded by tests |
| `test_orders_simulated.py` | — | Test | Simulated order test | read | **Archive** | Superseded by tests |
| `test_tokens.py` | — | Test | Manual token test | read + refresh | **Delete** | Directly conflicts with token governance |
| `automation.py` | — | Legacy | Early automation stub | read | **Archive** | Superseded by commerceos automation |
| `dashboard.py` | — | Legacy | Early dashboard | read | **Archive** | Superseded by `streamlit_app.py` + `pages/` |
| `demo.py` | — | Legacy | Demo script | none | **Archive** | Not production |
| `generate_fallback_report.py` | — | Legacy | Fallback report | read | **Archive** | Superseded by commerceos reporting |
| `shopee_monitor.py` | — | Legacy | Early monitor | read + self-refresh? | **Migrate or Archive** | Verify usage; likely superseded by `daily_monitor.py` |
| `setup_cron.sh` | — | Legacy | Old cron setup | none | **Delete** | Replaced by Hermes cron jobs |
| `cron_scripts/*.sh` | — | Legacy | Old cron wrappers | none | **Delete** | Replaced by Hermes cron jobs |

---

## Summary Counts

| Class | Count |
|-------|-------|
| Authority / Provider | 2 |
| Active (to keep, migrated) | 14 |
| Read-only compatibility | 6 |
| Archive | ~46 |
| Delete | ~12 |

---

## Critical Deletions (Independent Token Refreshers)

These files must be removed **first** because they directly invalidate Shopee refresh tokens:

1. `refresh_token.py`
2. `refresh_tokens.py`
3. `refresh_prod.py`
4. `refresh_ads_token.py`
5. `refresh_and_check.py`
6. `update_tokens.py`
7. `debug_refresh.py`
8. `test_tokens.py`
9. `evening_check_full.py`
10. `midday_check_full.py`
11. `exchange_auth_codes.py` (after documenting CLI equivalent)
12. `get_production_token.py`
13. `get_token.py`

## Active Migration Priority

1. `shopee_client.py` — many scripts depend on it; migrate its refresh logic to central provider.
2. `auto_optimizer.py`, `semi_auto_optimizer.py`, `simple_optimizer.py` — patch `ShopeeAPI` classes.
3. `full_automation.py` — patch token helper.
4. `app.py` — replace direct exchange/write with calls to `token_manager` CLI or module.
5. `financial_engine.py`, `monthly_report.py` — read-only; safe after `shopee_client.py` migration.

---

## Post-Consolidation Validation

After all changes:

- Run `python3 token_manager.py --health` — both healthy.
- Run repository scan for forbidden patterns (refresh/write outside `token_manager.py`) — must pass.
- Run `FULL_RESYNC=1 python3 scripts/live_resync.py` — succeeds.
- Run `python3 scripts/refresh_kpis.py` — succeeds.
- Resume cron jobs in phases, observing token health between each.
