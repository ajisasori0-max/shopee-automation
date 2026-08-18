# CHANGELOG.md

Historical record of completed work packages for the Shopee / CommerceOS project.
Do not edit active work package details here; update PROJECT_STATE.md instead.

## 2026-08-12 — Web COO Dashboard COMPLETE

- Built single orchestration service `commerceos/coo/web_service.py` (`WebCOODashboardService`) that exposes all dashboard data to Streamlit pages.
- Evolved existing `pages/mission_control.py` into the new Command Center; added 9 new focused pages:
  - Intelligence (`pages/intelligence.py`)
  - Decisions (`pages/decisions.py`) with approve/reject buttons wired to canonical `ApprovalWorkflow`
  - Executions (`pages/executions.py`)
  - Knowledge (`pages/knowledge.py`) with search and timeline
  - SOP & Rules (`pages/sop_rules.py`) surfacing deterministic SOP definitions and policy rules
  - Experiments (`pages/experiments.py`) with read-only scenario runner
  - Operations (`pages/operations.py`) for sync, jobs, health, alerts, dead letters
  - Analytics (`pages/analytics.py`) for SKU/campaign profitability, inventory, sales forecast
  - Timeline (`pages/timeline.py`) unifying events, executions, decisions, knowledge, sync
- Streamlit pages are presentation-only; no business logic, no direct SQL, no marketplace mutation bypass.
- Added graceful empty/stale/error states throughout; cached database session via `@st.cache_resource`.
- Fixed `AdvancedAnalyticsEngine` date comparison and Decimal casting for campaign and SKU profitability queries.
- Replaced deprecated `use_container_width=True` with `width='stretch'` across all dashboard pages to remove Streamlit deprecation warnings.
- Full regression: 343 tests passing.
- Streamlit app launched and verified on port 8501; Command Center and Intelligence pages rendered with navigation.
- Sync + KPI refresh smoke test succeeded: all domains synced, 369 KPIs refreshed.
- OAT smoke test passed after sync refresh.
- SOP engine smoke test: all 4 SOPs evaluated, 0 applicable (expected: ROAS healthy, stock coverage above threshold).
- Evidence: `docs/engineering/CommerceOS-Web-COO-Dashboard-Closeout.md`.
- Next: choose next epic (Epic 6 multi-store, Epic 7 production hardening, or UI/operational hardening).

## 2026-08-11 — Final Stabilization & Roadmap Reconciliation

- Fixed `ad_performances` UNIQUE constraint failure by normalizing DateTime natural keys to `datetime.date` in `commerceos/ingestion/sync_engine.py` and using `func.date(col)` in `_resolve_existing_ids`.
- Added `tests/unit/test_ad_performance_idempotent.py` proving first insert, idempotent second run, value update, and no duplicate canonical rows.
- Removed root-level debug/auth/test scratch scripts containing hardcoded Shopee `partner_key` values.
- Tightened `.gitignore` to exclude `tokens_*.json`, root debug/auth scratch files, and `.streamlit/secrets.toml`.
- Removed `tokens_ads.json` and `tokens_production.json` from the git index (local runtime files remain).
- Removed duplicate `commerceos/monitoring/notifiers/telegram.py`; canonical notifier remains `commerceos/telegram/notifier.py`.
- Removed stale Hermes cron jobs: `shopee-growth-engine`, `shopee-daily-monitor`, `shopee-midday-check`, `shopee-evening-check`.
- Documented host crontab stale entries requiring manual `crontab -r` (macOS TCC blocks programmatic removal).
- Removed `LegacyFinancialAdapter` from the dashboard public API, eliminating the active import of archived `financial_engine.py`.
- Adjusted OAT `knowledge_flow.recent_notes` to distinguish a healthy quiet knowledge period from a broken knowledge layer; OAT now passes 8/8 on the populated production database.
- Verified end-to-end incremental sync + KPI refresh with `scripts/sync_then_refresh.py`; all six domains succeeded, no duplicate `ad_performances` rows, 357 KPIs refreshed.
- Full regression: 280 tests passing.
- Updated `docs/ROADMAP.md` with canonical roadmap reconciliation and `docs/ARCHITECTURE.md` with natural-key normalization note.
- Created `docs/engineering/CommerceOS-Stabilization-Closeout.md`.
- Next canonical WP: **WP3.4 Operational SOP Engine**.

