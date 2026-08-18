# Phase 1 — Implementation Plan
## Commerce Operating System (COS) — First Production Deployment

**Role:** Founding CTO / Principal Architect  
**Date:** 2026-07-16  
**Status:** Proposed — awaiting approval  
**Constraint:** No code changes. Planning only.

---

## Executive Summary

Phase 1 builds the **minimum viable architecture** for the Commerce Operating System, using Gerard’s Shopee business as Customer #1. The goal is not to fix scripts. The goal is to establish the foundational capabilities that every later phase depends on:

1. **Trusted Business State** — a single, validated source of truth.
2. **Secure Marketplace Integration** — a connector model that abstracts Shopee.
3. **Observability and Control** — the system must be visible, auditable, and recoverable.

Everything else — AI agents, decision engine, automation, multi-store, multi-marketplace — rests on these three foundations. If we build them correctly, future work becomes easier. If we skip or weaken them, we accumulate architectural debt that compounds.

---

## Guiding Principles for Phase 1

1. **No isolated scripts.** Every deliverable strengthens a module.
2. **Shopee is a connector, not the core.** Business logic must not depend on Shopee-specific fields.
3. **Business State is sacred.** Every implementation either produces, consumes, or validates it.
4. **Keep the business operational.** Every work package must leave the current system running.
5. **Remove technical debt when reasonable.** Hardcoded secrets, broken cron paths, and inconsistent databases must be addressed.
6. **No AI execution.** AI may read and reason, but Phase 1 establishes deterministic execution paths.
7. **Everything observable.** Logs, health checks, and audit trails are first-class deliverables.

---

## Phase 1 Work Packages

### Work Package 1: Secure Foundations and Secret Management

#### Business Objective
Establish a secure, production-ready operating environment where credentials and keys are never exposed in code, files, or logs. Trust is the foundation of the platform; without it, no automation or AI decision is safe.

#### Technical Objective
- Move all API keys, tokens, and partner IDs out of source code and plaintext JSON files.
- Introduce a secret vault that deterministic services can access at runtime.
- Ensure no secret is ever committed to version control or logged in plaintext.
- Define a secret rotation policy.

#### Deliverables
- Secret vault integration (macOS Keychain or 1Password CLI as the first backend; interface allows future migration to HashiCorp Vault or cloud-native secret managers).
- `SecretManager` abstraction with interface: `get_secret(name)`, `set_secret(name, value)`, `rotate_secret(name)`.
- Migration of all current secrets: Shopee partner IDs, seller tokens, ads tokens, Telegram bot tokens, OpenClaw gateway tokens, Render keys.
- Updated configuration files that reference secret names, not values.
- Pre-commit hook or CI check to block secrets from being committed.
- Audit log of secret access and rotation.
- Documentation: Secret management SOP in Obsidian.

#### Dependencies
- None. This is foundational.
- Requires Gerard to provide or confirm current credentials during migration.
- Requires decision on vault backend (Keychain vs. 1Password vs. other).

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Lost access during migration | Low | Critical | Migrate one secret at a time; keep old values until verified |
| Vault backend unavailable | Low | High | Keep fallback file-based encrypted storage with master key in Keychain |
| Gerard resistance to change | Medium | Medium | Explain security risk and demonstrate ease of use |
| Third-party tool dependency | Medium | Medium | Abstract interface allows swapping backends |

#### Success Criteria
- [ ] No hardcoded secrets remain in any source file.
- [ ] No plaintext token files in the workspace.
- [ ] All connectors retrieve secrets via `SecretManager`.
- [ ] Application runs successfully using secrets from vault.
- [ ] Secret access is logged.
- [ ] Version control scan confirms no secrets committed.

#### Estimated Complexity
**Medium.** The concept is simple, but there are many scattered secrets, and the migration must be done carefully to avoid downtime.

