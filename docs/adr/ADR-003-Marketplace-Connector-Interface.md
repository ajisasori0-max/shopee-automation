# ADR-003: Marketplace Connector Interface (Revised)

## Status

Accepted

## Context

CommerceOS must integrate with multiple marketplaces (Shopee, Amazon, TikTok Shop, Lazada, Shopify, WooCommerce, etc.). Each marketplace has its own API surface, authentication mechanism, pagination strategy, rate limits, and data model. To avoid marketplace-specific logic leaking into the canonical commerce domain, we need a clean, provider-agnostic connector framework.

## Decision

Introduce a `commerceos.connectors` bounded context with a strict interface-first design.

### 1. ConnectorAuth

- Each connector owns its own authentication object.
- Authentication retrieves credentials from the provider-agnostic `SecretManager` using a connector-specific namespace.
- Example namespace for Shopee: `shopee/{store_id}/partner_id`, `shopee/{store_id}/partner_key`, etc.
- The `SecretManager` remains agnostic; it only knows secret names, not marketplace semantics.

### 2. MarketplaceConnector

- Every connector implements the same `MarketplaceConnector` interface.
- Connectors expose business capabilities, not marketplace endpoints:
  - `fetch_orders`
  - `fetch_products`
  - `fetch_inventory`
  - `fetch_payments`
  - `fetch_ads`
- Each method returns a standardized `ConnectorResult`.
- Every connector exposes `marketplace_code`, `name`, `version`, and `auth`.
- Sync methods default to incremental mode using cursors or timestamps.

### 3. ConnectorResult

Every connector operation returns a `ConnectorResult` with:
- `success`: boolean
- `data`: canonical or raw payload
- `errors`: list of error dictionaries with `message` and optional `code`
- `metadata`: sync metadata including
  - `sync_mode`: full or incremental
  - `cursor`: pagination / next cursor
  - `source_timestamp`: timestamp from the source system
  - `connector_version`: implementation version
  - `request_id`: optional request correlation id
  - `fetched_at`: when the fetch occurred (UTC)
  - `page_count`: number of pages consumed

### 4. ConnectorHealth

Each connector exposes deterministic health via `ConnectorHealth`:
- `authenticated`: credentials present and valid
- `api_available`: marketplace API reachable
- `last_successful_sync`: timestamp
- `last_failed_sync`: timestamp
- `rate_limit_remaining`: count
- `rate_limit_reset_at`: timestamp
- `token_expires_at`: timestamp
- `data_freshness_seconds`: seconds since last successful sync
- `status`: string summary
- `errors`: list of error messages

This becomes the foundation for Platform Stabilization in Epic 2.

### 5. Raw Payload Preservation

For every synchronized entity, the connector retains the original marketplace payload alongside the canonical mapping. The canonical mapping is produced by the connector, but the raw payload is stored in a durable, schema-versioned raw data store for debugging, replay, and future schema evolution.

### 6. ConnectorRegistry

A lightweight registry maps marketplace codes to connector instances. It provides:
- `register`
- `get`
- `list`
- `health`
- `health_all`

## Consequences

- New marketplaces require only a new implementation of `MarketplaceConnector` and `ConnectorAuth`.
- Orchestration, retries, logging, and observability can be built against `ConnectorResult` and `ConnectorHealth` without marketplace-specific logic.
- The sync engine can treat all connectors uniformly.
- Raw payload preservation increases storage but dramatically improves debuggability and forward compatibility.
- Namespaced secrets allow multi-store support without redesign.

## Risks

- The interface may need to evolve as we integrate more marketplaces. We will version the connector interface and bump connector versions independently.
- Raw payload retention requires a durable, append-only raw store. This will be implemented as part of the Sync Engine in Epic 1.
- Connector health checks may require additional API calls; we must avoid health checks consuming excessive rate limits.

## Technical Debt

- This ADR only defines the interface. Concrete Shopee connector implementation follows in E1.3.
- Health check implementations may be shallow until we have real API telemetry.
- Raw payload store is not yet implemented.