## 2026-07-30 — Cronjob Infrastructure Hotfix

- Fixed `shopee-midday-check`, `shopee-evening-check`, and `shopee-daily-monitor` cron prompts to run archived legacy scripts using `.venv/bin/python3` with `PYTHONPATH`.
- Fixed `e1-oat-verification` cron prompt to use `.venv/bin/python3` + `PYTHONPATH`.
- Fixed import order in `scripts/e1_oat_verification.py` so `commerceos` is resolvable before first use.
- Verified `shopee-token-health` and `shopee-growth-engine` jobs remain healthy.
- E1 OAT now executes but reports stale sync checkpoints (~28h); the CommerceOS sync pipeline has not run recently and needs scheduling or a manual run.

## 2026-07-30 — CommerceOS Sync Pipeline Restored

- Root cause: the old host crontab still pointed to archived `full_automation.py`/`auto_optimizer.py`, and the new Hermes scheduler had no job running `scripts/live_resync.py`, so ingestion stopped after 2026-07-29 03:23.
- Added `scripts/sync_then_refresh.py` wrapper that runs incremental sync (`FULL_RESYNC=0`) and immediately refreshes KPIs/CommerceState only on success.
- Patched `scripts/live_resync.py` to invoke Alembic via `sys.executable -m alembic` so it works when called from the venv Python without an explicit shell activation.
- Created Hermes scheduler job `shopee-sync` (every 4h) running `scripts/sync_then_refresh.py`.
- Verified end-to-end: sync updated all `sync_checkpoints`, `kpi-refresh` ran immediately after, `e1_oat_verification` passed, and `pytest tests` returned 276 passing.
- Host crontab cleanup attempted but the current environment's `crontab` command hangs/times out; the stale entries are documented as remaining technical debt.

## 2026-07-25 — Epic 2 CLOSED

- WP2.1 Secret Management: migrated credentials to SecretManager, removed hardcoded secrets from active scripts.
- WP2.2 Monitoring Layer: 24 health checks, alerts, snapshots, scheduler health.
- WP2.3 Intelligence Foundation: trends, anomalies, explainers, insights.
- WP2.4 Decision Engine v1: rule-based recommendations with approval workflow.
- WP2.5 Execution Engine v1: dry-run → plan → execute → audit → rollback.
- WP2.6 Event Bus & Workflow Orchestration: event-driven workflows, dead letters, locks.
- Regression: 194 tests passing.
- Evidence: `docs/engineering/E2-Closeout-Report.md`

## 2026-07-29 — WP3.0 CLOSED

- Built Mission Control (`pages/mission_control.py`) as unified COO workspace.
- Consumed only existing APIs: DashboardQueryService, MonitoringDashboard, IntelligenceDashboard, DecisionDashboard, ExecutionDashboard, EventsDashboard.
- No direct SQL or marketplace calls in Streamlit pages.
- Made Mission Control default homepage via `streamlit_app.py` redirect.
- Preserved existing Financial Dashboard and Ingestion Health pages.
- Regression: 194 tests passing.
- Evidence: `docs/engineering/WP3.0-Closeout-Report.md`

## 2026-07-29 — WP3.2 CLOSED

- Created `commerceos/knowledge/organizational_memory.py` for rich memory classification: lessons, experiments, SOPs, and project notes.
- `OrganizationalMemory` writes Markdown notes under `30 Projects/`, `40 SOP/`, and `50 Reference/` with deterministic tags and wiki-links.
- Lifecycle helper `apply_retention()` wires `RetentionPolicy` archive rules for daily/weekly/monthly notes.
- Added `tests/unit/knowledge/test_organizational_and_retrieval.py` — 10 new tests passed.
- Regression: 253 tests passing.
- Evidence: `docs/engineering/WP3-Epic3-Closeout.md`
- Next: WP3.3 Memory Retrieval Engine v1.

## 2026-07-29 — WP3.3 CLOSED

