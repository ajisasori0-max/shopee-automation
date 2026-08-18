# ADR-002: Canonical Commerce Database Schema

## Status

Accepted

## Date

2026-07-16

## Context

CommerceOS needs a single source of truth for commerce data. The legacy system stores data in multiple inconsistent SQLite databases (`growth_data.db`, `financial_data.db`) and JSON files. Marketplace APIs are treated as the source of truth, which makes reconciliation, validation, and reporting difficult.

We need a canonical database that models commerce concepts, not marketplace APIs. It must be database-agnostic (SQLite today, PostgreSQL in production) and support future multi-marketplace, multi-store, and multi-tenant evolution.

## Problem Statement

1. Data is fragmented across multiple files and databases.
2. Marketplace-specific fields leak into business logic.
3. No schema versioning or migration framework.
4. Identifiers are SQLite auto-increment integers, which do not scale across multiple databases or tenants.
5. Timestamps are inconsistent and may not be UTC.

## Options Considered

### Option A: Keep legacy SQLite databases and add views

Create a reporting layer over the existing databases.

- Pros: Fast, no migration.
- Cons: Perpetuates fragmentation; marketplace-specific schemas; no path to PostgreSQL or SaaS.

### Option B: One big marketplace-specific schema

Design tables around Shopee's API response shape.

- Pros: Fast to ingest.
- Cons: Hard to add TikTok Shop, Lazada, Tokopedia later; business logic coupled to Shopee.

### Option C (Selected): Marketplace-agnostic canonical schema

Model business entities (`Order`, `Product`, `Payment`, etc.) with tenant IDs, UUIDs, and UTC timestamps. Use marketplace-specific mappings only in connectors.

- Pros: Clean business logic; multi-marketplace ready; SaaS-ready; PostgreSQL-compatible.
- Cons: Requires careful mapping from Shopee API responses.

## Decision

Adopt Option C.

CommerceOS will use a **canonical commerce database** with the following properties:

- Entities represent commerce concepts, not marketplace concepts.
- Every table has `organization_id`, `business_id`, and `store_id` for multi-tenant evolution.
- Primary identifiers are UUIDs where practical.
- Timestamps are stored in UTC.
- Constraints and indexes are PostgreSQL-compatible.
- Migrations are managed with Alembic.
- Persistence is isolated behind repository interfaces.
- Initial schema is limited to entities with active consumers today.

## Why This Option Was Chosen

- It aligns with the CommerceOS vision: the platform thinks in business capabilities, not marketplace APIs.
- It prevents future rewrites when adding TikTok Shop, Lazada, Tokopedia, or SaaS.
- It makes the database portable from SQLite to PostgreSQL without changing domain logic.

## Initial Schema Scope (Epic 1)

### Implemented

- `Organization`, `Business`, `Store`, `Marketplace`
- `Product`, `Variant`, `Inventory`
- `Order`, `OrderItem`
- `Payment`, `Expense`, `Revenue`
- `Campaign`, `Ad`, `AdPerformance`
- `KPI`, `KPIHistory`
- `CommerceState`, `CommerceStateHistory`, `TodayFocus`
- `BusinessRule`, `RuleExecution`
- `DataQualityEvent`, `ReconciliationEvent`

### Deferred

- `Customer` — needs CRM module.
- `Shipment` — needs operations/fulfillment module.
- `Return` — needs customer service module.
- `Supplier` — needs supplier module.
- `PurchaseOrder` — needs supplier module.
- `Warehouse` — simple location text suffices initially; formal multi-warehouse later.
- `Invoice` — needs tax/compliance module.
- `Promotion` — can be folded into `Campaign` initially; separate when needed.

## Benefits

- Single source of truth for commerce data.
- Marketplace-agnostic core business logic.
- Multi-tenant fields from day one.
- PostgreSQL-compatible design.
- Schema versioning and migrations.

## Trade-offs

- More design effort upfront than copying Shopee API responses.
- Some marketplace-specific fields must be stored in JSON metadata columns, which is less queryable than normalized columns.
- Initial schema omits useful entities to keep Epic 1 focused.

## Risks

| Risk | Mitigation |
|------|------------|
| JSON metadata becomes unmanageable | Only use for truly marketplace-specific fields; document each field |
| UUIDs increase index size | Acceptable trade-off for portability; use indexes wisely |
| SQLite migration features differ from PostgreSQL | Test migrations on PostgreSQL target before production cutover |
| Schema too simple for future features | Schema is versioned; add tables via migrations |

## Consequences

- All connectors write to canonical tables.
- All KPIs, rules, and state read from canonical tables.
- No business logic reads Shopee API responses directly.
- Marketplace-specific mappings are owned by the connector, not the domain.

## Migration Strategy

1. Create new canonical database with Alembic migrations.
2. Migrate existing data from `growth_data.db` and `financial_data.db` into canonical tables.
3. Run old scripts and new connectors in parallel until new data is validated.
4. Retire old databases once cutover is approved.

## SQLite to PostgreSQL Migration Path

- All SQLAlchemy models use generic types (`String`, `Integer`, `Decimal`, `DateTime`, `UUID`, `Boolean`, `JSON`, `Text`).
- No SQLite-only features (e.g., `AUTOINCREMENT`, `DATETIME` functions).
- Timestamps are Python `datetime` objects in UTC, stored as `DateTime(timezone=True)`.
- Migrations are written for both SQLite and PostgreSQL dialects where they differ.
- Connection strings are configurable via settings.
- Repository implementations are swappable behind interfaces.

## Technical Debt: Domain Models vs Persistence Models

For Epic 1, the SQLAlchemy declarative models in `commerceos/commerce/models/` are serving as both the domain model and the persistence model. This was chosen to maximize speed and keep the system usable while Gerard runs the business.

This is temporary. The long-term architecture is:

```
Domain Models → Repository Interfaces → Persistence Models (SQLAlchemy)
```

- Domain models contain pure business logic and value objects.
- Repository interfaces define the persistence contract.
- Persistence models (SQLAlchemy) are used only for database access.
- Mappers translate between domain and persistence models.

After core capabilities are proven and the platform is stable, we will refactor the coupled models into clean domain models and SQLAlchemy persistence models. This debt is tracked and will be paid down before the first external marketplace is added.

## Rollback Strategy

If the canonical schema proves too abstract for the first Shopee store, we can add Shopee-specific extension tables without changing the core entities. Old databases remain intact until the new system is validated. Alembic migrations support `alembic downgrade` to reverse schema changes.

## Related ADRs

- ADR-001: Commerce State and KPI Engine Architecture
- ADR-003: Marketplace Connector Interface

## Affected Modules

- `commerceos.platform.database`
- `commerceos.commerce`
- `commerceos.finance`
- `commerceos.advertising`
- `commerceos.kpi`
- `commerceos.rules`
- `commerceos.state`
- `commerceos.connectors`
- `commerceos.sync`
