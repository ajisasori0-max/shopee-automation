# ROADMAP.md

Canonical CommerceOS product roadmap. Reconciled against the actual implementation during the 2026-08-11 stabilization pass. Statuses: **COMPLETE**, **PARTIAL**, **NOT STARTED**.

## Epic 1 — CommerceOS Foundation

- Unified sync engine, raw payloads, provenance, checkpoints, canonical domain tables, token governance.
- **Status: COMPLETE**

## Epic 2 — Operational Intelligence

- Monitoring, health checks, alerts, snapshots, intelligence, decision engine, execution engine, event bus.
- **Status: COMPLETE**

## Epic 3 — COO Operating System

| WP | Name | Status | Evidence / Gap |
|----|------|--------|----------------|
| WP3.0 | Mission Control | **COMPLETE** | `pages/mission_control.py`, DashboardQueryService |
| WP3.1 | COO Briefs + Knowledge Layer | **COMPLETE** | Daily/weekly/monthly reporters, Obsidian vault, retrieval APIs |
| WP3.2 | COO Context & Memory Engine | **COMPLETE** | Organizational memory + retrieval exist; deterministic relevance/context construction via COO Interface |
| WP3.3 | COO Workflow Manager | **PARTIAL** | Job runner + health monitoring exist; persistent Observe→Learn loop orchestrator not modeled separately from feedback loop |
| WP3.4 | Operational SOP Engine | **COMPLETE** | `commerceos/sop/engine.py`, 4 deterministic SOPs, DecisionEngine integration, tests |
| WP3.5 | COO Interface | **COMPLETE** | `commerceos/coo/interface.py`, intent classification, deterministic response formatter, dashboard, CLI, tests |

### Web COO Dashboard

- Single orchestration service: `commerceos/coo/web_service.py` (`WebCOODashboardService`)
- Streamlit pages: Command Center, Intelligence, Decisions, Executions, Knowledge, SOP & Rules, Experiments, Operations, Analytics, Timeline
- **Status: COMPLETE**

## Epic 4 — Autonomous Operations

| WP | Name | Status | Evidence / Gap |
|----|------|--------|----------------|
| WP4.1 | Policy Engine | **COMPLETE** | `commerceos/policy/engine.py`, configurable rules, limits, cooldown, rate limit, tests |
| WP4.2 | Autonomous Execution | **COMPLETE** | `commerceos/policy/autonomous_execution.py`, auto-execute vs approval routing, idempotent, tests |
| WP4.3 | Feedback Loop | **COMPLETE** | `commerceos/policy/feedback_loop.py`, outcome capture, KPI deltas, lesson promotion |
| WP4.4 | Experimentation Engine | **COMPLETE** | `commerceos/policy/experiment_engine.py`, guardrails, policy check, conclusion, tests |

## Epic 5 — Business Intelligence & Forecasting

| WP | Name | Status | Evidence / Gap |
|----|------|--------|----------------|
| WP5.1 | Advanced Analytics | **COMPLETE** | `commerceos/analytics/engine.py`, SKU/campaign profitability, revenue decomposition, tests |
| WP5.2 | Demand Forecasting | **COMPLETE** | `commerceos/analytics/forecasting.py`, naive/MA/trend/seasonal, tests |
| WP5.3 | Inventory Intelligence | **COMPLETE** | `commerceos/analytics/inventory.py`, velocity, stockout risk, restock recommendations, tests |
| WP5.4 | Financial Forecasting | **COMPLETE** | `commerceos/analytics/finance.py`, P&L, cash forecast, tests |
| WP5.5 | Scenario Engine | **COMPLETE** | `commerceos/analytics/scenarios.py`, ad spend, sales decline, supplier delay, price, new SKU, tests |

## Epic 6 — Multi-Store / Multi-Marketplace

- Store registry, connector registry, unified commerce state, cross-marketplace intelligence.
- **Status: NOT STARTED**

## Epic 7 — Production Hardening & Scale

- PostgreSQL, durable queue, worker infrastructure, observability, disaster recovery, security hardening.
- **Status: NOT STARTED**

## Epic 8 — CommerceOS 1.0 / Productization

- Product architecture, configuration system, user/role system, full COO experience.
- **Status: NOT STARTED**

## Next Canonical Work Package

Web COO Dashboard is complete. Decide next priority before starting Epic 6 (multi-store/multi-marketplace), Epic 7 (production hardening/scale), or UI/operational hardening.