- Created `commerceos/knowledge/retrieval_engine.py` with deterministic query APIs:
  - `what_happened_before(target, days)` — timeline reconstruction around a note or decision.
  - `decision_history(decision_id, days)` — notes related to a decision.
  - `project_history(project, days)` — notes tagged to a project.
  - `timeline_around_metric(metric, days)` — notes mentioning a metric or KPI.
  - `memory_timeline(days)` — flat chronological view across note types.
- All retrieval APIs return metadata first; full content loaded only on explicit `read_note`.
- No embeddings, no semantic search, no vector database.
- Tests integrated in `tests/unit/knowledge/test_organizational_and_retrieval.py`.
- Regression: 253 tests passing.
- Evidence: `docs/engineering/WP3-Epic3-Closeout.md`
- Next: WP3.4 and WP3.5 architecture finalization only.

## 2026-07-29 — WP3.4 Preparation

- Architecture documented in `docs/engineering/WP3.4-Knowledge-Graph-Architecture.md`.
- Proposed entities: Business, Project, Decision, Experiment, Event, Metric, Person, SOP.
- Proposed relationships: caused, affected, implemented, produced, triggered, belongs_to, contains, learned_from.
- Implementation deferred until notes > ~1,000 or multi-hop traversal becomes necessary.
- Current `links` and `source_domains` in `knowledge_notes` provide a lightweight one-hop graph.

## 2026-07-29 — WP3.5 Preparation

- Architecture documented in `docs/engineering/WP3.5-AI-COO-Architecture.md`.
- AI COO would consume deterministic knowledge APIs, business state, and monitoring/intelligence dashboards.
- Safety rules: marketplace mutations only through `ExecutionEngine`, high-risk decisions require human approval, all AI actions logged to `execution_audit`.
- Implementation deferred until WP3.2/3.3 have accumulated enough historical notes and a recurring decision justifies automation.

## 2026-07-29 — v1.0 Architecture Review & Stabilisation CLOSED

- Reviewed bounded contexts, dependency direction, repository consistency, configuration, testing, scripts, and operational workflows for v1.0 readiness.
- Eliminated circular dependency between `connectors` and `ingestion` by introducing `commerceos/connectors/core/mapper.py` as a shared kernel for `CanonicalEntity` and `Mapper`.
- Centralised UTC timestamp creation across `commerceos/`, `scripts/`, and `pages/` to use `utc_now()` from `commerceos.shared.value_objects.primitives` (~162 inline `datetime.now(timezone.utc)` calls replaced in 72 files).
- Archived 15 legacy root-level operational scripts to `archive/legacy_scripts/` and updated reporting inventory and secret-regression tests to reflect the canonical paths.
- Updated `LegacyFinancialAdapter` to import archived `financial_engine.py` explicitly.
- Improved OAT messaging in `scripts/oat_verification.py`: now distinguishes `operational_flow.monitoring_active` (snapshot exists) from `operational_flow.monitoring_healthy` (overall status is `healthy`).
- Updated unit test expectations in `tests/unit/oat/test_oat_verification.py` for the new OAT check.
- Full regression: 276 tests passing.
- Created `docs/engineering/CommerceOS-v1.0-Architecture-Review.md` with architecture overview, debt classification, refactor log, and final assessment.
- Architecture Health Score: 8.2 / 10.
- Final recommendation: **CommerceOS v1.0 Approved for Epic 5**.
- Next: choose next epic (WP3.4 implementation, WP3.5 implementation, or Epic 5 marketplace growth execution).

## 2026-07-29 — Epic 4 CLOSED