#### Validation Checklist
- [ ] Run `grep -r "partner_id\|partner_key\|access_token\|bot_token"` across source files and find only references, not values.
- [ ] Verify current automations still run (daily monitor, growth engine) using new secret path.
- [ ] Verify token refresh still works.
- [ ] Check audit log for secret access entries.

#### Why This Comes First
Secrets are the prerequisite for every other work package. We cannot safely refactor, move, or execute anything if credentials are scattered and exposed. Without secure foundations, later work is built on sand.

#### What Future Work It Unlocks
- Multi-tenant SaaS: each tenant can have isolated secrets.
- Connector abstraction: each connector can authenticate independently.
- Audit and compliance: secret access is traceable.
- CI/CD: code can be safely committed and deployed without leaking credentials.

#### Rollback Strategy
If the vault migration fails or breaks automation, restore the original token files from backup and revert connector references. The old files remain untouched until WP1 is validated.

#### Alignment with COS Architecture
Security is a cross-cutting concern. Secret management is not a module; it is a capability that all modules depend on. It supports the principle that AI never sees secrets and that deterministic services own authentication.

---

### Work Package 2: Canonical Business Database and Schema

#### Business Objective
Create a single source of truth for all operational data. Replace the current fragmented SQLite files with one authoritative, versioned, schema-enforced database that supports Gerard today and multi-tenant SaaS tomorrow.

#### Technical Objective
- Design a canonical relational schema based on the domain model from Phase 0C.
- Set up the database with migrations (Alembic or equivalent).
- Migrate existing data from `growth_data.db`, `financial_data.db`, and scattered JSON files into the canonical schema.
- Implement schema validation and reconciliation rules.
- Establish backup and recovery procedures.

#### Deliverables
- `cos_business.db` or `cos_business` PostgreSQL instance (SQLite acceptable for Phase 1; PostgreSQL for multi-tenant later).
- Schema covering: Organization, Business, Store, Marketplace, Product, Variant, Inventory, Supplier, PurchaseOrder, Customer, Order, OrderItem, Shipment, Return, Campaign, Ad, Promotion, AdPerformance, Expense, Revenue, Payment, Invoice, User, Task, Notification, Approval, SOP, KPI, Incident, Decision, Risk.
- Alembic migration scripts for schema versioning.
- Data migration script with reconciliation report.
- Backup script and documented restore procedure.
- Database access layer (DAO / repository pattern) with clear ownership per module.
- Documentation: database schema reference and migration SOP in Obsidian.

#### Dependencies
- Work Package 1 (secrets may be needed for migration, but schema design can start in parallel).
- Gerard’s confirmation of business entity (Organization, Business).
- Decision on SQLite vs. PostgreSQL for Phase 1.

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data migration loses or corrupts history | Medium | High | Migrate to new DB while keeping old DBs read-only; validate row counts |
| Schema is too rigid for future needs | Medium | Medium | Use nullable fields and extension tables; version schema with migrations |
| Migration downtime | Medium | Medium | Run migration in background; old scripts continue until validated |
| Gerard does not know Organization/Business structure | Low | Medium | Default to single Organization and single Business |

#### Success Criteria
- [ ] Canonical DB contains all data from old SQLite files without loss.
- [ ] Row counts match old DBs for orders, ad performance, inventory, etc.
- [ ] Migrations run successfully from scratch.
- [ ] Backup and restore tested.
- [ ] No module writes directly to old DBs after WP2.
- [ ] Schema documentation is complete and accurate.

#### Estimated Complexity
**High.** This is the biggest work package. It requires careful data modeling, migration, and validation. It is also the most important.

#### Validation Checklist
- [ ] Run migrations on a fresh database.
- [ ] Compare migrated data row counts and sample values against old DBs.
- [ ] Verify that old scripts still run and write to old DBs during transition.
- [ ] Test backup and restore.
- [ ] Review schema for tenant-awareness (organization_id, business_id present).

#### Why This Comes After WP1
Schema design can begin before secrets are fully migrated, but data migration from existing sources requires token access to validate live data. More importantly, the database is the foundation for the Business State; it must be authoritative before we build anything on top of it.

