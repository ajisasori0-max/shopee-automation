# Epic 4 — Operational Reliability & Growth Execution Closeout

## Overview

Epic 4 transformed CommerceOS from a system that can understand and remember the business into a system that can operate continuously. The objective was to build the operational loop:

```
Observe → Understand → Decide → Execute → Measure Outcome → Learn
```

without implementing AI reasoning, knowledge graphs, or autonomous execution. Those remain deferred to future epics.

The epic is accepted as production-ready because all tests pass, runtime smoke tests pass, the operational cycle can be scheduled, Telegram degrades gracefully, OAT behaves correctly, and the closed loop has been verified end-to-end.

## Operational Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Cron Scheduler (host)                     │
│  run_scheduled_jobs.py  /  send_morning_brief.py  /  etc.        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Automation Runtime (commerceos/jobs)              │
│  JobRegistry → JobRunner → job_executions table                   │
│  JobHealthReporter → overdue detection / failure summary           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                Domain Services (Monitoring, Knowledge)            │
│  system_health_check → health_checks / alerts / snapshots         │
│  daily_coo_brief → KnowledgeReporter → Obsidian + knowledge_notes  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Telegram COO Channel                          │
│  COOReporter + TelegramNotifier → morning / evening briefs     │
│  Returns delivery status; no-op if credentials missing           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Closed Operational Loop                       │
│  Decision → ExecutionPlan → OutcomeTracker → decision_outcomes     │
│  Successful outcome → OrganizationalMemory → lesson note         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OAT Verification (scripts/oat_verification)   │
│  Data health + operational flow + knowledge flow → PASS/FAIL       │
└─────────────────────────────────────────────────────────────────┘
```

## Runtime Components

### `commerceos/jobs/registry.py`

In-memory job registry with `JobDefinition` metadata and handler registration. No external scheduler dependency.

### `commerceos/jobs/runner.py`

`JobRunner` executes jobs by name, records every run to `job_executions`, captures exceptions, and rolls back only on failure so the failure record itself can be committed. Supports idempotency keys via job definitions.

### `commerceos/jobs/health.py`

`JobHealthReporter` summarizes recent failures, detects overdue jobs against expected intervals, and returns an overall healthy/unhealthy status.

### `commerceos/jobs/handlers.py` / `factory.py`

Default handlers:

- `daily_coo_brief` — daily COO brief
- `weekly_business_review` — weekly summary
- `monthly_executive_review` — monthly summary
- `knowledge_index_refresh` — rebuild vault index
- `knowledge_retention` — apply archive policy
- `system_health_check` — collect health, evaluate alerts, generate snapshot

All handlers are idempotent and receive the runner's database session.

## Job System

### Idempotency

Daily/weekly/monthly brief generation uses deterministic `note_id` values (e.g., `kn-2026-07-29`). `KnowledgeReporter._persist_metadata` now updates an existing record instead of raising a unique-constraint violation.

### Failure recording

Failed jobs are recorded with status `failed`, error message, and traceback. The runner's session is rolled back on failure so the job execution log can still be committed.

### Overdue detection

`JobHealthReporter.overdue_jobs(expected_intervals)` compares each job's latest `finished_at` against an expected interval in hours.

### Scheduler survival

The runner has been verified to survive repeated execution against the same database. A `finally` block ensures the session is clean after failures, and successful handler commits are preserved.

### Scripts

- `scripts/run_scheduled_jobs.py` — cron entrypoint; runs all jobs or a `--only` subset; can chain morning/evening Telegram briefs.
- `scripts/run_operational_cycle.py` — runs health check, daily brief, index refresh, and OAT in one invocation.
- `scripts/jobs_runtime_smoke.py` — end-to-end smoke test for the runtime.

## Telegram Integration

### `commerceos/telegram/notifier.py`

- `TelegramNotifier` — thin HTTP wrapper around `https://api.telegram.org/bot<token>/sendMessage`. Returns `TelegramDelivery` with `ok`, `status_code`, `telegram_message_id`, and `error`.
- `COOReporter` — builds morning and evening briefs from business state, alerts, decisions, and execution summaries. Full knowledge remains in Obsidian; Telegram receives only concise summaries.
- `from_settings()` loads `telegram_bot_token` and `telegram_chat_id` from `Settings` (`.env`).

### Graceful degradation

