# Phase 0B — Architecture Blueprint
## Autonomous Commerce Operating System (ACOS)

**Role:** Principal Systems Architect
**Date:** 2026-07-16
**Scope:** Long-term architecture for Gerard’s commerce operations, designed to scale beyond a single platform or business.
**Status:** Proposed — awaiting approval before any implementation.

---

## Executive Summary

The current system is a collection of useful but tightly-coupled Python scripts that talk directly to Shopee APIs, store data in local SQLite files, and notify via Telegram. It works in parts, but it is not yet a system that can be safely delegated to AI.

This blueprint designs a production-grade **Autonomous Commerce Operating System (ACOS)**. ACOS is a *state-driven, observable, multi-platform commerce control plane*. Hermes is one component within it — specifically, the **cognitive orchestrator / COO layer** — not the system itself.

The goal is to move from:

> “Scripts that fetch data and send reports”

to:

> “A business state machine where deterministic workers collect validated data, department agents reason about it, and a COO agent prioritizes actions, proposes decisions, and escalates uncertainty.”

---

## 0. Architectural Assumptions I Am Challenging

Before designing the target, I am explicitly questioning several current assumptions:

| Current Assumption | Challenge | Proposed Replacement |
|--------------------|-----------|----------------------|
| SQLite files in the workspace are fine for now. | They are already creating truth conflicts (ads DB has 65 rows, financial DB has 2 ad rows, orders table empty). | A single versioned business database with schema enforcement and migrations. |
| Hermes should call scripts directly and parse outputs. | This makes Hermes both orchestrator and executor. It couples reasoning to implementation. | Hermes consumes **Business State** and issues **intents**; deterministic workers execute them. |
| Obsidian is a place to dump notes. | It is actually the most organized source Gerard has. It should be treated as institutional memory, not a scratchpad. | A structured knowledge architecture with machine-readable and human-readable partitions. |
| Shopee is the only platform we need to support. | Gerard will likely add Lazada, Tokopedia, TikTok Shop, Meta/Google Ads. | A **platform abstraction layer** so each new channel is a connector, not a rewrite. |
| Auto-optimizer should adjust budgets automatically. | Current code changes budgets even when API returns zero data. | Budget changes are **proposals** requiring approval above confidence/impact thresholds. |
| Telegram messages are the reporting system. | They are notifications. They are not searchable, auditable, or structured. | Reports live in Business DB + Obsidian; Telegram is a delivery channel. |
| Secrets can live in JSON files and code. | Hardcoded partner keys and plaintext tokens are a security incident waiting to happen. | Central secret vault with environment separation and rotation. |

---

## 1. System Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL WORLD                                   │
│  Shopee Seller API   Shopee Ads API   Lazada   Tokopedia   TikTok   Meta  │
│   Suppliers            Banks              Couriers          Customers      │
└──────────┬──────────────────────┬──────────────────────────────┬──────────┘
           │                      │                              │
           ▼                      ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DATA COLLECTION LAYER (Deterministic)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Shopee      │  │   Ads        │  │   Platform   │  │   External   │   │
│  │  Connector   │  │  Connector   │  │  Connectors  │  │  Connectors   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│        │                  │                  │                  │            │
│        ▼                  ▼                  ▼                  ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      VALIDATION & NORMALIZATION LAYER               │   │
│  │  Schema validation · Reconciliation · Anomaly detection · Deduplication │ │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BUSINESS DATABASE (Source of Truth)                  │
│  orders · order_items · products · inventory · ads · campaigns · spend      │
│  income · expenses · cogs · cashflow · supplier_events · shipments           │
│  customer_tickets · risks · actions · decisions · audit_log                  │
└─────────────────────────────────┬─────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BUSINESS STATE (Derived Context)                     │
│  Daily KPIs · Revenue · Profit · Inventory · Orders · Ads · Cashflow       │
│  Supplier Issues · Shipping Issues · Customer Issues · Risks · Priorities    │
│  Open Actions · Pending Decisions                                          │
│                                                                              │
│  This is the canonical context every AI agent reads.                        │
└─────────────────────────────────┬─────────────────────────────────────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐   ┌─────────────────────┐   ┌─────────────────────────────┐
│  DEPARTMENT     │   │  OBSIDIAN           │   │  OBSERVABILITY & CONTROL   │
│  AGENTS         │   │  KNOWLEDGE BASE     │   │  PLANE                     │
│                 │   │                     │   │                            │
│  Finance Agent  │   │  Company            │   │  Health Dashboard          │
│  Inventory Agent│   │  SOPs               │   │  Automation Dashboard      │
│  Growth Agent   │   │  Strategy           │   │  Execution History           │
│  Ops Agent      │   │  Products           │   │  Structured Logs             │
│  Customer Agent │   │  Suppliers          │   │  Alert System                │
│  Compliance     │   │  Projects           │   │  Audit Trail                 │
│  Supplier Agent │   │  Decision Log       │   │  Error Recovery              │
│  Analytics      │   │  Lessons Learned    │   │  Metrics / SLA               │
│                 │   │  Incidents          │   │                            │
└────────┬────────┘   │  KPIs / Reports     │   └─────────────────────────────┘
         │            │  Meeting Notes      │
         │            │  Executive Reports  │
         │            │  Agent Documentation│
         │            └──────────┬──────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │   HERMES COO AGENT       │
        │  (Cognitive Orchestrator) │
        │                          │
        │  Reads Business State    │
        │  Reads Obsidian          │
        │  Hears Department Agents │
        │  Prioritizes actions     │
        │  Proposes decisions      │
        │  Escalates uncertainty   │
        │  Approves within policy  │
        └──────────────────────────┘