#### What Future Work It Unlocks
- Business State builder (WP4)
- Connector abstraction (WP3)
- All modules: Finance, Inventory, Advertising, etc.
- Multi-tenancy (later phase)
- Analytics and AI reasoning

#### Rollback Strategy
If the new DB is unstable or migration fails, keep old DBs as the source of truth. Revert connector/module writes to old DBs. The migration can be re-run after fixes.

#### Alignment with COS Architecture
The Business Database is the single source of truth. It is the most critical architectural component. The schema must be marketplace-agnostic and tenant-aware, even if only one organization exists today.

---

### Work Package 3: Marketplace Connector Layer — Shopee Implementation

#### Business Objective
Establish a clean, reusable way to integrate with ecommerce marketplaces. Shopee is the first connector, but the architecture must allow Lazada, Tokopedia, TikTok Shop, Meta, and Google to be added later without rewriting core business logic.

#### Technical Objective
- Define the canonical connector interface.
- Implement the Shopee Connector as the first adapter.
- Move all Shopee-specific API logic (authentication, signing, pagination, rate limiting, retries) into the connector.
- Ensure the connector outputs canonical business entities, not Shopee API responses.
- Fix the broken order/income API integration through the connector.

#### Deliverables
- `Connector` base class / interface with methods: `authenticate`, `get_orders`, `get_order_detail`, `get_order_income`, `get_products`, `get_inventory`, `get_campaigns`, `get_ads`, `get_ad_performance`, `get_payments`, `get_reviews`, `get_returns`, `apply_action`, `health_check`.
- `ShopeeConnector` implementing the interface.
- `ConnectorRegistry` to load and manage connectors per marketplace.
- `ConnectorHealth` model with status, last_sync, errors, token_expiry.
- Token refresh logic centralized in the connector.
- Fix for order detail and income API issues (current financial engine is broken).
- Connector tests with mock API responses.
- Documentation: connector architecture and Shopee-specific notes in Obsidian.

#### Dependencies
- Work Package 1 (secrets for API authentication).
- Work Package 2 (canonical DB to store connector outputs).
- Shopee API documentation and credentials.

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Shopee API changes during implementation | Medium | Medium | Versioned connector; abstraction isolates impact |
| Income API remains broken/unreliable | Medium | High | Document fallback logic; use order-level computation where possible |
| Connector abstraction becomes too generic | Medium | Medium | Start with concrete Shopee needs; generalize carefully |
| Rate limiting blocks sync | Medium | Medium | Built-in retries, backoff, and scheduling |

#### Success Criteria
- [ ] Shopee Connector implements the full interface.
- [ ] Connector outputs canonical entities (Order, Product, etc.) not Shopee raw responses.
- [ ] Order and income data sync correctly into canonical DB.
- [ ] Token refresh is automatic and logged.
- [ ] Health check returns status for all connector methods.
- [ ] Tests pass with mock Shopee API responses.

#### Estimated Complexity
**High.** The connector layer is where the platform’s long-term flexibility is won or lost. It must be done carefully.

#### Validation Checklist
- [ ] Run connector health check.
- [ ] Sync orders and compare against Shopee Seller Center.
- [ ] Sync ad performance and compare against Shopee Ads dashboard.
- [ ] Verify token refresh before token expiry.
- [ ] Test retry and backoff on simulated API failures.

#### Why This Comes After WP2
The connector must have a canonical schema to write into. Without the canonical DB, the connector would produce data with no home. WP1 and WP2 provide the foundation.

#### What Future Work It Unlocks
- Adding Lazada, Tokopedia, TikTok connectors (Phase 6).
- Cross-marketplace reporting.
- Business State builder.
- All modules that consume marketplace data.

#### Rollback Strategy
If the connector fails, keep the old `shopee_client.py` and scripts operational. Switch data flow back to old scripts. The new connector is a parallel path until validated.

#### Alignment with COS Architecture
The Marketplace Connector Layer is the boundary between external platforms and internal business concepts. It enforces the principle that the core platform never depends on Shopee-specific APIs.