If token or chat_id is missing, `TelegramNotifier.is_enabled()` returns `False`, `send()` returns `ok=False` with a clear error, and the caller scripts continue without crashing. Verified in unit tests and script execution.

### Scripts

- `scripts/send_morning_brief.py` — generates morning brief from current business state and sends it.
- `scripts/send_evening_review.py` — generates evening review from the last 24 hours and sends it.

## OAT

### `scripts/oat_verification.py`

`OATVerification` runs three suites:

1. **Data Health** — sync checkpoint freshness, KPI availability, data quality score.
2. **Operational Flow** — health snapshot presence, open alert visibility.
3. **Knowledge Flow** — recent notes within 48 hours, retrieval API functionality.

Output is a structured PASS/FAIL report with actionable details per check.

### Verified behavior

- **Populated production database:** PASS (7/7 checks).
- **Empty database:** FAIL (3/7 checks) with clear messages: no checkpoints, no KPIs, no snapshot, no notes. This is the expected behavior.

### Bug fix

`DashboardQueryService.get_freshness()` now handles offset-naive timestamps by treating them as UTC, preventing crashes on older SQLite records.

## Closed Loop

### `commerceos/closed_loop/models.py`

`DecisionOutcome` links a `Decision` to an optional `ExecutionPlan`, recording:

- expected vs actual outcome
- success / failure
- impact score
- lessons
- follow-up decision IDs
- recorded_by and notes

### `commerceos/closed_loop/service.py`

`OutcomeTracker` provides:

- `record(...)` — manual outcome recording.
- `capture_execution_feedback(plan_id, success, impact, error)` — derive expected outcome from the decision, actual outcome from execution impact, and compute an impact score.
- `update_lessons(...)` — append lessons to an outcome.
- `promote_to_memory(outcome_id)` — create a lesson note in the knowledge vault only if the outcome was successful.

### Migration

`commerceos/closed_loop/migrations/001_create_decision_outcomes.py` creates the `decision_outcomes` table. Applied to `commerceos.db`.

### Verification

`scripts/closed_loop_smoke.py` demonstrates:

1. Create a decision.
2. Create an execution plan.
3. Capture execution feedback with impact.
4. Update lessons.
5. Promote to memory as a lesson note.

Result: `✅ Closed-loop smoke test passed.`

## Reporting Consolidation

### `commerceos/reporting/consolidation.py`

`REPORT_INVENTORY` documents every reporting path and marks it as canonical or deprecated. Examples:

- Canonical: Daily COO Brief, Weekly Business Review, Monthly Executive Review (all knowledge layer).
- Deprecated: legacy intelligence, monitoring, decision, execution, and event Telegram reporters; legacy scripts (`daily_monitor.py`, `growth_engine.py`, etc.); legacy financial Excel reports.

Legacy paths remain in place for compatibility; new code and scripts use the canonical knowledge layer.

### `commerceos/reporting/router.py`

`get_latest_canonical_report(note_type)` and `get_report_content(note_id)` route consumers to the knowledge layer. They return `None` gracefully if the database table is missing or empty (e.g., during OAT on a fresh system).

## Testing

### Epic 4 tests

- `tests/unit/jobs/test_runtime.py` — 7 tests: job registration, execution, logging, failure recording, idempotency, health summary, overdue detection, recent failures.
- `tests/unit/telegram/test_notifier.py` — 5 tests: disabled notifier, graceful real HTTP failure, morning brief, evening review, disabled reporter.
- `tests/unit/reporting/test_consolidation.py` — 4 tests: inventory split, canonical daily brief, deprecated legacy report, router empty DB.
- `tests/unit/closed_loop/test_outcome_tracker.py` — 5 tests: capture feedback, record outcome, update lessons, promote to memory only on success, impact score with no comparable metrics.
- `tests/unit/oat/test_oat_verification.py` — 4 tests: report structure, data health checks, knowledge flow checks, operational flow checks.

**Total: 25 Epic 4 unit tests, all passing.**

### Full regression

```
276 passed in 15.39s
```

## Production Readiness

### Scheduler robustness

- Jobs are plain Python callables; no distributed queue, no worker process, no extra infrastructure.
- Cron entries are documented in `scripts/run_scheduled_jobs.py` header.
- Failure of one job does not block other jobs in `run_many()`.
- `run_scheduled_jobs.py` exits with non-zero code if any job fails, which cron will surface as an error.