```

### 1.2 Major Components

| Component | Role | Technology-agnostic Description |
|-----------|------|----------------------------------|
| **External APIs** | Sources of truth for marketplaces, ads, logistics, banks, suppliers. | Shopee, Lazada, Tokopedia, TikTok, Meta, Google, courier APIs, banking APIs, supplier APIs. |
| **Data Collection Layer** | Deterministic workers that fetch, authenticate, rate-limit, and retry external data. | Never contains business logic beyond retries and normalization. |
| **Validation Layer** | Schema validation, anomaly detection, reconciliation between sources. | Rejects bad data before it enters the Business DB. |
| **Business Database** | The single source of truth for operational data. | Schema-enforced, versioned, backed up, queryable. |
| **Business State** | A derived, always-current summary of the business. | The primary context fed to all agents. |
| **Department Agents** | Specialized AI agents that reason about one domain and propose actions. | Read Business State, read/write Obsidian domain notes, emit proposals. |
| **Hermes COO** | The orchestrating agent that prioritizes, decides, escalates, and communicates. | Reads Business State, reads Obsidian, delegates to department agents, approves within policy. |
| **Obsidian Knowledge Base** | Institutional memory: SOPs, strategy, decisions, incidents, reports, agent docs. | Human-written + machine-generated + read-only + continuously updated partitions. |
| **Dashboards** | Human-facing interfaces for monitoring, control, and reporting. | Health dashboard, automation dashboard, financial dashboard, executive dashboard. |
| **Notifications** | Delivery channels for alerts and reports. | Telegram, email, SMS, Slack — but never the primary store. |

---

## 2. System Boundaries

### 2.1 What Deterministic Code Does

Deterministic code is responsible for everything that must be **exact, repeatable, auditable, and fast**:

| Responsibility | Examples |
|----------------|----------|
| Fetch data from APIs | OAuth, token refresh, pagination, rate limiting, retries |
| Validate and normalize | Schema checks, unit conversion, currency normalization, deduplication |
| Persist data | Inserts, updates, migrations, backups, archival |
| Compute deterministic metrics | Revenue = sum(order_items), COGS = units × cogs_per_unit, Profit = revenue - cogs - expenses - ad_spend |
| Enforce business rules | “Do not reduce price below COGS × 1.05”, “Do not spend more than daily budget” |
| Execute approved actions | Update campaign budget, send message, create supplier PO, update inventory |
| Generate logs and audit trails | Every API call, every state change, every decision |
| Recover from failures | Retry with backoff, circuit breakers, dead-letter queues |
| Serve dashboards | Read Business DB, render charts, expose health endpoints |

### 2.2 What AI Does

AI is responsible for everything that requires **judgment, pattern recognition, prioritization, and communication**:

| Responsibility | Examples |
|----------------|----------|
| Interpret anomalies | “Why did ROAS drop 40% today?” |
| Prioritize actions | “Which issues are existential vs. noise?” |
| Propose decisions | “Increase budget by 15% because stock is high and ROAS is strong” |
| Draft communications | Supplier emails, customer replies, executive summaries |
| Synthesize context | Combine Business State, Obsidian, and external news into a morning brief |
| Detect risks | “Supplier lead time is increasing; we may stock out in 7 days” |
| Learn from incidents | Update SOPs and lessons learned after failures |
| Negotiate trade-offs | “Lower price to move inventory vs. hold margin” |
| Coordinate agents | COO delegates tasks, integrates outputs, resolves conflicts |

### 2.3 What NEVER Gets Delegated to AI

These are hard boundaries. Violating them destroys trust and creates legal/financial risk.

| Forbidden to AI | Why | Who Owns It |
|-----------------|-----|-------------|
| Direct money movement | Bank transfers, supplier payments, payroll | Human + bank tooling |
| Final pricing decisions without policy guardrails | Can trigger price wars or margin destruction | Human or deterministic rule engine |
| Changing ad budgets above a threshold | Current system already does this dangerously | Deterministic proposal + human approval |
| Issuing refunds or returns | Customer trust and accounting impact | Human or explicit policy engine |
| Modifying production secrets | Security risk | Human via secret vault |
| Changing core business rules | Strategy-level decisions | Human + Decision Log |
| Accessing credentials or keys | AI should never see secrets | Secret vault |
| Any action that cannot be undone | One-way doors require human sign-off | Human |
| Legal or tax filings | Liability | Human + accountant |
| Single-source financial reconciliation | AI must not self-validate its own numbers | Deterministic reconciliation engine |

---

## 3. Business State

### 3.1 Definition

The **Business State** is a derived, always-current, machine-readable summary of the business. It is the canonical context every agent reads before acting. It is not stored as a single JSON blob; it is a set of structured views/tables derived from the Business Database and refreshed on a schedule.

### 3.2 Contents

| Domain | Key Fields | Source |
|--------|-----------|--------|
| **Daily KPIs** | revenue, orders, aov, units, sessions, conversion_rate, roas, mer, net_profit | Computed from orders + ads + expenses |
| **Revenue** | gross_revenue, net_revenue, discounts, shipping_paid, platform_fees | Orders + income API |
| **Profit** | gross_profit, net_profit, profit_margin, contribution_margin | Revenue - COGS - expenses - ad_spend - platform_fees |
| **Inventory** | sku_levels, stock_value, days_of_inventory, low_stock_skus, overstock_skus | Seller API + supplier data |
| **Orders** | new_orders, pending_orders, shipped, returned, cancellation_rate | Orders API |
| **Ads** | spend, impressions, clicks, ctr, conversion, roas, mer, campaigns_by_status | Ads API |
| **Cashflow** | cash_balance, incoming_payouts, upcoming_expenses, runway | Bank + platform payouts + expense schedule |
| **Supplier Issues** | delayed_shipments, quality_flags, price_changes, lead_time_drift | Supplier agent + manual input |
| **Shipping Issues** | late_deliveries, lost_packages, courier_failures, customer_complaints | Ops agent + courier APIs |
| **Customer Issues** | open_tickets, negative_reviews, refund_requests, repeat_complaint_topics | Customer agent + platform APIs |
| **Risks** | risk_id, severity, probability, impact, owner, mitigation_status | All agents + COO |
| **Priorities** | ranked list of top 5 current priorities with owner and deadline | COO generates |
| **Open Actions** | action_id, description, owner, due, status, source_agent | Agents + COO |
| **Pending Decisions** | decision_id, question, options, confidence, recommended_option, approval_required | Decision Engine |

### 3.3 Where It Lives

- **Primary store:** Business Database (relational, versioned, backed up).
- **Derived materialized views:** `business_state_current`, `business_state_today`, `business_state_rolling_7d`, `business_state_rolling_30d`.
- **Working context:** A constrained, prompt-safe snapshot (JSON or structured text) loaded into Hermes and department agents at the start of each run.

### 3.4 How It Is Generated

1. **Collectors** fetch raw data from APIs on schedule.
2. **Validation Layer** checks schema, anomalies, and reconciliation rules.
3. **Business DB** stores validated raw data.
4. **State Builder** (deterministic) computes materialized views.
5. **State Publisher** writes the current snapshot to a known location and emits a `business_state_updated` event.
6. **Agents** consume the snapshot.

### 3.5 Update Frequency

| View | Frequency | Trigger |
|------|-----------|---------|
| Orders | Every 15-60 minutes | Cron + webhook (if available) |
| Inventory | Every 1-6 hours | Cron |
| Ads | Every 1-4 hours | Cron (token refresh before each) |
| Financials | Every 6 hours | Cron + after manual sync |
| Supplier/Shipping | Daily + event-driven | Agent + manual input |
| Business State snapshot | After every data update + on-demand | Event-driven |

### 3.6 Ownership

| Owner | Responsibility |
|-------|---------------|
| **Deterministic State Builder** | Ensures numbers are correct and consistent. |
| **Finance Agent** | Validates profit/cash logic and flags inconsistencies. |
| **COO Agent** | Interprets the state, prioritizes, and communicates. |
| **Gerard (human)** | Defines KPIs, thresholds, and strategic targets. |

### 3.7 Consumers

- Department agents
- Hermes COO
- Dashboards
- Notifications
- Obsidian reports (machine-generated sections)

---

## 4. Obsidian Architecture

### 4.1 Design Principle

Obsidian is the company’s **institutional memory**. It is not a database. It is the place where meaning, context, decisions, and lessons live. The architecture must separate:

- **Human thinking** (strategy, reflections, meeting notes)
- **Machine records** (daily reports, incident timelines, KPI summaries)
- **Read-only references** (SOPs, policies, agent documentation)
- **Living documents** (priorities, risks, open actions)

### 4.2 Folder Architecture

```
Obsidian Vault/
├── Company/
│   ├── Vision & Strategy.md          (human-written, living)
│   ├── Business Model.md             (human-written, reference)
│   ├── Operating Principles.md       (human-written, reference)
│   └── Org Chart & Roles.md          (human-written, reference)
├── SOPs/
│   ├── Pricing Decisions.md          (human-written, reference)
│   ├── Ad Budget Changes.md          (human-written, reference)
│   ├── Supplier Communication.md     (human-written, reference)
│   ├── Refunds & Returns.md          (human-written, reference)
│   ├── Financial Reconciliation.md   (human-written, reference)
│   └── Incident Response.md          (human-written, reference)
├── Products/
│   ├── SKU Master Index.md           (machine-generated daily, reference)
│   ├── SKU-XXXXX.md                  (per-product notes, mixed human/machine)
│   └── Product Launch Playbook.md    (human-written, reference)
├── Suppliers/
│   ├── Supplier Master Index.md      (machine-generated weekly, reference)
│   ├── Supplier X.md                 (mixed human/machine, living)
│   └── Supplier Evaluation.md        (machine-generated quarterly, reference)
├── Finance/
│   ├── Daily Reports/
│   │   └── 2026-07-16.md           (machine-generated daily, read-only after publish)
│   ├── Weekly Reports/
│   │   └── 2026-W28.md             (machine-generated weekly, read-only)
│   ├── Monthly Reviews/
│   │   └── 2026-06.md              (machine-generated monthly, read-only)
│   ├── KPIs.md                       (machine-generated, updated daily, reference)
│   └── Profitability Model.md        (human-written, reference)
├── Operations/
│   ├── Open Actions.md               (machine-generated, living)
│   ├── Risks.md                      (machine-generated, living)
│   ├── Pending Decisions.md          (machine-generated, living)
│   ├── Inventory Status.md           (machine-generated, updated 6-hourly, reference)
│   ├── Shipping Issues.md            (machine-generated, living)
│   ├── Supplier Issues.md            (machine-generated, living)
│   └── Customer Issues.md            (machine-generated, living)
├── Marketing & Growth/
│   ├── Campaign Notes.md             (mixed human/machine, living)
│   ├── Creative Performance.md       (machine-generated, living)
│   └── Channel Strategy.md           (human-written, reference)
├── Projects/
│   ├── Active/
│   │   └── Dashboard Upgrade.md      (human-written, living)
│   ├── Archive/                      (completed projects, read-only)
│   └── Backlog/                      (human-written, reference)
├── Decisions/
│   ├── Decision Log.md               (machine-generated, append-only, read-only)
│   └── Proposals/
│       └── 2026-07-16 Increase Lazada Budget.md (human-written after approval, read-only)
├── Incidents/
│   ├── Incident Log.md               (machine-generated, append-only, read-only)
│   ├── Post-Mortems/                 (human-written, read-only)
│   └── Lessons Learned.md            (human-written, reference)
├── Meetings/
│   └── 2026-07-16 Weekly Review.md (human-written, read-only)
├── Executive/
│   ├── Morning Brief.md              (machine-generated daily, read-only)
│   ├── Weekly Executive Summary.md   (machine-generated weekly, read-only)
│   └── Quarterly Review.md           (machine-generated + human commentary, read-only)
├── Agents/
│   ├── Agent Registry.md             (human-written, reference)
│   ├── Finance Agent.md              (human-written, reference)
│   ├── Inventory Agent.md            (human-written, reference)
│   ├── Growth Agent.md               (human-written, reference)
│   ├── Operations Agent.md           (human-written, reference)
│   ├── Customer Agent.md             (human-written, reference)
│   ├── Compliance Agent.md           (human-written, reference)
│   ├── Supplier Agent.md             (human-written, reference)
│   ├── Analytics Agent.md            (human-written, reference)
│   └── COO Agent.md                  (human-written, reference)
└── Archive/
    └── (old reports, decisions, incidents — read-only)