---

### Work Package 4: Business State Builder

#### Business Objective
Produce the canonical, always-current Business State that every agent, dashboard, report, and notification reads. This is the heartbeat of the platform.

#### Technical Objective
- Build a deterministic Business State builder that queries the canonical DB and computes the current snapshot.
- Define the Business State schema (from Phase 0C Part 5).
- Implement freshness tracking, data quality scoring, and source attribution.
- Persist snapshots with versioning and history.
- Expose the Business State to consumers via a stable interface.

#### Deliverables
- `BusinessStateBuilder` service.
- `BusinessState` model with all fields: metadata, summary, KPIs, inventory, orders, ads, cashflow, risks, open actions, pending decisions, etc.
- Snapshot persistence with versioning.
- Data quality scoring engine.
- Source freshness tracker.
- `BusinessStateStore` for reading/writing snapshots.
- Event emission on state update (`business_state.updated`).
- Documentation: Business State schema and usage in Obsidian.

#### Dependencies
- Work Package 2 (canonical DB).
- Work Package 3 (connector data flowing into DB).
- Definition of KPIs and thresholds by Gerard.

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| State computation is too slow | Medium | Medium | Materialized views, caching, incremental updates |
| Data quality score is inaccurate | Medium | High | Validate against known good days and manual checks |
| Snapshot becomes too large | Low | Medium | Store only necessary fields; archive old snapshots |
| Missing fields force redesign | Medium | Medium | Extensible schema with typed fields |

#### Success Criteria
- [ ] Business State snapshot generated after each data sync.
- [ ] Snapshot contains all fields from Phase 0C schema.
- [ ] Data quality score reflects actual data quality (e.g., drops when income API missing).
- [ ] Consumers can read the latest snapshot without direct DB access.
- [ ] Historical snapshots retained for 90 days.

#### Estimated Complexity
**Medium-High.** The concept is straightforward, but the data quality scoring and freshness tracking require careful design.

#### Validation Checklist
- [ ] Generate snapshot manually and inspect all fields.
- [ ] Compare `revenue_today`, `profit_today`, `orders_today` against manual calculation.
- [ ] Simulate missing data and verify quality score drops.
- [ ] Verify event emission on state update.
- [ ] Check snapshot history retention.

#### Why This Comes After WP3
The Business State is derived from the canonical DB. The DB must be populated by connectors before the state can be meaningful. Building it earlier would produce empty or misleading state.

#### What Future Work It Unlocks
- All AI agents and the COO agent (Phase 3-4).
- Dashboards and reports (WP5).
- Notifications and alerts (WP5).
- Decision Engine and Approval Engine (Phase 3).

#### Rollback Strategy
If the Business State builder produces incorrect values, fall back to manual reports and direct DB queries. The canonical DB remains authoritative, so rollback is non-destructive.

#### Alignment with COS Architecture
Business State is the central artifact. Every module either produces, consumes, or validates it. This work package makes the architecture real.

---

### Work Package 5: Observability, Control, and Notifications

#### Business Objective
Make the system visible, trustworthy, and recoverable. Gerard and future operators must know when the system is healthy, when it fails, and what actions it has taken — without guessing.

#### Technical Objective
- Build a structured logging system across all components.
- Implement health checks and a health dashboard.
- Implement alerting and notification routing.
- Build an audit trail for all actions and state changes.
- Implement error recovery: retries, dead-letter queue, circuit breakers.
- Create an automation dashboard showing schedules, last runs, and outcomes.

#### Deliverables
- Structured JSON logger with correlation IDs, component tags, and secret masking.
- `HealthCheck` service covering connectors, DB, Business State, automation schedules.
- `NotificationRouter` supporting Telegram, email, and future channels.
- `AuditLog` service recording every action, decision, and state change.
- Automation dashboard (Streamlit or web) showing:
  - Last sync times per connector
  - Recent errors and warnings
  - Open actions and pending decisions
  - Recent actions with verification status
