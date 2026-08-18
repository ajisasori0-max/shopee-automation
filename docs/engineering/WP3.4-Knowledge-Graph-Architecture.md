# WP3.4 — Knowledge Graph Architecture Notes

Status: architecture only. No implementation.

## Purpose

A future graph model would let the COO agent traverse cause-effect relationships
across business events, decisions, executions, and outcomes without scanning
Markdown files.

## Proposed Entities

- `Business` — revenue, profit, marketing, inventory domains.
- `Project` — CommerceOS, Shopee store operations.
- `Decision` — proposed/approved/rejected business decisions.
- `Experiment` — hypotheses, outcomes, conclusions.
- `Event` — workflow events, sync events, marketplace events.
- `Metric` — KPIs and trend snapshots.
- `Person` — human actors / approvers.
- `SOP` — standard operating procedures.

## Proposed Relationships

- `Decision → caused → Execution`
- `Execution → affected → Metric`
- `Execution → implemented → Decision`
- `Experiment → produced → Outcome`
- `Event → triggered → Decision`
- `Metric → belongs_to → Business`
- `Project → contains → Decision/Experiment/SOP`
- `Lesson → learned_from → Experiment/Decision/Event`

## Implementation Options

1. **Property graph DB** (Neo4j / NetworkX / Kuzu) if traversal becomes common.
2. **Relational graph** using `knowledge_relationships` table if queries are simple and local-first remains a priority.
3. **File-based graph** embedded in frontmatter `links` and `source_domains` if the graph is small and read-heavy.

## Recommendation

Defer graph storage until:
- The number of notes exceeds ~1,000.
- Retrieval engine cannot answer common questions in <3 API calls.
- A real use case requires multi-hop traversal (e.g., "Which decision caused the metric change that caused the alert?").

Until then, the deterministic `links` and `source_domains` in `knowledge_notes` provide a lightweight one-hop graph.

## Migration Path

The current `KnowledgeNote` model already has `links` and `source_domains`. A
g migrator can later convert those into explicit graph edges.

No schema changes required now.
