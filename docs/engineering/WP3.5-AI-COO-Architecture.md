# WP3.5 — AI COO Architecture Notes

Status: architecture only. No implementation.

## Purpose

A future AI COO agent would consume the deterministic knowledge layer and business
state to reason, recommend, plan, and execute low-risk workflows autonomously.

## Inputs

- `KnowledgeDashboard` APIs (recent memory, timeline, related decisions, related events, project history, search).
- `MemoryRetrievalEngine` (what happened before X, decision history, metric timeline).
- `DashboardQueryService` (current business state, P&L, ads, freshness, orders).
- `MonitoringDashboard` (health, alerts).
- `IntelligenceDashboard` (insights, trends).
- `DecisionDashboard` (open decisions, summaries).
- `ExecutionDashboard` (execution queue, outcomes).

## Capabilities

1. **Reasoning** — explain why a metric changed using recent notes and decisions.
2. **Recommendations** — propose next actions based on historical outcomes.
3. **Planning** — generate execution plans for approved decisions.
4. **Autonomous workflows** — execute low-risk SOPs within policy (WP3.2 scope).

## Non-Goals

- Open-ended chat over notes.
- Replacing the deterministic knowledge layer with an LLM memory.
- Vector-based semantic search as the primary retrieval path.

## Architecture Sketch

```
User question
    ↓
Intent router (rule-based)
    ↓
Knowledge retrieval  OR  Business state  OR  Action proposal
    ↓
Reasoning layer (LLM or deterministic rules)
    ↓
Structured answer / recommendation / execution plan
```

## Safety Rules

- All marketplace mutations go through the existing `ExecutionEngine`.
- No autonomous execution of high-risk decisions without human approval.
- Every AI action is logged to `execution_audit`.
- AI reasoning cites specific note IDs and API results for traceability.

## Implementation Trigger

Implement when:
- WP3.2/3.3 have accumulated enough historical notes to answer real questions.
- At least one recurring decision is painful enough to automate.
- The user explicitly requests natural-language interaction with the COO layer.

No code changes required now.
