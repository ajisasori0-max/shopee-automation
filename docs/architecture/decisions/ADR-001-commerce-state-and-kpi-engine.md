# ADR-001: Commerce State, KPI Engine, and Business Rules Engine Architecture

## Status

Accepted

## Date

2026-07-16

## Context

CommerceOS is an AI-native commerce operating system. Gerard's Shopee business is the first production deployment, but the platform must eventually support multiple marketplaces, stores, and companies without rewriting core business logic.

We need a canonical way to represent what is happening in the commerce operation so that dashboards, reports, Telegram summaries, and AI agents all consume the same trusted operational snapshot. We also need clear boundaries between data ingestion, validation, rules, metrics, state, and AI-generated decisions.

## Problem Statement

1. The legacy system mixes data fetching, calculation, and presentation in scripts.
2. There is no single source of truth for "what is happening in the business right now."
3. AI currently risks calculating business metrics, which is unsafe and unexplainable.
4. Deterministic alerts, risks, and focus items are entangled with AI-generated recommendations.
5. Marketplace-specific fields leak into business logic.

## Options Considered

### Option A: Business State directly from database queries

Every consumer reads the canonical database directly and computes what it needs.

- Pros: Simple, no intermediate layers.
- Cons: Every consumer reimplements metrics; inconsistent dashboards; AI tempted to compute directly.

### Option B: Business State as a read model with embedded metric computation

A single builder computes metrics and stores a snapshot.

- Pros: Centralized computation; consumers share the same snapshot.
- Cons: Metric formulas and business rules are mixed inside the state builder; hard to extend.

### Option C (Selected): KPI Engine + Business Rules Engine + Commerce State

Separate concerns into distinct, observable layers:

- Marketplace Connectors fetch data.
- Canonical Commerce Database stores validated business entities.
- Validation & Reconciliation layer quarantines bad data.
- Business Rules Engine evaluates deterministic thresholds and generates flags/alerts/opportunities.
- KPI Engine computes deterministic metrics, using validated data and rule outputs.
- Commerce State Builder assembles a lightweight, current snapshot.
- AI agents consume Commerce State and generate recommendations separately.

- Pros: Clear ownership; explainable metrics; testable layers; AI only reads state.
- Cons: More components; initial complexity.

## Decision

Adopt Option C.

CommerceOS will have:

- A **Canonical Commerce Database** that models marketplace-agnostic business entities.
- A **Validation & Reconciliation Layer** that flags bad data.
- A **Business Rules Engine** that owns deterministic thresholds, alerts, risks, opportunities, and Today's Focus.
- A **KPI Engine** that owns all deterministic business metric computation.
- A **Commerce State Builder** that produces a lightweight, current snapshot consumed by reports, dashboards, and AI agents.
- An **AI Decision Layer** (future) that reads Commerce State and produces recommendations, but never calculates KPIs or accesses repositories directly.

## Why This Option Was Chosen

- It enforces the principle that **AI reasons, code computes**.
- It makes every metric explainable by tracing it back to a formula, dependencies, and validation status.
- It separates deterministic facts from AI-generated opinions.
- It allows CommerceOS to evolve toward SaaS by keeping domain layers clean and extensible.

## Benefits

- Single source of truth for consumers (Commerce State).
- Deterministic metrics are reproducible and testable.
- Business rules are visible, versionable, and tunable without code changes.
- AI agents cannot accidentally corrupt business logic.
- New marketplaces and stores can plug into the same architecture.

## Trade-offs

- More initial components than a monolithic script.
- Requires discipline to keep business logic inside domains, not in application services or AI prompts.
- Adds a small amount of latency between raw data and Commerce State.

## Risks

| Risk | Mitigation |
|------|------------|
| KPI Engine becomes too complex | Start with core KPIs; add formulas incrementally; document dependencies |
| Business rules drift out of sync with reality | Rule execution logs; periodic review; Gerard owns threshold tuning |
| Consumers bypass Commerce State and query DB | Enforce through code review; reporting layer only reads state |
| AI accidentally calculates metrics | Model interfaces only expose Commerce State, not repositories |

## Consequences

- All dashboards, reports, Telegram summaries, and AI agents consume Commerce State.
- No module except KPI Engine computes revenue, profit, ROAS, margins, or inventory metrics.
- No module except Rules Engine generates deterministic alerts, risks, or Today's Focus.
- Recommendations are explicitly outside Commerce State and belong to the AI layer.
- The architecture can support additional marketplaces, stores, and companies without changing these layers.

### Commerce State is a read model

Commerce State is never a source of truth. It is always a derived, disposable snapshot.

The source of truth chain is:

```
Marketplace Connectors
        ↓
Canonical Commerce Database
        ↓
Validation & Reconciliation
        ↓
Business Rules Engine
        ↓
KPI Engine
        ↓
Commerce State
```

Commerce State must be fully rebuildable from upstream data at any time. Consumers (reports, dashboards, Telegram, APIs, AI agents) read from Commerce State and never write to it. AI agents do not access repositories or canonical data directly.

### Business Rules Engine is read-only

The Business Rules Engine evaluates deterministic rules and produces:

- Alerts
- Risks
- Opportunities
- Today's Focus items
- Events

It must never mutate Orders, Payments, Inventory, Products, or any other canonical record. It is a read-only evaluator.

## Migration Strategy

This is the foundational architecture for Epic 1. Legacy scripts continue to operate on old data until the new Commerce State is validated and approved.

## Rollback Strategy

If the layered architecture proves too heavy for a single Shopee store, we can simplify by collapsing Rules and KPI into one engine while keeping the deterministic/AI boundary. Commerce State remains the consumer-facing snapshot.

## Related ADRs

- ADR-002: Canonical Commerce Database Schema
- ADR-003: Marketplace Connector Interface

## Affected Modules

- `commerceos.platform`
- `commerceos.connectors`
- `commerceos.sync`
- `commerceos.commerce`
- `commerceos.finance`
- `commerceos.advertising`
- `commerceos.rules`
- `commerceos.kpi`
- `commerceos.state`
- `commerceos.reporting`
- `commerceos.knowledge`
- `commerceos.agents`
- `commerceos.application`
- `commerceos.workflows`
