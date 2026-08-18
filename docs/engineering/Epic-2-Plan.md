# Epic 2 — Operational Intelligence & Autonomous Decision Support

**Date:** 2026-07-24  
**Status:** Planning  
**Dependency:** Epic 1 Operational Acceptance Test passes (24h observation ends ~2026-07-25 10:30 WIB)

---

## 1. Goal

Turn CommerceOS from a data platform into an operational co-pilot that:
1. Watches the business continuously.
2. Detects opportunities, risks, and anomalies.
3. Recommends or proposes actions.
4. Never acts without approval unless explicitly configured to do so.

---

## 2. Objectives

| ID | Objective | Success Criteria |
|----|-----------|------------------|
| E2.1 | Continuous monitoring layer | Health checks, freshness, data quality run automatically and alert on issues |
| E2.2 | Business intelligence engine | Daily/weekly reports generated from CommerceState with narrative summaries |
| E2.3 | Anomaly & risk detection | Detect revenue drops, ROAS changes, stockouts, ad spend spikes automatically |
| E2.4 | Decision engine v1 | Rule-based recommendations with approval workflow for ad budget, pricing, stock |
| E2.5 | Knowledge integration | Machine-generated reports and decisions written to Obsidian |
| E2.6 | Secret management | Move hardcoded partner keys/tokens out of scripts into `SecretManager` |

---

## 3. Architecture

### New modules

| Module | Path | Responsibility |
|--------|------|----------------|
| Monitoring | `commerceos/monitoring/` | Health checks, freshness, alerts |
| Intelligence | `commerceos/intelligence/` | Trends, anomalies, recommendations |
| Decision Engine | `commerceos/decisions/` | Rules, approval workflow, execution |
| Knowledge Writer | `commerceos/knowledge/` | Write reports/decisions to Obsidian |
| Secret Manager | `commerceos/platform/secrets/` | Centralized secret storage and access |

### Event-driven design

```
CommerceState.updated
    ├── monitoring → check freshness/quality → alert if bad
    ├── intelligence → detect anomalies → emit Opportunity / Risk
    ├── decision engine → evaluate rules → emit Recommendation
    ├── knowledge writer → append to Obsidian
    └── notification router → send to Telegram/email
```

---

## 4. Work Packages

### WP1: Secret Management (E2.6)
- Move partner keys, tokens, Telegram bot token into `SecretManager`.
- Backends: macOS Keychain first, file-based encrypted fallback.
- Remove all hardcoded secrets from active scripts.
- Add audit log for secret access.

### WP2: Monitoring Layer (E2.1)
- Replace ad-hoc debug scripts with `MonitoringService`.
- Check connectors, DB, KPI freshness, data quality score.
- P0/P1/P2 alert classification.
- Route alerts to Telegram.

### WP3: Intelligence Engine (E2.2, E2.3)
- Compute trends: revenue, ROAS, CTR, AOV vs previous period.
- Detect anomalies using simple thresholds + statistical methods.
- Generate daily and weekly briefs.

### WP4: Decision Engine v1 (E2.4)
- Rule DSL: `IF roas < 2.5 FOR 2 days THEN recommend reduce budget`.
- Approval workflow: proposals written to `pending_approval.json`, user approves via Telegram/UI.
- Safe execution: only after explicit approval.

### WP5: Knowledge Integration (E2.5)
- `KnowledgeWriter` service.
- Templates: daily report, weekly report, decision log, risk log.
- Write to Obsidian vault under agreed structure.

---

## 5. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Decision engine proposes unsafe actions | Medium | High | Dry-run by default; approval required; no autonomous writes |
| Alert fatigue | Medium | Medium | P0/P1 only initially; tune thresholds |
| Secret migration causes downtime | Low | High | Migrate one secret at a time; keep backups |
| Anomaly detection false positives | Medium | Medium | Start with conservative thresholds; human review |

---

## 6. Definition of Done for Epic 2

- [ ] No hardcoded secrets in active code.
- [ ] Automated monitoring runs every 4 hours without false alerts.
- [ ] Daily business brief generated and written to Obsidian.
- [ ] At least 3 anomaly/risk rules operational.
- [ ] Decision engine can propose and (after approval) execute ad budget changes.
- [ ] All actions are audited.
- [ ] User can view pending approvals in Telegram or dashboard.

---

## 7. First Task

**WP1: Secret Management.**

This is the prerequisite for everything else. We cannot safely build autonomous actions while secrets are scattered in scripts. Start here.