- WP4.1 Automation Runtime: `commerceos/jobs/` registry, runner, health reporter, and default handlers. Jobs are idempotent, history is recorded, failures are captured, overdue jobs are detectable. Added `scripts/run_scheduled_jobs.py` and `scripts/run_operational_cycle.py`.
- WP4.2 Telegram COO Channel: `commerceos/telegram/notifier.py` with `TelegramNotifier` and `COOReporter`. Morning brief and evening review scripts added. Gracefully disabled when `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` are absent.
- WP4.3 Operational Acceptance Testing: `scripts/oat_verification.py` verifies data health, operational flow, and knowledge flow. Reports PASS/FAIL with actionable findings.
- WP4.4 Reporting Consolidation: `commerceos/reporting/` inventory and router establish the knowledge layer as the canonical reporting path. Legacy paths are documented as deprecated but remain in place for compatibility.
- WP4.5 Closed Operational Loop Foundation: `commerceos/closed_loop/` with `DecisionOutcome` model and `OutcomeTracker`. Captures execution feedback, computes impact scores, updates lessons, and promotes successful outcomes to knowledge lesson notes.
- Fixed timezone handling in `DashboardQueryService.get_freshness()` for offset-naive timestamps.
- Made `KnowledgeReporter` metadata persistence idempotent for daily/weekly/monthly notes.
- Applied migrations: `knowledge_notes` and `decision_outcomes` tables in `commerceos.db`.
- Added 23 Epic 4 unit tests across `tests/unit/jobs/`, `tests/unit/telegram/`, `tests/unit/reporting/`, `tests/unit/closed_loop/`, `tests/unit/oat/`.
- Full regression: 276 tests passing.
- Evidence: `docs/engineering/Epic4-Operational-Reliability-Closeout.md`
- Next: Epic selection (WP3.4 implementation, WP3.5 implementation, or Epic 5).

## 2026-07-29 — WP3.1 CLOSED

- Completed Phases A through E of the COO Briefing System v1.
- Phase D: `KnowledgeDashboard` retrieval APIs, `links.py` wiki-link helpers, Mission Control knowledge panel.
- Phase E: `RetentionPolicy`, `KnowledgeReporter` wiring, concise Telegram summary helpers.
- Full WP3.1 test regression: 243 tests passing.
- Evidence: `docs/engineering/WP3.1-Closeout-Report.md`
- Next: WP3.2 Organizational Memory Foundation.

## 2026-07-29 — WP3.1 Phase C CLOSED

- Created `KnowledgeMemory` to collect operational data from existing dashboards only (`DashboardQueryService`, `MonitoringDashboard`, `IntelligenceDashboard`, `DecisionDashboard`, `ExecutionDashboard`, `EventsDashboard`).
- Created `MemorySummarizer` with deterministic synthesis for daily body, weekly, monthly, and yearly notes.
- Synthesizers do not concatenate input; they extract trends, wins, failures, recurring issues, decisions, and lessons.
- Created `KnowledgeIndex` to rebuild `index.md` from metadata records deterministically.
- Added 12 unit tests for memory collection, summarizer synthesis, and index generation.
- Regression: 226 tests passing.
- Next: WP3.1 Phase D (retrieval APIs + Mission Control integration).

## 2026-07-29 — WP3.1 Phase B CLOSED

- Created `ObsidianVault` for deterministic Obsidian folder structure (`00 Inbox`, `10 COO`, `20 Decisions`, `30 Projects`, `40 SOP`, `50 Reference`, `90 Archive`).
- Created `ObsidianWriter` for YAML frontmatter + Markdown generation with tags, links, source domains, and extra frontmatter.
- `ObsidianVault.ensure_structure()` is idempotent and never deletes existing files.
- `ObsidianWriter.write()` returns the canonical file path under the vault layout.
- Added 12 unit tests for vault structure and writer behavior.
- Regression: 214 tests passing.
- Next: WP3.1 Phase C (memory generation).

## 2026-07-29 — WP3.1 Phase A CLOSED

- Created `commerceos/knowledge/` bounded context package.
- Added `KnowledgeNote` model and `knowledge_notes` table (navigation metadata only).
- Implemented abstract repository and SQLAlchemy unit of work.
- Added `obsidian_vault_path` default to `Settings`.
- Created standalone migration script under `commerceos/knowledge/migrations/`.
- Added 8 unit tests for models and repositories.
- Regression: 202 tests passing.
- Next: WP3.1 Phase B (vault foundation + writer).

## 2026-07-29 — Memory Architecture Created

- Created `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/CHANGELOG.md`.
- Reduced `memory.md` to Hermes behavior and workflow rules only.
- Created `hermes-dev-protocol` skill.
