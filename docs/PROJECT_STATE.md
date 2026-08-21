# PROJECT_STATE.md

Short-term operational memory for the Shopee / CommerceOS project.
Updated after every work package. Represents the current truth of the system.

## Current Epic / Work Package

- **Epic:** Web COO Dashboard — COMPLETE
- **Status:** WP3.4 COMPLETE; WP3.5 COMPLETE; Epic 4 COMPLETE; Epic 5 COMPLETE; Web COO Dashboard COMPLETE
- **Active blockers:** None
- **Verification:** 343 tests passing (314 unit + 29 integration); Streamlit dashboard launched and verified; sync + OAT smoke tests passed; plain `pytest` now passes cleanly after excluding archived scripts

## Completed Milestones

- Epic 1 CLOSED: Unified Platform Sync Engine
- Epic 2 CLOSED: Operational Intelligence & Autonomous Decision Support
- WP3.0 CLOSED: Unified COO Workspace (Mission Control)
- WP3.1 CLOSED: COO Briefing System v1
- WP3.2 CLOSED: Organizational Memory Foundation
- WP3.3 CLOSED: Memory Retrieval Engine v1
- WP3.4 CLOSED: Operational SOP Engine
- WP3.5 CLOSED: COO Interface
- Epic 4 CLOSED: Autonomous Operations (Policy Engine, Autonomous Execution, Feedback Loop, Experiments)
- Epic 5 CLOSED: Business Intelligence & Forecasting
- **Web COO Dashboard CLOSED: primary visual command center for CommerceOS**

## Current Implementation Status

- **Tests:** 314 unit tests passing, 29 integration tests passing
- **Database:** `commerceos.db` (SQLite); analytics rely on existing canonical tables
- **Analytics:** SKU/campaign profitability, demand forecasting, inventory intelligence, financial forecasting, scenario engine
- **Policy/Autonomy:** Policy engine, autonomous execution, feedback loop, experimentation engine
- **SOP Engine:** 4 deterministic SOPs (LOW_STOCK, ROAS_COLLAPSE, REVENUE_DROP, CASH_PRESSURE)
- **COO Interface:** Rule-based intent classification and deterministic response formatting
- **Web Dashboard:** Streamlit-based Command Center + Intelligence + Decisions + Executions + Knowledge + SOP/Rules + Experiments + Operations + Analytics + Timeline
- **Dashboard service:** `commerceos/coo/web_service.py` (`WebCOODashboardService`) orchestrates all reads and exposes a single service layer to Streamlit pages

## Important Implementation Decisions

- SOP logic is code-first; no config-driven SOP engine to keep business rules inspectable.
- Missing data is explicitly reported in `missing_inputs` rather than synthesized.
- SOP recommendations are deduplicated by title against open `Decision` records.
- SOPs do not execute marketplace mutations directly; they feed the Decision/Execution engine.
- Policy rules are configurable and code-first; automatic execution only when policy explicitly permits.
- Forecast confidence is computed from historical data length and volatility; low data returns `none` confidence.
- Analytics engines are deterministic and code-first; no LLM synthesis of business data.
- Streamlit pages are presentation-only; all reads flow through `WebCOODashboardService`; no direct SQL or marketplace mutations from the UI.
- Existing Mission Control was evolved into the new Command Center rather than replaced by a duplicate dashboard.
- Decision approve/reject buttons in the UI call the canonical `ApprovalWorkflow`, preserving audit history.

## Technical Debt

1. COGS, opening cash balance, and customer identity are not yet available; analytics and forecasts report them as missing.
2. Default lead time is 7 days; per-SKU supplier lead time not yet modeled.
3. No Alembic; migrations are standalone scripts.
4. Host crontab still references archived scripts (manual cleanup needed).
5. Streamlit dashboard computes today's metrics from materialized KPIs; if no orders occurred today, metrics are zero — this is data-accurate but may confuse first-time users until a "last N days" default is added.
6. `archive/` contains dead scripts with unresolvable imports; they are now excluded from pytest discovery via `pytest.ini`, but long-term they should either be deleted or moved outside the repo root.

## Immediate Next Actions

1. Decide next priority: Epic 6 (multi-store/multi-marketplace), Epic 7 (production hardening/scale), or UI/operational hardening (e.g., improve KPI coverage for today's metrics, add experiment conclusion workflow).
2. If the Web Dashboard is used operationally, monitor page load times and consider caching expensive queries (e.g., analytics summary) in session state or materialized KPIs.

## Last Updated

2026-08-12
