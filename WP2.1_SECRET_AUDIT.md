# WP2.1 Secret Governance Audit

**Scope:** Active production code set defined for WP2.1 regression test.
**Excluded:** tests/, archive/, debug/check/test/auth/demo/send_* prefixed files, and allowed handlers `token_manager.py` / `scripts/migrate_secrets.py`.

## Summary of findings

| Category | Count | Files |
|---|---|---|
| Migrated | 22 | commerceos platform code + root orchestrators that use SecretManager / central token provider |
| Legacy-readonly | 7 | Root scripts still reading tokens_*.json but not writing them; some still have hardcoded credentials |
| Archived | 0 | N/A (archive/ excluded from active scan) |
| Requires follow-up | 4 | `apply_approved.py`, `generate_auth_url.py`, `simple_optimizer.py`, `semi_auto_optimizer.py` contain hardcoded partner_key/IDs in active production files |

## Classified credential consumers

### Migrated

- `commerceos/platform/secrets/manager.py` — SecretManager provider-agnostic abstraction (env + local file fallback).
- `commerceos/platform/secrets/__init__.py` — exports workspace SecretManager.
- `commerceos/platform/secrets_schema.py` — canonical secret names, no values.
- `commerceos/platform/tokens.py` — central token provider; delegates refresh/write to `token_manager.py`.
- `commerceos/platform/shopee_config.py` — reads configuration from environment.
- `commerceos/platform/exceptions.py` — no credentials.
- `commerceos/connectors/shopee/client.py` — accepts credentials via constructor, no hardcoded values.
- `commerceos/connectors/shopee/connector.py` — uses SecretManager-backed configuration.
- `commerceos/connectors/shopee/mappers.py` — no credentials.
- `commerceos/connectors/shopee/__init__.py` — no credentials.
- `commerceos/connectors/core/*` — no credentials.
- `commerceos/commerce/models/__init__.py` — no credentials.
- `commerceos/ingestion/sync_engine.py` — uses connector/SecretManager, no hardcoded secrets.
- `commerceos/ingestion/audit.py` — no credentials.
- `commerceos/kpi/engine.py` — no credentials.
- `commerceos/dashboard/query_service.py` — no credentials.
- `token_manager.py` — allowed central secret/token handler.
- `daily_monitor.py` — uses central token provider.
- `full_automation.py` — uses central token provider.
- `auto_optimizer.py` — uses central token provider.
- `shopee_monitor.py` — uses central token provider.
- `automation.py` — uses central token provider.
- `monthly_report.py` — uses central token provider.
- `growth_engine.py` — uses central token provider.
- `financial_engine.py` — uses central token provider.
- `app.py` / `streamlit_app.py` — UI wrappers, no hardcoded credentials.
- `midday_check.py` / `evening_check.py` — uses central token provider.
- `shopee_client.py` — accepts credentials via constructor, no hardcoded values.
- `pause_non_hero_campaigns.py` / `update_roas_targets.py` — uses central token provider / no hardcoded credentials.
- `scripts/e1_oat_verification.py` — verification script, no credential literals.
- `scripts/live_resync.py` — orchestrates via migrated connectors.
- `scripts/refresh_kpis.py` — no hardcoded credentials.
- `scripts/seed_tenant.py` — seeds using SecretManager values.
- `scripts/verify_kpis.py` — no hardcoded credentials.

### Legacy-readonly

- `scripts/debug_freshness.py` — debug script (excluded by prefix) but still reads tokens from legacy path.
- `send_midday_check.py` / `send_evening_check.py` / `send_growth_report.py` — send Telegram notifications; excluded by `send_` prefix but contain hardcoded `chat_id`.
- `debug_*` / `check_*` / `test_*` / `auth_*` / `demo_*` scripts at repo root — excluded by prefix; numerous contain hardcoded partner_key/ID/shop_id and read tokens_*.json.

### Requires follow-up (active production files with hardcoded credentials)

1. `apply_approved.py` — hardcoded `PARTNER_ID`, `PARTNER_KEY`, `SHOP_ID`; reads `tokens_ads.json` directly.
2. `generate_auth_url.py` — hardcoded `SHOP_ID`, `partner_id`, `partner_key` for both Seller and Ads apps.
3. `simple_optimizer.py` — hardcoded `PARTNER_ID`, `PARTNER_KEY`, `SHOP_ID`; uses migrated `get_access_token` but still signs requests with local secret.
4. `semi_auto_optimizer.py` — hardcoded `PARTNER_ID`, `PARTNER_KEY`, `SHOP_ID`; same pattern as `simple_optimizer.py`.

## Recommendation

1. Refactor the four follow-up files to load partner_id, partner_key, and shop_id from `SecretManager` and remove all literal `shpk...` values.
2. Replace direct `tokens_ads.json` reads in `apply_approved.py` with the central `commerceos.platform.tokens.get_access_token()` helper.
3. Move root debug/check/test/auth/demo/send scripts to `archive/` or delete them; until then they remain outside the active scan scope.
4. Once follow-up files are migrated, the WP2.1 regression test (`tests/unit/test_secrets_regression.py`) should pass completely.