- Retry/backoff/circuit breaker utilities.
- Alerting rules (P0-P3) and notification templates.
- Documentation: observability and incident response SOPs in Obsidian.

#### Dependencies
- Work Package 1 (secrets for notifications).
- Work Package 2 (DB for audit logs).
- Work Package 3 (connectors for health checks).
- Work Package 4 (Business State for dashboard data).

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Too many alerts causing alert fatigue | Medium | Medium | Start with P0/P1 only; tune thresholds |
| Health dashboard becomes noise | Medium | Low | Focus on actionable signals |
| Audit log volume grows quickly | Medium | Medium | Retention policy and archival |
| Notification delivery failures | Medium | Medium | Fallback channels and delivery tracking |

#### Success Criteria
- [ ] Every component emits structured logs.
- [ ] Health dashboard shows green/yellow/red status for all critical components.
- [ ] P0/P1 alerts are delivered within 1 minute.
- [ ] Audit log contains every action and state change.
- [ ] Automation dashboard displays last run times and outcomes.
- [ ] Retry/backoff tested on simulated failures.

#### Estimated Complexity
**Medium.** This is mostly integration and instrumentation, but it touches every component.

#### Validation Checklist
- [ ] Trigger a simulated API failure and verify retry/backoff.
- [ ] Trigger a validation failure and verify alert delivery.
- [ ] Review audit log entries for recent actions.
- [ ] Check health dashboard after each sync.
- [ ] Verify notification delivery to Telegram.

#### Why This Comes After WP4
Observability requires something to observe. The Business State and connectors provide the data. Without them, the dashboard is empty.

#### What Future Work It Unlocks
- AI agent monitoring (Phase 3-4).
- SLA tracking and compliance reporting.
- Autonomous action verification (Phase 4).
- Incident response automation.

#### Rollback Strategy
If observability tooling causes issues, disable the new dashboard/alerts and fall back to existing logs and Telegram messages. Core operations continue unaffected.

#### Alignment with COS Architecture
Observability is a cross-cutting capability. It supports the principle that every important action is observable and every automation is reversible.

---

### Work Package 6: Knowledge Architecture and Obsidian Migration

#### Business Objective
Establish Obsidian as the institutional memory of the platform. Gerard and future users must have a clear, structured, and machine-readable knowledge base that improves over time and prevents duplication.

#### Technical Objective
- Implement the Obsidian folder structure from Phase 0B.
- Create templates for machine-generated and human-written notes.
- Build a knowledge writer service that ACOS modules can use to generate reports, decisions, and status updates.
- Migrate existing notes into the new structure.
- Establish linking conventions and linting rules.
- Document SOPs for the core operational processes.

#### Deliverables
- Obsidian folder structure (Company, SOPs, Products, Suppliers, Finance, Operations, Marketing, Projects, Decisions, Incidents, Meetings, Executive, Agents, Archive).
- Templates for daily reports, weekly reports, monthly reviews, decision log, incident log, open actions, risks, pending decisions, KPIs, agent docs.
- `KnowledgeWriter` service with methods: `write_report`, `update_living_doc`, `append_decision`, `append_incident`, `link_notes`.
- Migration of existing notes into the structure.
- SOP documentation for: pricing decisions, ad budget changes, supplier communication, refunds, financial reconciliation, incident response.
- Link checker / knowledge linter (optional, can be manual initially).
- Documentation: knowledge architecture guide in Obsidian.

#### Dependencies
- Work Package 4 (Business State provides data for reports).
- Work Package 5 (Observability provides incidents for the log).
- Gerard’s participation in reviewing SOPs and folder structure.

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Gerard does not adopt the structure | Medium | High | Co-design structure; start small; demonstrate value |
| Machine-generated notes overwhelm human notes | Medium | Medium | Separate read-only machine notes from living docs |
| Note drift over time | Medium | Medium | Quarterly review cycle; linting rules |
| Obsidian sync conflicts | Low | Medium | Use git or Obsidian Sync; document workflow |

