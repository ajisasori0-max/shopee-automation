# ARCHITECTURE.md

Long-term system memory for the Shopee / CommerceOS project.
Only update when architecture changes.

## System Overview

CommerceOS is a local-first, event-driven operational platform for managing a Shopee store.
It ingests marketplace data, materializes business metrics, monitors health, generates intelligence, proposes decisions, and executes approved actions safely.

## Core Components (Bounded Contexts)

| Component | Path | Responsibility |
|-----------|------|--------------|
| Platform | `commerceos/platform/` | Secrets, database connection, settings |
| Ingestion | `commerceos/ingestion/` | Sync engine, raw payloads, provenance, checkpoints |
| Commerce | `commerceos/commerce/` | Canonical entities, KPI engine, commerce state |
| Monitoring | `commerceos/monitoring/` | Health checks, alerts, snapshots, scheduler health |
| Intelligence | `commerceos/intelligence/` | Trends, anomalies, explainable insights |
| Decision | `commerceos/decision/` | Rule-based recommendations, approval workflow |
| Execution | `commerceos/execution/` | Safe plan → dry-run → execute → audit → rollback |
| Events | `commerceos/events/` | Event bus, workflow orchestration, dead letters, locks |
| Dashboard | `commerceos/dashboard/` | Stable read APIs for Streamlit and reporters |
| Connectors | `commerceos/connectors/` | Marketplace-specific ingestion adapters (Shopee) |

## Data Flow

```
Marketplace API
      ↓
Shopee Connector
      ↓
SyncEngine (ingestion)
      ↓
Canonical tables (orders, payments, products, inventory, campaigns, ads)
      ↓
KPI Engine
      ↓
CommerceState + KPI tables
      ↓
Monitoring / Intelligence / Decision / Execution / Events
      ↓
Dashboard Query Service + Domain Dashboards
      ↓
Streamlit / Obsidian / Telegram / Cron jobs
```

## Major Design Decisions

1. **Bounded contexts with repository/UoW pattern.** Each component owns its models and persistence. SQLAlchemy repositories implement abstract interfaces.
2. **No direct SQL outside repositories.** Streamlit pages and scripts consume service/dashboard APIs only.
3. **No marketplace calls in UI.** Marketplace mutations only happen through the Execution Engine after explicit approval.
4. **Centralized token management.** `token_manager.py` is the only production path for Shopee access tokens.
5. **Idempotent, resume-safe sync.** Sync checkpoints record last successful positions; sync runs are immutable audit logs.
   - DateTime natural keys are normalized to `datetime.date` during upsert so repeated incremental syncs update rather than duplicate rows.
6. **Materialized KPIs.** KPIs are pre-computed daily per (store, date, code) for fast dashboard reads.
7. **Event-driven orchestration.** Workflows are triggered by events; locks prevent duplicate execution.
8. **Approval before execution.** Decision engine proposes; execution engine acts only after approval.

## Technology Choices

- **Python 3.11** with type hints
- **SQLAlchemy** ORM + Alembic migrations
- **SQLite** for local single-tenant operation (PostgreSQL-ready design)
- **Streamlit** for dashboards
- **Pydantic Settings** for configuration
- **MacOS Keychain / file fallback** for secrets via `SecretManager`

## Architectural Constraints

- All Streamlit pages must use `DashboardQueryService` or domain dashboard classes.
- All scripts must log job execution to `job_executions` if they run on a schedule.
- All secret access must go through `SecretManager`.
- All marketplace mutations must go through `ExecutionEngine`.
- All new code must keep the regression suite passing.

## Patterns Used

- **Repository + Unit of Work** for persistence
- **Domain-driven bounded contexts**
- **Immutable sync runs** + mutable checkpoints
- **Natural-key upsert** for incremental sync deduplication, with DateTime columns normalized to date for stable comparison
- **Provenance tracking** for auditability
- **Dry-run → approve → execute** for safe automation

## Things Future Agents Must Understand

1. The internal store alias is `store-ppm-001`. The real Shopee `shop_id` lives inside the connector/API client.
2. KPIs are materialized by `refresh_kpis.py` / `KPIEngine.refresh()` after every sync.
3. `CommerceState` is the single aggregated business snapshot; dashboards should prefer it over re-aggregating.
4. `token_manager.py` is the only supported path to refresh Shopee tokens.
5. Old scripts in the root (`daily_monitor.py`, `full_automation.py`, etc.) are legacy and being retired.

## Last Updated

2026-07-29
