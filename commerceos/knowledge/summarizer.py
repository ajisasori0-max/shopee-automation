"""Deterministic summarization for the knowledge layer.

Transforms structured daily memory into higher-level notes. No concatenation.
Causality, decisions, outcomes, recurring patterns, and lessons are preserved.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


class MemorySummarizer:
    """Synthesize daily/weekly/monthly/yearly memory from structured inputs."""

    def __init__(self, store_id: str = "store-ppm-001"):
        self.store_id = store_id

    # ------------------------------------------------------------------
    # Daily body generation
    # ------------------------------------------------------------------

    def daily_body(self, memory: Dict[str, Any]) -> str:
        """Return Markdown body for a daily memory note."""
        lines: List[str] = []
        bs = memory.get("business_state", {})

        lines.append("## Business State")
        lines.append("")
        lines.append(self._business_state_paragraph(bs))
        lines.append("")

        lines.append("## KPIs")
        lines.append("")
        kpis = memory.get("kpis", [])
        if kpis:
            lines.append("| Date | Revenue | Orders |")
            lines.append("|------|---------|--------|")
            for row in kpis:
                lines.append(
                    f"| {row.get('date', '—')} | {self._money(row.get('revenue'))} | {self._int(row.get('orders'))} |"
                )
        else:
            lines.append("No KPI data available for the period.")
        lines.append("")

        insights = memory.get("insights", [])
        if insights:
            lines.append("## Intelligence")
            lines.append("")
            for i in insights:
                lines.append(f"- **[{i.get('severity', 'info').upper()}] {i.get('title', 'Untitled')}**")
                lines.append(f"  {i.get('explanation', '')}")
            lines.append("")

        decisions = memory.get("decisions", {}).get("open", [])
        if decisions:
            lines.append("## Decisions")
            lines.append("")
            for d in decisions[:5]:
                lines.append(f"- **{d.get('severity', 'info').upper()}: {d.get('title', 'Untitled')}**")
                lines.append(f"  Status: {d.get('status', 'unknown')} | Recommended: {d.get('recommended_action', '—')}")
            lines.append("")

        executions = memory.get("executions", [])
        if executions:
            lines.append("## Executions")
            lines.append("")
            for e in executions:
                lines.append(f"- {e.get('status', 'unknown').upper()}: {e.get('action_type', '—')} ({e.get('id', '—')})")
            lines.append("")

        alerts = memory.get("alerts", [])
        if alerts:
            lines.append("## Alerts")
            lines.append("")
            for a in alerts:
                lines.append(f"- [{a.get('severity', 'info').upper()}] {a.get('title', 'Untitled')}: {a.get('description', '')}")
            lines.append("")

        events = memory.get("events", [])
        if events:
            lines.append("## Important Events")
            lines.append("")
            for e in events:
                lines.append(f"- {e.get('status', 'unknown').upper()}: {e.get('event_type', '—')} ({e.get('aggregate_type', '—')}:{e.get('aggregate_id', '—')})")
            lines.append("")

        lessons = memory.get("lessons", [])
        lines.append("## Lessons")
        lines.append("")
        if lessons:
            for lesson in lessons:
                lines.append(f"- {lesson.get('text', '')}")
        else:
            lines.append("No explicit lessons recorded today.")
        lines.append("")

        follow_ups = memory.get("follow_ups", [])
        lines.append("## Follow-ups")
        lines.append("")
        if follow_ups:
            for item in follow_ups:
                lines.append(f"- {item.get('text', '')}")
        else:
            lines.append("No outstanding follow-ups recorded.")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Weekly / Monthly / Yearly synthesis
    # ------------------------------------------------------------------

    def synthesize_weekly(self, daily_memories: List[Dict[str, Any]], week_date: Optional[date] = None) -> Dict[str, Any]:
        """Return structured weekly memory from a list of daily memories."""
        week_date = week_date or self._week_start(date.today())
        note_id = f"kn-{week_date.year}-W{week_date.isocalendar()[1]:02d}"
        title = f"Weekly Business Review — {week_date.isoformat()}"

        revenue_trend = self._revenue_trend(daily_memories)
        decisions_made = self._decisions_across(daily_memories)
        lessons = self._lessons_across(daily_memories)
        recurring_issues = self._recurring_issues(daily_memories)
        unresolved = self._unresolved_items(daily_memories)
        wins = self._wins(daily_memories)
        failures = self._failures(daily_memories)

        body = self._weekly_body(
            week_date,
            revenue_trend,
            wins,
            failures,
            decisions_made,
            lessons,
            recurring_issues,
            unresolved,
        )

        return {
            "note_id": note_id,
            "note_type": "weekly",
            "note_date": week_date.isoformat(),
            "title": title,
            "body": body,
            "tags": ["weekly", "review", "business", "decisions", "lessons"],
            "links": [m.get("note_id") for m in daily_memories if m.get("note_id")],
            "source_domains": ["intelligence", "monitoring", "decision", "execution", "events"],
        }

    def synthesize_monthly(self, weekly_memories: List[Dict[str, Any]], month_date: Optional[date] = None) -> Dict[str, Any]:
        """Return structured monthly memory from a list of weekly memories."""
        month_date = month_date or date.today().replace(day=1)
        note_id = f"kn-{month_date.year}-{month_date.month:02d}"
        title = f"Monthly Executive Review — {month_date.strftime('%B %Y')}"

        performance = self._monthly_performance(weekly_memories)
        strategic_changes = self._strategic_changes(weekly_memories)
        experiments = self._experiments(weekly_memories)
        recurring_patterns = self._recurring_patterns(weekly_memories)
        major_decisions = self._major_decisions(weekly_memories)
        kpis = self._kpi_trends(weekly_memories)

        body = self._monthly_body(
            month_date,
            performance,
            strategic_changes,
            experiments,
            kpis,
            recurring_patterns,
            major_decisions,
        )

        return {
            "note_id": note_id,
            "note_type": "monthly",
            "note_date": month_date.isoformat(),
            "title": title,
            "body": body,
            "tags": ["monthly", "executive", "strategy", "experiments"],
            "links": [m.get("note_id") for m in weekly_memories if m.get("note_id")],
            "source_domains": ["intelligence", "monitoring", "decision", "execution"],
        }

    def synthesize_yearly(self, monthly_memories: List[Dict[str, Any]], year: Optional[int] = None) -> Dict[str, Any]:
        """Return structured yearly memory from a list of monthly memories."""
        year = year or date.today().year
        note_id = f"kn-{year}"
        title = f"Yearly Executive Review — {year}"

        executive_summary = self._yearly_executive_summary(monthly_memories)
        milestones = self._yearly_milestones(monthly_memories)
        strategic_lessons = self._yearly_strategic_lessons(monthly_memories)
        evolution = self._yearly_evolution(monthly_memories)

        body = self._yearly_body(
            year,
            executive_summary,
            milestones,
            strategic_lessons,
            evolution,
        )

        return {
            "note_id": note_id,
            "note_type": "yearly",
            "note_date": f"{year}-01-01",
            "title": title,
            "body": body,
            "tags": ["yearly", "executive", "strategy", "milestones"],
            "links": [m.get("note_id") for m in monthly_memories if m.get("note_id")],
            "source_domains": ["intelligence", "decision", "execution"],
        }

    # ------------------------------------------------------------------
    # Body generators for higher-level notes
    # ------------------------------------------------------------------

    def _weekly_body(
        self,
        week_date: date,
        revenue_trend: str,
        wins: List[str],
        failures: List[str],
        decisions: List[Dict[str, Any]],
        lessons: List[str],
        recurring_issues: List[str],
        unresolved: List[str],
    ) -> str:
        lines = [f"## Business Summary\n\n{revenue_trend}\n"]

        lines.append("## Wins")
        lines.append("")
        if wins:
            for w in wins:
                lines.append(f"- {w}")
        else:
            lines.append("No significant wins recorded this week.")
        lines.append("")

        lines.append("## Failures")
        lines.append("")
        if failures:
            for f in failures:
                lines.append(f"- {f}")
        else:
            lines.append("No major failures recorded this week.")
        lines.append("")

        lines.append("## Trends")
        lines.append("")
        lines.append(self._weekly_trend_paragraph(revenue_trend))
        lines.append("")

        lines.append("## Decisions Made")
        lines.append("")
        if decisions:
            for d in decisions:
                lines.append(f"- {d.get('title', 'Untitled')} ({d.get('status', 'unknown')})")
        else:
            lines.append("No decisions were made this week.")
        lines.append("")

        lines.append("## Lessons Learned")
        lines.append("")
        if lessons:
            for lesson in lessons:
                lines.append(f"- {lesson}")
        else:
            lines.append("No explicit lessons recorded this week.")
        lines.append("")

        lines.append("## Recurring Issues")
        lines.append("")
        if recurring_issues:
            for issue in recurring_issues:
                lines.append(f"- {issue}")
        else:
            lines.append("No recurring issues detected.")
        lines.append("")

        lines.append("## Unresolved Items")
        lines.append("")
        if unresolved:
            for item in unresolved:
                lines.append(f"- {item}")
        else:
            lines.append("No unresolved items carried forward.")
        lines.append("")

        return "\n".join(lines)

    def _monthly_body(
        self,
        month_date: date,
        performance: str,
        strategic_changes: List[str],
        experiments: List[Dict[str, Any]],
        kpis: str,
        recurring_patterns: List[str],
        major_decisions: List[Dict[str, Any]],
    ) -> str:
        lines = [
            f"## Performance Review\n\n{performance}\n",
            f"## KPI Trends\n\n{kpis}\n",
        ]

        lines.append("## Strategic Changes")
        lines.append("")
        if strategic_changes:
            for c in strategic_changes:
                lines.append(f"- {c}")
        else:
            lines.append("No strategic changes recorded this month.")
        lines.append("")

        lines.append("## Experiments")
        lines.append("")
        if experiments:
            for e in experiments:
                lines.append(f"- {e.get('title', 'Untitled')}: {e.get('outcome', 'No outcome recorded')}")
        else:
            lines.append("No experiments concluded this month.")
        lines.append("")

        lines.append("## Recurring Patterns")
        lines.append("")
        if recurring_patterns:
            for p in recurring_patterns:
                lines.append(f"- {p}")
        else:
            lines.append("No recurring patterns detected.")
        lines.append("")

        lines.append("## Major Decisions")
        lines.append("")
        if major_decisions:
            for d in major_decisions:
                lines.append(f"- {d.get('title', 'Untitled')} ({d.get('status', 'unknown')})")
        else:
            lines.append("No major decisions recorded this month.")
        lines.append("")

        return "\n".join(lines)

    def _yearly_body(
        self,
        year: int,
        executive_summary: str,
        milestones: List[str],
        strategic_lessons: List[str],
        evolution: List[str],
    ) -> str:
        lines = [
            f"## Executive Summary\n\n{executive_summary}\n",
            "## Major Milestones",
            "",
        ]
        if milestones:
            for m in milestones:
                lines.append(f"- {m}")
        else:
            lines.append("No major milestones recorded this year.")
        lines.append("")

        lines.append("## Strategic Lessons")
        lines.append("")
        if strategic_lessons:
            for lesson in strategic_lessons:
                lines.append(f"- {lesson}")
        else:
            lines.append("No strategic lessons recorded this year.")
        lines.append("")

        lines.append("## Business Evolution")
        lines.append("")
        if evolution:
            for e in evolution:
                lines.append(f"- {e}")
        else:
            lines.append("No documented business evolution this year.")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Synthesis helpers
    # ------------------------------------------------------------------

    def _business_state_paragraph(self, bs: Dict[str, Any]) -> str:
        parts = []
        health = bs.get("overall_health")
        if health:
            parts.append(f"Overall system health: {health}.")
        revenue = bs.get("revenue")
        if revenue is not None:
            parts.append(f"Revenue was {self._money(revenue)}.")
        profit = bs.get("gross_profit")
        if profit is not None:
            parts.append(f"Gross profit was {self._money(profit)}.")
        orders = bs.get("orders")
        if orders is not None:
            parts.append(f"Orders: {self._int(orders)}.")
        roas = bs.get("roas")
        if roas is not None:
            parts.append(f"ROAS: {roas:.2f}x.")
        spend = bs.get("spend")
        if spend is not None:
            parts.append(f"Ad spend: {self._money(spend)}.")
        score = bs.get("data_quality_score")
        if score is not None:
            parts.append(f"Data quality score: {score:.0%}.")
        if not parts:
            return "No business state data available for the period."
        return " ".join(parts)

    def _weekly_trend_paragraph(self, revenue_trend: str) -> str:
        return revenue_trend or "No trend data available."

    def _revenue_trend(self, dailies: List[Dict[str, Any]]) -> str:
        revenues = []
        for d in dailies:
            bs = d.get("business_state", {})
            rev = bs.get("revenue")
            if rev is not None:
                revenues.append(rev)
        if not revenues:
            return "Revenue data unavailable for the week."
        if len(revenues) < 2:
            return f"Recorded revenue for the period was {self._money(revenues[0])}."
        first, last = revenues[0], revenues[-1]
        if last > first:
            direction = "increased"
        elif last < first:
            direction = "decreased"
        else:
            direction = "remained flat"
        pct = 0 if first == 0 else ((last - first) / first) * 100
        return f"Revenue {direction} from {self._money(first)} to {self._money(last)} ({pct:+.1f}%)."

    def _decisions_across(self, dailies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        decisions = []
        for d in dailies:
            for item in d.get("decisions", {}).get("open", []):
                key = item.get("id") or item.get("title")
                if key and key not in seen:
                    seen.add(key)
                    decisions.append(item)
        return decisions

    def _lessons_across(self, dailies: List[Dict[str, Any]]) -> List[str]:
        lessons = []
        for d in dailies:
            for lesson in d.get("lessons", []):
                text = lesson.get("text")
                if text and text not in lessons:
                    lessons.append(text)
        return lessons

    def _recurring_issues(self, dailies: List[Dict[str, Any]]) -> List[str]:
        counts: Dict[str, int] = {}
        for d in dailies:
            for a in d.get("alerts", []):
                title = a.get("title") or a.get("category") or "unknown"
                counts[title] = counts.get(title, 0) + 1
        return [issue for issue, count in counts.items() if count >= 2]

    def _unresolved_items(self, dailies: List[Dict[str, Any]]) -> List[str]:
        items = []
        for d in dailies:
            for item in d.get("follow_ups", []):
                text = item.get("text")
                if text and text not in items:
                    items.append(text)
        return items

    def _wins(self, dailies: List[Dict[str, Any]]) -> List[str]:
        wins = []
        for d in dailies:
            for e in d.get("events", []):
                if e.get("status") == "completed":
                    text = f"{e.get('event_type', 'Workflow')} completed"
                    if text not in wins:
                        wins.append(text)
            # Treat revenue increase as a win if there is prior comparison.
            bs = d.get("business_state", {})
            if bs.get("overall_health") == "healthy":
                text = "System health remained healthy"
                if text not in wins:
                    wins.append(text)
        return wins

    def _failures(self, dailies: List[Dict[str, Any]]) -> List[str]:
        failures = []
        for d in dailies:
            for e in d.get("events", []):
                if e.get("status") == "failed":
                    text = f"{e.get('event_type', 'Workflow')} failed"
                    if text not in failures:
                        failures.append(text)
            for e in d.get("executions", []):
                if e.get("status") in ("failed", "partial"):
                    text = f"Execution {e.get('action_type', '—')} failed"
                    if text not in failures:
                        failures.append(text)
        return failures

    def _monthly_performance(self, weeklies: List[Dict[str, Any]]) -> str:
        summaries = []
        for w in weeklies:
            body = w.get("body", "")
            for line in body.splitlines():
                if line.startswith("Revenue"):
                    summaries.append(line)
        if not summaries:
            return "Performance data unavailable for the month."
        return " ".join(summaries)

    def _kpi_trends(self, weeklies: List[Dict[str, Any]]) -> str:
        return "See weekly summaries for detailed KPI movement."

    def _strategic_changes(self, weeklies: List[Dict[str, Any]]) -> List[str]:
        changes = []
        for w in weeklies:
            for d in w.get("decisions_made", []) if "decisions_made" in w else []:
                title = d.get("title")
                if title and title not in changes:
                    changes.append(title)
        return changes

    def _experiments(self, weeklies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # v1: no experiment tracking yet; return empty.
        return []

    def _recurring_patterns(self, weeklies: List[Dict[str, Any]]) -> List[str]:
        patterns = []
        for w in weeklies:
            for issue in w.get("recurring_issues", []):
                if issue not in patterns:
                    patterns.append(issue)
        return patterns

    def _major_decisions(self, weeklies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        decisions = []
        seen = set()
        for w in weeklies:
            for d in w.get("decisions_made", []) if "decisions_made" in w else []:
                key = d.get("id") or d.get("title")
                if key and key not in seen:
                    seen.add(key)
                    decisions.append(d)
        return decisions

    def _yearly_executive_summary(self, monthlies: List[Dict[str, Any]]) -> str:
        if not monthlies:
            return "No monthly data available for the year."
        return f"Yearly review synthesized from {len(monthlies)} monthly reviews."

    def _yearly_milestones(self, monthlies: List[Dict[str, Any]]) -> List[str]:
        milestones = []
        for m in monthlies:
            for d in m.get("major_decisions", []) if "major_decisions" in m else []:
                title = d.get("title")
                if title and title not in milestones:
                    milestones.append(title)
        return milestones

    def _yearly_strategic_lessons(self, monthlies: List[Dict[str, Any]]) -> List[str]:
        lessons = []
        for m in monthlies:
            body = m.get("body", "")
            in_section = False
            for line in body.splitlines():
                if line.startswith("## Strategic Lessons"):
                    in_section = True
                    continue
                if in_section:
                    if line.startswith("##"):
                        break
                    if line.startswith("- "):
                        text = line[2:].strip()
                        if text and text not in lessons:
                            lessons.append(text)
        return lessons

    def _yearly_evolution(self, monthlies: List[Dict[str, Any]]) -> List[str]:
        evolutions = []
        for m in monthlies:
            body = m.get("body", "")
            in_section = False
            for line in body.splitlines():
                if line.startswith("## Business Evolution"):
                    in_section = True
                    continue
                if in_section:
                    if line.startswith("##"):
                        break
                    if line.startswith("- "):
                        text = line[2:].strip()
                        if text and text not in evolutions:
                            evolutions.append(text)
        return evolutions

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _week_start(self, d: date) -> date:
        return d - timedelta(days=d.weekday())

    def _money(self, value: Optional[float]) -> str:
        if value is None:
            return "—"
        return f"Rp {value:,.0f}"

    def _int(self, value: Optional[int]) -> str:
        if value is None:
            return "—"
        return f"{value:,}"