```

### 4.3 Document Ownership Rules

| Type | Who Writes | Who Updates | Mutable? | Versioning |
|------|-----------|-------------|----------|------------|
| **Human-written** | Gerard / humans | Gerard / humans | Yes | Git commits or Obsidian version history |
| **Machine-generated** | ACOS | ACOS | No after publish | Append-only or timestamped files |
| **Living** | ACOS | ACOS | Yes, continuously | Always overwrite latest, keep history in archive |
| **Reference** | Humans + ACOS | Humans + ACOS | Yes, but controlled | Git |
| **Read-only** | ACOS | Never | No | Timestamped, immutable |
| **Append-only** | ACOS | ACOS append only | No edit, only append | Natural log |

### 4.4 Machine-Readable Notes

Some notes must be machine-readable (YAML frontmatter + structured sections) so agents can read them without parsing ambiguity:

- `Open Actions.md`
- `Risks.md`
- `Pending Decisions.md`
- `KPIs.md`
- `Decision Log.md`
- `Incident Log.md`
- `SKU Master Index.md`
- `Supplier Master Index.md`
- All agent documentation

### 4.5 Human-Readable Notes

Some notes are intentionally free-form for human thinking:

- `Vision & Strategy.md`
- `Meeting notes`
- `Post-Mortems`
- `Creative notes`
- Personal reflections

---

## 5. AI Agent Architecture

### 5.1 Design Principle

Agents are **specialized reasoning units**, not omnipotent assistants. Each agent has a narrow domain, well-defined inputs/outputs, allowed actions, and explicit forbidden actions. They do not execute directly; they propose to the COO or to a deterministic rule engine.

### 5.2 Agent Registry

| Agent | Responsibilities | Inputs | Outputs | Allowed Actions | Forbidden Actions | Dependencies |
|-------|-----------------|--------|---------|-----------------|-------------------|--------------|
| **Finance Agent** | P&L analysis, cashflow forecasting, margin alerts, expense validation, reconciliation flags | Business State, orders, income, expenses, COGS, bank data | Profit reports, cash warnings, expense anomalies, reconciliation issues | Propose budget shifts, flag pricing issues, request COGS updates | Move money, change prices, approve spending without policy | Business DB, Bank API, seller income API |
| **Inventory Agent** | Stock levels, reorder points, days of inventory, overstock/understock, supplier lead times | Business State, SKU data, supplier data, sales velocity | Reorder recommendations, stockout risks, overstock actions | Propose PO quantities, propose promotions to clear stock | Place supplier orders, change prices directly | Seller API, supplier data, Business DB |
| **Growth Agent** | Ad performance, ROAS, MER, campaign optimization, budget allocation, channel mix | Business State, ads data, campaign settings, financials | Budget proposals, campaign pause/resume proposals, creative tests | Propose budget changes, propose new campaigns, propose bid changes | Apply budget changes without approval, delete campaigns | Ads API, Business DB |
| **Operations Agent** | Order fulfillment, shipping, returns, courier issues, warehouse coordination | Business State, orders, shipments, courier data | Fulfillment alerts, shipping issue flags, return recommendations | Propose courier escalation, propose refund within policy, flag delays | Issue refunds without policy, change shipping fees | Seller API, courier APIs, Business DB |
| **Customer Agent** | Reviews, tickets, complaints, repeat issue detection, response drafting | Business State, reviews, tickets, chat logs | Response drafts, escalation flags, satisfaction trends | Draft replies, propose refund/gift within policy, flag abuse | Send final replies without human review above threshold | Platform APIs, Business DB |
| **Supplier Agent** | Supplier performance, price changes, lead times, quality issues, negotiation support | Business State, supplier communications, POs, receipts | Supplier scorecards, negotiation talking points, risk flags | Draft negotiation emails, propose alternative suppliers | Commit to POs, sign contracts | Email, supplier data, Business DB |
| **Compliance Agent** | Tax readiness, invoice tracking, platform policy changes, regulatory alerts | Business State, transaction data, platform policies | Compliance alerts, tax summary drafts, policy change summaries | Request documentation, flag missing invoices | File taxes, submit legal documents | Business DB, platform policies |
| **Analytics Agent** | Trend analysis, cohort analysis, forecasting, anomaly detection, experiment design | Business State, historical data, external data | Forecasts, anomaly reports, experiment recommendations, dashboards | Propose experiments, propose data collection changes | Make operational decisions | Business DB, external data sources |
| **COO Agent** | Prioritization, cross-functional coordination, decision synthesis, escalation, communication | Business State, Obsidian, all agent proposals, human messages | Priorities, approved/rejected decisions, escalations, morning/evening briefs, open actions | Approve within policy, escalate, delegate, notify, update Obsidian | Execute actions directly, override policy without human sign-off, change secrets | All agents, Business DB, Obsidian, notifications |

### 5.3 Agent Communication Pattern

```
Agent receives task/context
        │
        ▼