#### Success Criteria
- [ ] All existing notes migrated to new structure.
- [ ] Machine-generated reports are created automatically after each sync.
- [ ] SOPs are documented for core processes.
- [ ] KnowledgeWriter can update Open Actions, Risks, and Decision Log.
- [ ] Gerard can find any important note within 3 clicks.

#### Estimated Complexity
**Medium.** This is organizational and cultural as much as technical. The tooling is simple; the discipline is harder.

#### Validation Checklist
- [ ] Review Obsidian folder structure.
- [ ] Verify daily report generated with correct template.
- [ ] Verify Decision Log entry appended after a decision.
- [ ] Check SOPs cover pricing, ad budget, refunds, supplier communication, reconciliation, incident response.
- [ ] Confirm no orphaned or duplicate notes.

#### Why This Comes After WP5
Knowledge needs data to be useful. Business State, observability, and actions provide the content. Also, SOPs should be written based on real processes, not guessed.

#### What Future Work It Unlocks
- AI agents reading SOPs and context (Phase 3-4).
- Decision Log and incident post-mortems (Phase 3).
- Executive briefs and reports (Phase 2-4).
- Long-term institutional memory for SaaS customers.

#### Rollback Strategy
If the new structure is not adopted, keep old notes and structure alongside the new one. Revert to old notes if needed. No operational data is lost because truth lives in the Business DB.

#### Alignment with COS Architecture
Obsidian is the institutional memory. It is not the database. It is the place where meaning, context, decisions, and lessons live. This work package makes the knowledge architecture operational.

---

### Work Package 7: Legacy Script Sunset and Operational Cutover

#### Business Objective
Retire the old fragmented scripts and cut over daily operations to the new Commerce Operating System modules. This reduces technical debt and ensures the business runs on the new architecture.

#### Technical Objective
- Map each legacy script to a new module or workflow.
- Replace old cron jobs with module-based schedules.
- Ensure no writes to old SQLite DBs after cutover.
- Archive old scripts with documentation of their replacements.
- Validate that all daily reports, notifications, and dashboards work through the new system.
- Fix the broken `daily_growth_run.sh` Python path as part of the cutover.

#### Deliverables
- Legacy script inventory with mapping to new modules.
- New cron/workflow definitions using the new architecture.
- Archive folder for old scripts (read-only, clearly labeled).
- Migration runbook.
- Operational cutover checklist.
- Post-cutover validation report.
- Updated Obsidian SOPs for daily operations.

#### Dependencies
- Work Packages 1-6 complete.
- All new modules tested and validated.
- Gerard’s sign-off on cutover timing.

#### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cutover breaks daily operations | Medium | Critical | Parallel run period; rollback plan; Gerard available |
| Missing legacy behavior | Medium | High | Thorough inventory and testing of each script |
| New system slower than old | Low | Medium | Performance testing before cutover |
| Gerard discomfort with new paths | Medium | Medium | Training, documentation, and support period |

#### Success Criteria
- [ ] No old script runs in production.
- [ ] All daily reports generated by new modules.
- [ ] All notifications sent by new NotificationRouter.
- [ ] Old DBs are read-only and archived.
- [ ] Gerard can access Business State and dashboards.
- [ ] No P0 or P1 incidents for 7 days after cutover.

#### Estimated Complexity
**Medium.** This is mostly coordination and cleanup, but the cutover moment is high-stakes.

#### Validation Checklist
- [ ] Run a full day of operations through new system.
- [ ] Compare new reports to old reports for consistency.
- [ ] Verify all notifications are delivered.
- [ ] Check audit log for all actions.
- [ ] Confirm old scripts are archived and not scheduled.

#### Why This Comes Last
Cutover is only safe after the new architecture is proven. WP1-WP6 build the system; WP7 makes it the operational default.