### Idempotency

- Daily/weekly/monthly briefs overwrite their file and update their metadata record on repeated runs.
- Health checks, alerts, and snapshots are designed to be run repeatedly; each run creates new records.
- Index refresh regenerates `index.md` from the latest metadata.

### Configuration

- All settings flow through `commerceos.config.settings.Settings` and `.env`.
- Telegram credentials are optional; absence is handled gracefully.
- Obsidian vault path defaults to iCloud Drive but can be overridden via `OBSIDIAN_VAULT_PATH`.

### Logging

- Every job execution is logged to `job_executions` with status, duration, metadata, and traceback on failure.
- Job execution history is queryable through `JobHealthReporter` and Mission Control.

### Error handling

- `TelegramNotifier.send()` catches all exceptions and returns a failed `TelegramDelivery`.
- `OATVerification` never crashes; it records findings and returns PASS/FAIL.
- `KnowledgeReporter` handles missing dashboard dependencies by using safe defaults.
- `ReportingRouter` catches `OperationalError` and returns `None`.

### Recovery after restart

- No in-memory state is required for correctness. The schedule is driven by the host cron.
- On startup, the runner reads the latest `job_executions` records to determine overdue jobs.
- `KnowledgeReporter` can be re-run at any time; it will update existing notes rather than duplicate them.

## Remaining Limitations

1. **Cron entries are not installed automatically.** The operator must copy the example crontab lines from `scripts/run_scheduled_jobs.py` into the host scheduler.
2. **Telegram delivery is not verified against a live chat.** The token and chat ID are not configured in this environment; actual delivery must be verified after deployment.
3. **Legacy scripts are still present.** `daily_monitor.py`, `growth_engine.py`, `financial_engine.py`, `auto_optimizer.py`, `full_automation.py`, and various `send_*.py` legacy scripts are deprecated but not removed. They should be retired once the new operational cycle is confirmed in production.
4. **No central retry policy.** The job runner records failures but does not automatically retry. Retries are left to cron's natural re-invocation schedule.
5. **No alerting on job failure.** Failed `job_executions` records are queryable, but there is no automatic notification when a job fails. This can be added by extending `JobHealthReporter` with a Telegram notification hook.
6. **OAT requires manual population for PASS.** On a fresh system OAT correctly reports FAIL. In production, the first scheduled run of `run_operational_cycle.py` will populate the necessary state.
7. **WP3.4 and WP3.5 remain architecture-only.** No graph database or AI reasoning layer has been implemented.
8. **No Alembic.** Migrations are standalone scripts that must be run manually when schema changes are introduced.

## Recommended Next Epic

**Epic 5 — Marketplace Growth Execution.**

With the operational loop now closed, the next high-value step is to connect the decision/execution engine to real marketplace growth actions. This includes:

- Automated campaign budget scaling decisions based on ROAS thresholds, with human approval still required.
- Product boost / ad campaign optimization workflows executed through the `ExecutionEngine`.
- Outcome tracking for each action so the closed loop learns which interventions work.
- Migrating the remaining legacy scripts (`growth_engine.py`, `auto_optimizer.py`, `full_automation.py`) into the new bounded contexts.

This keeps the system focused on measurable business outcomes rather than adding AI reasoning before the action layer is mature.

## Closeout Evidence

- Implementation: `commerceos/jobs/`, `commerceos/telegram/`, `commerceos/reporting/`, `commerceos/closed_loop/`, `scripts/run_scheduled_jobs.py`, `scripts/run_operational_cycle.py`, `scripts/send_morning_brief.py`, `scripts/send_evening_review.py`, `scripts/oat_verification.py`, `scripts/jobs_runtime_smoke.py`, `scripts/closed_loop_smoke.py`.
- Tests: `tests/unit/jobs/`, `tests/unit/telegram/`, `tests/unit/reporting/`, `tests/unit/closed_loop/`, `tests/unit/oat/`.
- Docs: `docs/PROJECT_STATE.md`, `docs/CHANGELOG.md`, `docs/engineering/Epic4-Operational-Reliability-Closeout.md`.
- Verification: 276 tests passing, runtime smoke tests passing, OAT PASS on populated database, closed-loop smoke test passing.

## Status

**Epic 4 ACCEPTED and COMPLETE.**