Agent reads Business State + Obsidian references
        │
        ▼
Agent produces proposal / report / alert
        │
        ▼
Proposal goes to COO Agent (or deterministic rule engine if below threshold)
        │
        ▼
COO evaluates, resolves conflicts, assigns owner
        │
        ▼
If approved: deterministic executor carries out action
If uncertain: escalate to Gerard
If rejected: log reason
        │
        ▼
Outcome written to Business DB + Obsidian Decision Log / Incident Log
```

### 5.4 Agent Memory

Agents do not have long-term memory. They read:

1. **Business State** (current context)
2. **Obsidian reference documents** (SOPs, agent docs, product/supplier notes)
3. **Decision Log** (recent decisions)
4. **Incident Log** (recent failures)
5. **Agent Registry** (who does what)

This prevents memory drift and makes every agent decision explainable from current documents.

---

## 6. COO Architecture

### 6.1 Role

Hermes acts as the **COO Agent**. It is not a general-purpose chatbot. It is a function that reads Business State and Obsidian, coordinates department agents, and produces decisions/briefings/actions.

### 6.2 Daily Workflows

#### Morning Workflow (8:00 AM)

1. **Ingest Business State** — load latest snapshot.
2. **Review overnight events** — incidents, anomalies, new orders, ad spend.
3. **Read Obsidian** — yesterday’s evening check, open actions, risks, pending decisions.
4. **Delegate to agents** — ask each agent for top issues and proposals.
5. **Synthesize priorities** — produce `Open Actions.md` and `Priorities` section.
6. **Generate Morning Brief** — write to `Executive/Morning Brief.md` and send Telegram summary.
7. **Queue approved low-risk actions** — deterministic executor runs them.
8. **Escalate uncertain items** — present to Gerard for decision.

#### Midday Workflow (2:00 PM)

1. **Refresh Business State**.
2. **Check progress against morning priorities**.
3. **Flag any new risks**.
4. **Send pulse check** to Telegram (short, actionable).

#### Evening Workflow (8:00 PM)

1. **Load full-day Business State**.
2. **Summarize day** — revenue, profit, orders, ads, issues.
3. **Review open actions** — close completed, reschedule pending.
4. **Update risks and pending decisions**.
5. **Generate Evening Brief** — write to Obsidian and send Telegram.
6. **Prepare next-day priorities** for morning review.

#### Weekly Review

1. Compile 7-day KPIs and trends.
2. Review agent proposals and decisions made.
3. Update `Weekly Executive Summary.md`.
4. Identify next-week priorities and resource needs.
5. Schedule any human-required decisions.

#### Monthly Review

1. Reconcile full month.
2. Generate P&L, cashflow, balance sheet summaries.
3. Review supplier performance and product profitability.
4. Update `Monthly Reviews/` and `Quarterly Review` draft.
5. Present strategic questions to Gerard.

#### Quarterly Review

1. Analyze 90-day trends.
2. Evaluate strategy vs. targets.
3. Update `Vision & Strategy.md` if needed.
4. Plan next quarter’s experiments and projects.

### 6.3 Prioritization Model

COO uses a scoring model to rank issues:

| Factor | Weight | Source |
|--------|--------|--------|
| Financial impact | 30% | Business State |
| Risk of loss | 25% | Risk register + anomaly detection |
| Reversibility | 15% | Action metadata |
| Urgency | 15% | Deadlines, stockouts, campaign expiry |
| Strategic alignment | 10% | Obsidian strategy documents |
| Effort | 5% | Estimated action cost |

### 6.4 Communication Rules

- **Telegram:** brief, actionable, no raw data dumps.
- **Obsidian:** detailed, structured, permanent.
- **Escalations:** present context, options, recommendation, and confidence.
- **Silence:** no notification if nothing actionable changed.

### 6.5 Verification Loop

Every action executed by the system must be verified:

1. **Pre-action:** confirm state, policy, and expected outcome.
2. **Execution:** deterministic executor performs action and logs request/response.
3. **Post-action:** collector re-fetches relevant state to confirm effect.
4. **Close loop:** if effect matches expectation, mark complete; if not, flag incident.

### 6.6 Escalation Rules

Escalate to Gerard when:

- Confidence is below 80%.
- Financial impact exceeds a threshold (e.g., Rp 5M or 10% of daily budget).
- Action is irreversible.
- Policy is silent or ambiguous.
- Two agents conflict.
- Verification fails after execution.
- Security or compliance risk.

---

## 7. Decision Engine

### 7.1 Design Principle

Every important decision is a **proposal** until approved. The Decision Engine determines approval path based on confidence, impact, reversibility, and policy.

### 7.2 Decision Types

| Decision | Inputs | Decision Logic | Confidence | Approval | Verification |
|----------|--------|----------------|------------|----------|--------------|
| **Pricing** | COGS, competitor prices, stock level, margin target, demand | Inventory agent proposes; Finance validates margin; COO approves | High when data complete | Human for changes >X% or below floor | Check sales velocity and margin after 24h |
| **Inventory reorder** | Stock level, lead time, sales velocity, capital, supplier MOQ | Inventory agent computes reorder point and quantity | High when velocity stable | Human if PO > threshold | Confirm supplier acknowledgment and delivery |
| **Ad budget change** | ROAS, MER, stock level, cash, campaign performance | Growth agent proposes; Finance validates; COO approves | Medium-High | Auto-approve if within policy band; human if outside | Re-fetch campaign budget and metrics after 1h |
| **Campaign pause/resume** | ROAS, spend rate, stock, relevance | Growth agent proposes | High | Auto-approve within policy | Confirm campaign status and spend |
| **Refund/return** | Order value, reason, customer history, policy | Customer agent proposes | Medium | Human if > threshold or policy exception | Confirm platform refund status |
| **Supplier escalation** | Late shipments, quality issues, cost impact | Supplier agent proposes | Medium | Human | Confirm resolution or new supplier terms |
| **Shipping escalation** | Courier failure, SLA breach, customer complaint | Operations agent proposes | High | Auto-approve within policy | Confirm courier update or replacement |
| **Risk response** | Risk severity, probability, mitigation options | COO synthesizes | Variable | Human for high-impact; auto for low | Track risk status until closed |

### 7.3 Confidence Scoring

Confidence is computed deterministically from data quality, not guessed by AI:

| Confidence Level | Criteria |
|------------------|----------|
| **High (≥90%)** | Complete data, stable history, no anomalies, policy clear |
| **Medium (70-89%)** | Some data gaps, recent anomaly, or policy ambiguity |
| **Low (<70%)** | Missing data, conflicting signals, or novel situation |

Low-confidence decisions are always escalated.

### 7.4 Approval Requirements

| Action | Auto-approve | Human Required | Notes |
|--------|--------------|----------------|-------|
| Budget change ≤10% and within ROAS policy | ✅ | | With verification |
| Budget change >10% or ROAS outside policy | | ✅ | |
| Pause/resume campaign | ✅ | | If within policy |
| New campaign creation | | ✅ | |
| Price change ≤5% above floor | ✅ | | With verification |
| Price change >5% or below floor | | ✅ | |
| Refund within policy | ✅ | | If under threshold |
| Refund exception | | ✅ | |
| Supplier PO ≤ threshold | ✅ | | With acknowledgment |
| Supplier PO > threshold | | ✅ | |
| Any irreversible action | | ✅ | Always |

### 7.5 Verification After Execution

Every executed decision must be verified within a defined window:

| Decision | Verification Window | Success Criteria |
|----------|---------------------|------------------|
| Ad budget change | 1 hour | Budget updated, metrics stable |
| Price change | 24 hours | Sales velocity and margin acceptable |
| Campaign pause | 30 minutes | Status changed, no unintended spend |
| Refund | 2 hours | Platform confirms refund issued |
| Supplier PO | 24 hours | Supplier acknowledges with date |
| Shipping escalation | 4 hours | Courier updated or replacement arranged |

---

## 8. Observability

### 8.1 Health Dashboard

A single pane showing:

- Overall system health (green/yellow/red)
- Last successful data collection per connector
- API token expiry status
- Validation failures in last 24h
- Active incidents
- Pending human decisions
- Failed verifications
- Resource usage (disk, memory, DB size)

### 8.2 Automation Dashboard

- Cron schedule and last run status
- Job duration and success rate
- Data freshness by source
- Number of actions queued, executed, failed, escalated
- Agent activity log

### 8.3 Execution History

Immutable log of every action:

- `action_id`
- `proposed_by`
- `approved_by` (auto or human)
- `executor`
- `request_payload`
- `response_payload`
- `verification_result`
- `outcome`
- `timestamp`

Stored in Business DB (`audit_log` table) and mirrored to Obsidian `Decision Log`.

### 8.4 Structured Logs

All components emit structured JSON logs with:

- `timestamp` (UTC)
- `component`
- `level`
- `correlation_id`
- `event_type`
- `message`
- `context` (safe, no secrets)
- `duration_ms`

Logs are collected centrally and queryable.

### 8.5 Alert System

Alerts are tiered:

| Severity | Channel | Response Time | Examples |
|----------|---------|---------------|----------|
| P0 | Telegram + SMS | Immediate | System down, token expiry, API fraud alert, stockout |
| P1 | Telegram | 1 hour | ROAS crash, validation failure, verification failure |
| P2 | Telegram digest | 4 hours | Minor anomaly, missed schedule, data delay |
| P3 | Daily summary | Next day | Trends, recommendations, non-urgent flags |

### 8.6 Audit Trail

Every state change in Business DB is recorded:

- Who/what triggered it
- Previous and new value
- Timestamp
- Reason (if from decision, link to decision_id)

### 8.7 Error Recovery

| Failure Type | Recovery |
|--------------|----------|
| API transient error | Exponential backoff, retry 3-5 times, then alert |
| API auth failure | Attempt token refresh; if fails, alert P0 |
| Validation failure | Quarantine bad data, alert P1, do not propagate |
| Reconciliation mismatch | Flag P1, do not overwrite until resolved |
| Executor failure | Retry once, then dead-letter queue + alert |
| Verification failure | Open incident, escalate to human |
| DB corruption | Failover to latest backup, alert P0 |

### 8.8 Metrics & SLA Monitoring

| Metric | Target | Alert If |
|--------|--------|----------|
| Data freshness | < 1 hour for ads, < 6 hours for orders | > threshold |
| Automation success rate | > 99% | < 95% |
| Decision escalation rate | < 20% | > 30% (indicates AI over-cautious or data poor) |
| API error rate | < 1% | > 5% |
| Verification failure rate | < 1% | > 2% |
| Open action age | < 48 hours | > 72 hours |
| Incident resolution time | < 24 hours | > 48 hours |

---

## 9. Security

### 9.1 Secret Management

| Item | Storage | Access |
|------|---------|--------|
| API keys / partner IDs | Secret vault (e.g., macOS Keychain, 1Password CLI, or HashiCorp Vault) | Deterministic connectors only, never AI |
| OAuth tokens | Encrypted vault + short TTL | Auto-refresh by connectors |
| Database credentials | Secret vault | DB layer only |
| Telegram bot tokens | Secret vault | Notification service only |
| SSH / deploy keys | Secret vault | Deployment automation only |

**Rule:** AI agents and logs never see secrets. If a log must contain a credential, it is masked.

### 9.2 Access Control

| Role | Permissions |
|------|-------------|
| **System** | Read/write Business DB, execute approved actions, manage secrets via vault |
| **AI Agents** | Read Business State, read/write Obsidian within domain, propose actions, never execute |
| **COO Agent** | Read everything, approve within policy, escalate, never execute or see secrets |
| **Human (Gerard)** | Override everything, approve high-impact decisions, modify policy, rotate secrets |
| **Read-only dashboard** | View Business State and metrics, no execution |

### 9.3 Environment Separation

| Environment | Purpose | Data |
|-------------|---------|------|
| **Production** | Live business operations | Real API keys, real DB |
| **Staging** | Test changes with sandbox APIs | Sandbox credentials, anonymized DB snapshot |
| **Development** | Local experimentation | Mock data, no real secrets |
| **Obsidian** | Live knowledge base | Same vault, but with git/version history |

### 9.4 Backups

| Asset | Frequency | Retention | Method |
|-------|-----------|-----------|--------|
| Business DB | Hourly incremental, daily full | 30 days | Encrypted backup to cloud + local |
| Obsidian vault | Continuous (git) | Indefinite | Git repository with remote |
| Secrets | On change | Indefinite | Vault-native backup |
| Logs | Daily | 90 days | Compressed archive |
| Configuration | On change | Indefinite | Git |

### 9.5 Disaster Recovery

| Scenario | Recovery Time | Recovery Point | Procedure |
|----------|---------------|----------------|-----------|
| DB corruption | < 4 hours | Last hourly backup | Restore from backup, replay incremental logs |
| API key compromise | < 1 hour | N/A | Rotate keys, revoke tokens, audit logs |
| Server failure | < 2 hours | Last backup | Rebuild from config + backups |
| Obsidian corruption | < 30 minutes | Last git commit | Restore from git |
| Full environment loss | < 24 hours | Last daily backup | Rebuild infra from IaC + backups |

### 9.6 Audit Logging

Security-relevant events are logged:

- Secret access / rotation
- Login / authentication
- Policy changes
- High-impact decisions and approvals
- Privilege escalation
- Failed access attempts

---

## 10. Scalability

### 10.1 Platform Abstraction Layer

Every marketplace or ad platform is implemented as a **connector** with a standard interface:

```
Connector interface:
- authenticate()
- fetch_orders(since)
- fetch_products()
- fetch_inventory()
- fetch_ads_performance(since)
- fetch_campaigns()
- apply_action(action)
- validate_response(response)
```

Adding a new platform (e.g., Lazada) means:

1. Write a new connector implementing the interface.
2. Map platform-specific fields to canonical Business DB schema.
3. Add connector health check to observability.
4. Done. No changes to agents, dashboards, or COO logic.

### 10.2 Multi-Business Support

The Business DB schema is **tenant-aware**:

- `business_id` identifies each business.
- Each business has its own platform accounts, suppliers, products, and users.
- Agents can operate per-business or cross-business.
- COO can produce consolidated or per-business reports.

### 10.3 Data Growth Strategy

| Phase | Storage | Notes |
|-------|---------|-------|
| Now | SQLite or PostgreSQL on local/cloud | Sufficient for current volume |
| 1-2 years | Managed PostgreSQL | Better query performance, backups, concurrency |
| 2+ years | Data warehouse (BigQuery/ClickHouse) for analytics | Long-term trends, cohort analysis |

Raw data is never deleted; it is archived after 2 years for cost optimization.

### 10.4 Avoiding Future Rewrites

- **Canonical schema:** All platforms map to the same schema. Business logic is platform-agnostic.
- **Event-driven:** New capabilities subscribe to events rather than modifying existing code.
- **Plugin architecture:** Agents and connectors are pluggable.
- **API-first:** Internal services communicate via APIs, not file parsing.
- **Configuration over code:** Business rules live in config + policy, not code.

---

## 11. Migration Strategy

### 11.1 Guiding Rules

1. **Never big-bang.** Every phase leaves the business operational.
2. **Replace gradually.** New component runs alongside old until proven.
3. **Validate before switch.** Each new component must pass a comparison period.
4. **No unnecessary refactoring.** If a script works, wrap it; don’t rewrite it immediately.
5. **Preserve working paths.** Current Telegram notifications and Streamlit dashboard keep working.
6. **Clean up secrets first.** Before any new automation, secrets move to vault.

### 11.2 Phase 1: Foundation (Weeks 1-4)

| Task | Why | Output |
|------|-----|--------|
| Audit and centralize all secrets | Current system has hardcoded keys | Vault with all API keys/tokens |
| Stand up Business Database with canonical schema | Current DBs are inconsistent and fragile | PostgreSQL/SQLite with schema + migrations |
| Build schema validation and reconciliation layer | Prevents zero-data actions | Validation service |
| Fix Shopee order/income API integration | Financial engine is broken | Working order/income sync |
| Fix `daily_growth_run.sh` Python path | Currently broken | Working cron invocation |
| Add structured logging to all existing scripts | Observability | Centralized logs |

**Business remains operational** because existing scripts are only enhanced, not replaced.

### 11.3 Phase 2: Business State & Collectors (Weeks 5-8)

| Task | Why | Output |
|------|-----|--------|
| Build deterministic collectors for seller, ads, inventory, financials | Separates data fetching from business logic | Scheduled collectors |
| Build Business State builder | Creates canonical context | Materialized views + snapshot |
| Migrate SQLite data into canonical DB | Unifies truth | One business DB |
| Add health checks and alerts | Observability | Health dashboard |
| Build audit log | Traceability | audit_log table |

**Business remains operational** because old scripts can still read their old DBs while new DB is being validated.

### 11.4 Phase 3: Decision Engine & Policy (Weeks 9-12)

| Task | Why | Output |
|------|-----|--------|
| Define policy config (budget bands, price floors, approval thresholds) | Prevents dangerous auto-actions | Policy YAML/DB |
| Implement Decision Engine | Routes proposals to auto or human | Approval workflow |
| Wrap existing auto-optimizer as proposal generator | Stops direct budget changes | Proposals + approvals |
| Implement verification loop | Closes the action loop | Verification service |
| Build Decision Log in Obsidian | Institutional memory | Obsidian Decision Log |

**Business remains operational** because auto-optimizer is now a proposal system, not an executor.

### 11.5 Phase 4: Department Agents (Weeks 13-20)

| Task | Why | Output |
|------|-----|--------|
| Implement Finance Agent | Replaces manual financial reasoning | Profit/cash alerts |
| Implement Inventory Agent | Replaces manual stock checks | Reorder proposals |
| Implement Growth Agent | Replaces ad-hoc optimizer | Campaign proposals |
| Implement Operations Agent | Handles shipping/returns | Fulfillment alerts |
| Implement Customer Agent | Handles reviews/tickets | Response drafts |
| Implement Supplier Agent | Supplier management | Scorecards |
| Build Agent Registry in Obsidian | Documentation | Agent docs |

**Business remains operational** because agents are additive; they propose, they do not replace scripts.

### 11.6 Phase 5: COO Agent & Workflows (Weeks 21-28)

| Task | Why | Output |
|------|-----|--------|
| Implement morning/midday/evening workflows | Automates daily ops | Briefs, priorities, open actions |
| Implement prioritization model | Focus | Ranked priorities |
| Implement escalation rules | Safety | Escalation notifications |
| Build executive dashboard | Visibility | COO-level dashboard |
| Migrate Streamlit dashboard to new architecture | Better UX | New dashboard |

**Business remains operational** because old dashboard and notifications still run until new ones are validated.

### 11.7 Phase 6: Multi-Platform & Scale (Months 7-12)

| Task | Why | Output |
|------|-----|--------|
| Add Lazada connector | Scale | Lazada data in Business DB |
| Add Tokopedia connector | Scale | Tokopedia data |
| Add TikTok Shop connector | Scale | TikTok data |
| Add Meta/Google Ads connectors | Scale | Ad data consolidated |
| Implement multi-business tenant support | Future businesses | Tenant model |
| Add data warehouse | Analytics | Long-term analytics |

### 11.8 Dependency Graph

```
Phase 1 (Secrets + DB + Validation)
    │
    ├──► Phase 2 (Collectors + Business State)
    │       │
    │       ├──► Phase 3 (Decision Engine + Policy)
    │               │
    │               ├──► Phase 4 (Department Agents)
    │                       │
    │                       └──► Phase 5 (COO + Workflows)
    │                               │
    │                               └──► Phase 6 (Multi-platform)
    │
    └──► Parallel: Streamlit dashboard upgrade (Phase 4/5)
    │
    └──► Parallel: Obsidian structure migration (Phase 1-3)