#### What Future Work It Unlocks
- Phase 2: Reliable Commerce OS (dashboards, reports, briefs).
- Phase 3: Operational Intelligence (agents, decision engine).
- Phase 4: Commerce AI (COO, safe automation).
- All future work benefits from a clean, module-based architecture.

#### Rollback Strategy
If cutover fails, re-enable old scripts and revert cron jobs. Keep old DBs intact. The new system can be fixed and re-cutover later.

#### Alignment with COS Architecture
This work package enforces the principle that the system operates on modules and Business State, not on isolated scripts. It is the final cleanup of the old paradigm.

---

## Emergency Consolidation Work Package: Token Governance and Legacy Script Freeze (July 2026)

**Status:** In progress — triggered by recurring Shopee refresh-token death.

**Objective:** Stop all independent token refreshers, establish `token_manager.py` as the single source of truth, and prevent future refresh-token invalidation while the full Phase 1 cutover (WP7) is prepared.

**Problem:** There are 30+ scripts reading/writing `tokens_production.json` and `tokens_ads.json` directly. Shopee only allows one active refresh token per app-shop. Every independent refresh invalidates the others, causing tokens to die within hours of re-authorization.

**Immediate actions:**
1. Pause all cron jobs that independently touch tokens.
2. Make `token_manager.py` the only writer of token files (file locking, `_saved_at` metadata, one refresh path).
3. Add `token_manager.get_access_token(app_name)` as the canonical API for all other code.
4. Update `scripts/live_resync.py` to force-refresh via `token_manager.py` before sync.
5. Re-authorize production and ads apps; exchange codes via `token_manager.py --exchange`.
6. Verify health with `token_manager.py --health`.

**Transition actions (until WP7 full cutover):**
7. Wrap `daily_monitor.py`, `growth_engine.py`, and other active cron scripts so they call `token_manager.get_access_token()` instead of refreshing themselves.
8. Mark legacy direct-token scripts as deprecated; log warnings if they run.
9. Keep old scripts read-only or archive the non-essential ones.
10. Resume cron jobs only after they no longer refresh tokens independently.

**Success criteria:**
- [ ] Only `token_manager.py` writes token files.
- [ ] `token_manager.py --health` reports healthy for >24h after re-auth.
- [ ] All cron jobs run without independently refreshing tokens.
- [ ] Live resync succeeds end-to-end.

---

## Phase 1 Implementation Roadmap

| Sequence | Work Package | Duration | Dependencies | Key Deliverable |
|----------|--------------|----------|--------------|---------------|
| 1 | WP1: Secure Foundations | 1 week | None | Secret vault, no secrets in code |
| 2 | WP2: Canonical Business DB | 2-3 weeks | WP1 | Versioned schema, migrated data, backups |
| 3 | WP3: Marketplace Connector Layer | 2-3 weeks | WP1, WP2 | Shopee Connector, canonical entities, health check |
| 4 | WP4: Business State Builder | 1-2 weeks | WP2, WP3 | Current Business State snapshot with quality scoring |
| 5 | WP5: Observability, Control, Notifications | 2 weeks | WP1-WP4 | Health dashboard, audit log, alerts, automation dashboard |
| 6 | WP6: Knowledge Architecture / Obsidian | 1-2 weeks | WP4, WP5 | Folder structure, templates, SOPs, machine-generated reports |
| 7 | WP7: Legacy Script Sunset | 1-2 weeks | WP1-WP6 | Operational cutover to new modules |

**Total Estimated Duration:** 10-15 weeks, depending on Gerard’s availability and decision speed.

**Critical Path:** WP1 → WP2 → WP3 → WP4 → WP7. WP5 and WP6 can partially overlap with WP3/WP4 where dependencies allow.

---

## Why This Ordering

### WP1 First: Security
Without secure secrets, every other package is unsafe. Also, WP2 and WP3 require credential access during migration and connector implementation.

### WP2 Second: Database
The database is the single source of truth. The connector (WP3) must write into a canonical schema, and the Business State (WP4) must read from canonical data. Trying to build WP3 or WP4 before WP2 would force the connector to fit into fragmented legacy schemas, which is exactly the architectural debt we want to avoid.

