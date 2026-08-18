# Stale Scheduler References & Archived Production Dependencies Report

Generated: 2026-08-11

## 1. Host crontab stale entries

`crontab -l` currently schedules these scripts from the project root:

| Entry | Interval | Script | Status |
|-------|----------|--------|--------|
| 1 | `*/15 * * * *` | `/usr/local/bin/python3 full_automation.py` | **BROKEN** — file moved to `archive/legacy_scripts/full_automation.py` |
| 2 | `0 9 * * *` | `/usr/local/bin/python3 auto_optimizer.py` | **BROKEN** — file moved to `archive/legacy_scripts/auto_optimizer.py` |
| 3 | `0 */4 * * *` | `/usr/local/bin/python3 shopee_monitor.py --check stock` | **STALE** — legacy script; not archived under `archive/legacy_scripts/` but is root-level legacy |
| 4 | `0 */6 * * *` | `/usr/local/bin/python3 shopee_monitor.py --check orders` | **STALE** — same as above |
| 5 | `0 8 * * *` | `/usr/local/bin/python3 shopee_monitor.py --check prices` | **STALE** — same as above |
| 6 | `0 9 * * *` | `/usr/local/bin/python3 shopee_monitor.py --check ads` | **STALE** — same as above |
| 7 | `0 10 * * *` | `/usr/local/bin/python3 shopee_monitor.py --check growth` | **STALE** — same as above |
| 8 | `59 23 29 * *` | `/usr/local/bin/python3 monthly_report.py` | **BROKEN** — file moved to `archive/legacy_scripts/monthly_report.py` |

All entries use absolute project paths but point to scripts that no longer exist at those locations.
`semi_auto_optimizer.py` is **not in the live crontab**, but `cron_semi_auto.txt` still documents it as if active.

## 2. Project-root cron_* files still using archived paths

- `cron_full_automation.txt` line 8: `... python3 full_automation.py ...`
- `cron_optimizer.txt` line 4: `... python3 auto_optimizer.py ...`
- `cron_semi_auto.txt` line 6: `... python3 semi_auto_optimizer.py ...`
- `shopee_cron.txt` line 20: `... python3 monthly_report.py ...`
- `CRON_SETUP.md` line 27: `... python3 monthly_report.py ...`
- `setup_cron.sh` line 40: `$WORKSPACE/monthly_report.py`

These files are stale documentation/setup artifacts. They should either be updated to point to the current canonical scripts or removed.

## 3. commerceos/jobs/factory.py

File: `/Users/gerard/.openclaw/workspace/shopee-api-onboarding/commerceos/jobs/factory.py`

- Status: **OK** from stale-reference perspective.
- Uses canonical handlers from `commerceos/jobs/handlers.py`.
- No archived-script imports.
- All imports resolve to current package paths.

## 4. commerceos/jobs/handlers.py

File: `/Users/gerard/.openclaw/workspace/shopee-api-onboarding/commerceos/jobs/handlers.py`

- Status: **OK** from stale-reference perspective.
- Imports `DashboardQueryService` from `commerceos.dashboard.query_service`.
- Does **not** import `LegacyFinancialAdapter`.
- Uses `MonitoringService`, `KnowledgeReporter`, and current dashboard abstractions.

## 5. LegacyFinancialAdapter (commerceos/dashboard/__init__.py and query_service.py)

Files:
- `/Users/gerard/.openclaw/workspace/shopee-api-onboarding/commerceos/dashboard/__init__.py`
- `/Users/gerard/.openclaw/workspace/shopee-api-onboarding/commerceos/dashboard/query_service.py` (lines 456–503)

Findings:
- `commerceos/dashboard/__init__.py` exports `LegacyFinancialAdapter`.
- `LegacyFinancialAdapter.__init__` imports `ShopeeFinancialEngine` from `archive.legacy_scripts.financial_engine` (`archive/legacy_scripts/financial_engine.py` line 465).
- This is an archived production dependency actively surfaced through a public package export.
- The class docstring states it is "marked for removal once DashboardQueryService PL metrics are validated against legacy output for 3 consecutive days."
- No occurrences of `LegacyFinancialAdapter` were found in `commerceos/jobs/handlers.py` or `commerceos/reporting/consolidation.py`; it is exported but not currently consumed by operational jobs.

## 6. commerceos/reporting/consolidation.py

File: `/Users/gerard/.openclaw/workspace/shopee-api-onboarding/commerceos/reporting/consolidation.py`

- Status: **documentation-only** file (`REPORT_INVENTORY`).
- Lists deprecated paths, including:
  - `archive/legacy_scripts/financial_engine.py`
  - `archive/legacy_scripts/monthly_report.py`
  - legacy `send_*.py` scripts
- These paths are explicitly marked deprecated in the inventory itself.
- No active imports or runtime references to archived scripts.

## 7. Other stale references discovered

- `cron_scripts/run_ad_optimizer.sh`: references `auto_optimizer.py` in root.
- `cron_scripts/run_boost.sh`: references `full_automation.py` in root.
- `cron_scripts/run_monthly.sh`: references `monthly_report.py` in root.
- `cron_scripts/run_daily_report.sh`: imports from `full_automation` in root.
- `test_boost.py`: imports from `full_automation` in root.
- `archive/scripts/test_tokens.py`: imports from root `full_automation` (now stale even within archive context).
- `archive/debug_scripts/pause_non_hero_campaigns.py` and `update_roas_targets.py`: import from root `full_automation`.
- `docs/PROJECT_STATE.md` already notes that host crontab still references archived `full_automation.py` and `auto_optimizer.py` and generates log noise.

## 8. Recommended actions

1. **Clean host crontab** — remove or replace entries 1, 2, 3–7, 8 above. The active ingestion entrypoint is now `scripts/sync_then_refresh.py`; the active operational-cycle entrypoint is `scripts/run_scheduled_jobs.py`.
2. **Update or delete** stale cron documentation/setup files:
   - `cron_full_automation.txt`
   - `cron_optimizer.txt`
   - `cron_semi_auto.txt`
   - `shopee_cron.txt`
   - `CRON_SETUP.md`
   - `setup_cron.sh`
   - `cron_scripts/run_*.sh`
3. **Remove or deprecate `LegacyFinancialAdapter`** export from `commerceos/dashboard/__init__.py` once the documented 3-day validation criterion is satisfied; until then, the archived `financial_engine.py` import remains a production-archived dependency.
4. **Inventory root-level legacy scripts** (`shopee_monitor.py`, `full_automation.py`, etc. are already documented in `docs/runbooks/legacy-script-inventory.md`) and either archive them or replace their crontab entries.