```

---

## 12. Engineering Principles

These principles are non-negotiable. They override convenience.

| Principle | Meaning |
|-----------|---------|
| **The Business Database stores truth.** | Operational data is authoritative, versioned, and validated. Obsidian is memory, not a database. |
| **Obsidian stores knowledge.** | Decisions, SOPs, lessons, strategy, context. Machine-readable where agents need it. |
| **AI reasons. Code computes.** | AI proposes, interprets, prioritizes. Deterministic code executes, validates, and reconciles. |
| **Every automation is observable.** | If it runs, it is logged, measured, and its health is visible. |
| **Every important decision is explainable.** | Every decision links to data, policy, and reasoning. No black boxes. |
| **Every action is reversible unless explicitly approved.** | Default to safe. One-way doors require human sign-off. |
| **Every metric is validated.** | No number is trusted until it has been reconciled against a source of truth. |
| **Secrets never touch code or AI context.** | All credentials live in a vault and are injected at runtime. |
| **Machines propose. Humans approve high-impact actions.** | No autonomous spending, pricing, or irreversible changes without policy or approval. |
| **Fail safe, not fail operational.** | If validation fails, stop. Do not fall back to unverified data. |
| **Configuration over code.** | Business rules belong in policy/config, not hardcoded. |
| **Document first, automate second.** | A process must be defined in Obsidian before it is automated. |
| **No phantom context.** | Agents do not rely on long-term memory. They read current Business State and Obsidian. |
| **Prefer gradual replacement over rewrite.** | Old scripts are wrapped, then replaced, never deleted before the new path is proven. |

---

## 13. Critique of This Design

### 13.1 Weaknesses

1. **Complexity.** This is more moving parts than the current system. It requires disciplined maintenance.
2. **Latency.** Event-driven state updates introduce small delays. Real-time ad decisions may need synchronous paths.
3. **Cost.** A proper DB, backups, observability, and multi-platform connectors have ongoing costs.
4. **Over-engineering risk.** For a single Shopee shop, some abstractions may feel heavy. The defense is that they prevent rewrites later.
5. **Agent coordination overhead.** Multiple agents can conflict or produce noise without strong COO logic.
6. **Obsidian as machine-readable is fragile.** Free-form notes can drift. Strict templates and linting are required.

### 13.2 Trade-offs

| Trade-off | Chosen Side | Sacrificed |
|-----------|-------------|------------|
| Safety vs. speed | Safety | Some automation speed (e.g., budget changes require approval) |
| Abstraction vs. simplicity | Abstraction | More initial complexity |
| Centralized DB vs. local files | Centralized DB | Requires more infrastructure care |
| Proposals vs. auto-execution | Proposals | Less immediate responsiveness |
| Human-readable Obsidian vs. machine-readable | Hybrid | Both require disciplined formatting |
| Multi-platform ready vs. Shopee-only | Multi-platform ready | Some components are generalized before needed |

### 13.3 Open Questions

1. What is Gerard’s actual monthly transaction volume? This affects DB choice and retention.
2. What is the real business entity (sole prop, PT, etc.)? Needed for compliance and tax reporting.
3. Is there a budget for cloud infrastructure (Render, AWS, etc.)?
4. Does Gerard have sandbox accounts for Lazada/Tokopedia/TikTok for testing?
5. What is the tolerance for false-positive alerts? Determines sensitivity thresholds.
6. Should the dashboard be public-facing, internal-only, or mobile-first?
7. What is the exact approval appetite? E.g., “auto-approve budget changes up to 10%” may be too loose or too tight.
8. How should the system handle Shopee API deprecation/versioning?

### 13.4 Assumptions

1. Gerard wants to operate multiple platforms and possibly businesses in the future.
2. Gerard values reliability and explainability over raw automation speed.
3. Gerard will invest in maintaining the architecture, not just launching it.
4. Hermes (or equivalent) will continue to be available as the cognitive layer.
5. Shopee APIs will remain accessible and can be abstracted.
6. Gerard will provide real COGS, supplier data, and business rules.
7. A relational DB is sufficient for the next 2 years; warehouse is future.

### 13.5 Future Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Shopee API changes break connectors | High | High | Versioned connectors, abstraction layer, monitoring |
| Agent hallucinations lead to bad proposals | Medium | High | Deterministic validation, confidence scoring, human approval |
| Data quality issues corrupt Business State | Medium | High | Validation layer, reconciliation, anomaly detection |
| Secret leak | Medium | High | Vault, rotation, audit, no secrets in code |
| Over-reliance on AI reduces human judgment | Medium | High | Clear boundaries, escalation rules, periodic reviews |
| Scope creep turns ACOS into ERP | Medium | Medium | Strict boundaries, phase gates |
| Infrastructure cost exceeds value | Low | Medium | Start simple (SQLite → Postgres), measure ROI |
| Gerard’s attention/engagement drops | Medium | High | Morning/evening briefs designed to be low-friction, escalations only for important items |

---

## 14. Success Criteria

The architecture is approved when it satisfies:

- [ ] Clearly separates deterministic execution from AI reasoning.
- [ ] Defines a single source of truth for business data.
- [ ] Makes Hermes a COO within the system, not the system itself.
- [ ] Prevents dangerous autonomous actions without human approval.
- [ ] Is observable, auditable, and recoverable.
- [ ] Scales to multiple platforms and businesses without rewrite.
- [ ] Provides a realistic migration path that keeps the business operational.
- [ ] Documents what should and should not be delegated to AI.
- [ ] Defines a clear Obsidian knowledge architecture.
- [ ] Includes explicit critique of its own weaknesses and trade-offs.

---

## Next Step

This blueprint is **proposed, not implemented**. Awaiting Gerard’s approval, challenges, or adjustments before any code is written.
