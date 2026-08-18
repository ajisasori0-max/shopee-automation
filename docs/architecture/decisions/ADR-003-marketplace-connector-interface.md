# ADR-003: Marketplace Connector Interface

## Status

Accepted

## Date

2026-07-16

## Context

CommerceOS must support multiple marketplaces over time. Gerard's Shopee business is the first deployment. Future marketplaces may include TikTok Shop, Tokopedia, Lazada, and possibly Meta/Google Ads. The core platform should not depend on any specific marketplace API.

## Problem Statement

1. The legacy system is tightly coupled to Shopee API endpoints and response shapes.
2. Adding a new marketplace would require rewriting business logic.
3. Token refresh, authentication, signing, and rate limiting are scattered.

## Options Considered

### Option A: Direct marketplace client calls in each domain

Every domain service calls Shopee API directly when needed.

- Pros: Simple for one marketplace.
- Cons: Business logic is polluted with marketplace-specific code; impossible to reuse.

### Option B: Thin connector adapter per marketplace

Each connector maps API responses to a thin shared model. Business logic still handles many marketplace-specific quirks.

- Pros: Better than Option A.
- Cons: Shared model may still leak marketplace-specific fields into core.

### Option C (Selected): Full connector abstraction

Define a connector interface that operates on canonical commerce entities. Each marketplace implements the interface. The core platform only knows canonical concepts. Marketplace-specific details are isolated inside the connector.

- Pros: Clean core; easy to add marketplaces; testable; reusable.
- Cons: Requires designing a rich canonical model and careful mapping.

## Decision

Adopt Option C.

CommerceOS will have a connector framework with:

- A `Connector` interface in `commerceos.connectors.core`.
- A `ConnectorRegistry` to discover and load connectors.
- Marketplace-specific implementations (e.g., `ShopeeConnector`) in `commerceos.connectors.<marketplace>`.
- Connector outputs are canonical business entities.
- Connector responsibilities include: authentication, signing, pagination, rate limiting, retries, token refresh, health checks, and mapping.

## Connector Interface

Every connector implements:

- `name()` → marketplace identifier
- `authenticate(store)` → returns authenticated session or fails
- `health_check(store)` → returns connector health status
- `sync_orders(store, since)` → yields canonical `Order` entities
- `sync_products(store)` → yields canonical `Product` and `Variant` entities
- `sync_inventory(store)` → yields canonical `Inventory` entities
- `sync_advertising(store, since)` → yields canonical `Campaign`, `Ad`, and `AdPerformance` entities
- `sync_payments(store, since)` → yields canonical `Payment` entities
- `refresh_auth(store)` → refreshes tokens or credentials

## Why This Option Was Chosen

- It keeps the core platform marketplace-agnostic.
- It makes the Shopee implementation replaceable.
- It allows CommerceOS to add new marketplaces by implementing a single interface.
- It centralizes authentication, retries, and health checks in one place per connector.

## Benefits

- Core business logic does not depend on Shopee.
- Each marketplace can evolve independently.
- Connector tests can use mock API responses.
- Future SaaS customers can enable marketplaces per store.

## Trade-offs

- The canonical model must be rich enough to express the union of marketplace concepts.
- Some marketplace-specific features may not fit cleanly into the canonical model.
- Connector maintenance is an ongoing burden.

## Risks

| Risk | Mitigation |
|------|------------|
| Canonical model becomes too generic | Start with Shopee; generalize only when adding second marketplace |
| Shopee-specific workarounds leak into interface | Document and isolate in ShopeeConnector; do not add to interface |
| Marketplace API changes break connector | Versioned connector; abstraction limits blast radius |
| Performance cost of mapping | Acceptable; optimize if profiling shows bottleneck |

## Consequences

- The only Shopee-specific code in CommerceOS lives in `commerceos.connectors.shopee`.
- All other modules operate on canonical commerce entities.
- Sync engine calls connectors through the interface, not directly.
- Health checks can monitor each connector independently.

## Migration Strategy

1. Define the connector interface (E1.3).
2. Implement `ShopeeConnector` against the canonical schema.
3. Migrate existing `shopee_client.py` logic into `ShopeeConnector`.
4. Keep old `shopee_client.py` operational until the new connector is validated.
5. Add future marketplaces by implementing the same interface.

## Rollback Strategy

If the connector abstraction proves too heavy for a single marketplace, the Shopee implementation can be simplified internally while keeping the interface intact. The interface is preserved so future marketplaces still plug in.

## Related ADRs

- ADR-001: Commerce State and KPI Engine Architecture
- ADR-002: Canonical Commerce Database Schema

## Affected Modules

- `commerceos.connectors.core`
- `commerceos.connectors.shopee`
- `commerceos.sync`
- `commerceos.commerce`
- `commerceos.finance`
- `commerceos.advertising`