### WP3 Third: Connector
The connector is the boundary between Shopee and the core. Once the DB exists, the connector can be built cleanly and tested. Fixing the broken income/order API happens here because the connector owns Shopee-specific translation.

### WP4 Fourth: Business State
Business State is derived. It needs the DB and connector to be populated first. Building it earlier would mean building on empty or legacy data.

### WP5 Fifth: Observability
Observability needs data to observe. Once connectors and Business State exist, health checks, dashboards, and alerts become meaningful. It could overlap with WP4 but should be finalized after WP4.

### WP6 Sixth: Knowledge
Knowledge needs content. Reports, decisions, incidents, and SOPs all depend on the Business State and observability. It also needs Gerard’s participation, which is easier once the system is demonstrably working.

### WP7 Last: Cutover
Cutover is the final step. It only happens when the new system is proven to run the business correctly. This minimizes risk.

---

## Challenge to My Own Ordering

I considered starting with WP2 (database) before WP1 (secrets), because schema design is independent of credential migration. However, the data migration step requires live API access to validate order/income data, and the connector implementation (WP3) requires secrets. The risk of exposing secrets during active migration outweighs the small benefit of parallel starts. So WP1 remains first.

I also considered moving WP5 (Observability) earlier, because it helps debug WP2-WP4. But observability without a DB or connector is mostly empty dashboards. The better approach is to add lightweight logging from the start of WP2, then finalize observability in WP5. This is acceptable: implement lightweight logging early, but treat full observability as a WP5 deliverable.

I also considered making WP7 a gradual rollout per script rather than one cutover. This is actually better: sunset scripts one by one as their replacements are validated. I have updated WP7 to emphasize a gradual, script-by-script cutover rather than a big-bang switch. This reduces risk and keeps operations stable.

---

## First Work Package to Execute

**WP1: Secure Foundations and Secret Management.**

This is the only choice for the first package. Every other package depends on it either directly or indirectly. It also immediately reduces the largest security risk in the current system (hardcoded credentials and plaintext tokens) and establishes the discipline that secrets are a platform capability, not a script detail.

---

## Success Criteria for Phase 1 as a Whole

After Phase 1, the following must be true:

- [ ] No secrets in code or plaintext files.
- [ ] One canonical business database with schema migrations and backups.
- [ ] Shopee connector outputs canonical business entities into the canonical DB.
- [ ] Order and income sync works correctly.
- [ ] Business State is generated after each sync and is the primary context for operations.
- [ ] Health dashboard, audit log, and notifications are operational.
- [ ] Obsidian knowledge architecture is established and populated with SOPs and reports.
- [ ] Legacy scripts are retired and the business runs on modules.
- [ ] The system is more secure, observable, and maintainable than before.
- [ ] Future phases (AI, decision engine, multi-store, multi-marketplace) are unlocked and easier to build.

---

## Risks for Phase 1 as a Whole

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Phase takes longer than planned | High | Medium | Break into sprints; deliver visible value each sprint; prioritize WP1-WP4 |
| Gerard’s time/attention unavailable | Medium | High | Weekly review meetings; clear decisions needed from Gerard |
| Shopee API instability | Medium | High | Versioned connector; abstraction layer; fallback logic |
| Data migration reveals deeper data quality issues | Medium | High | Validate aggressively; quarantine bad data; escalate to Gerard |
| Over-engineering for one shop | Medium | Medium | Validate every abstraction against future use case; keep implementations simple |
| Underestimating complexity of canonical DB | Medium | High | Start with full schema but populate incrementally; use migrations |

---

## Final Notes

Phase 1 is intentionally foundational. It does not deliver flashy AI or autonomous budget changes. It delivers the architecture that makes those things possible and safe.

The most important principle:

> **Build the platform. Use Gerard’s business as the validation environment. Do not let the validation environment dictate the architecture.**

This plan is ready for review. Awaiting approval.
