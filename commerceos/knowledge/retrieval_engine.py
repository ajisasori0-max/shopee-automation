"""WP3.3 — Memory Retrieval Engine v1.

Deterministic historical queries on top of `KnowledgeDashboard`. No embeddings,
no semantic search, no LLM.
"""
from __future__ import annotations


from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from commerceos.knowledge.dashboard import KnowledgeDashboard


class MemoryRetrievalEngine:
    """Richer deterministic historical queries for the COO agent."""

    def __init__(self, dashboard: KnowledgeDashboard):
        self.dashboard = dashboard

    def what_happened_before(
        self,
        event_date: date,
        window_days: int = 7,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Retrieve notes leading up to a date."""
        start = event_date - timedelta(days=window_days)
        end = event_date - timedelta(days=1)
        timeline = self.dashboard.get_business_timeline(start, end, categories=categories)
        return {
            "event_date": event_date.isoformat(),
            "window_days": window_days,
            "note_count": len(timeline),
            "notes": timeline,
        }

    def decision_history(
        self,
        query: Optional[str] = None,
        days: int = 90,
    ) -> List[Dict[str, Any]]:
        """Retrieve decision notes and related executions."""
        decisions = self.dashboard.recent_decisions(days=days, limit=100)
        if query:
            query_lower = query.lower()
            decisions = [d for d in decisions if query_lower in d.get("title", "").lower()]
        for d in decisions:
            related = self.dashboard.find_related_events(aggregate_id=d.get("note_id"), days=days)
            d["related_count"] = len(related)
        return decisions

    def project_history(
        self,
        project: str = "CommerceOS",
        days: int = 90,
    ) -> Dict[str, Any]:
        """Retrieve project notes, milestones, decisions, and lessons."""
        notes = self.dashboard.find_project_history(project, limit=100)
        if days:
            cutoff = (date.today() - timedelta(days=days)).isoformat()
            notes = [n for n in notes if n.get("note_date", "") >= cutoff]
        decisions = [n for n in notes if n.get("note_type") == "decision"]
        lessons = [n for n in notes if "lesson" in n.get("tags", [])]
        milestones = [n for n in notes if n.get("note_type") in ("project", "monthly", "yearly")]
        return {
            "project": project,
            "note_count": len(notes),
            "decisions": decisions,
            "lessons": lessons,
            "milestones": milestones,
        }

    def timeline_around_metric(
        self,
        metric_keyword: str,
        days: int = 14,
    ) -> Dict[str, Any]:
        """Retrieve notes mentioning a metric keyword around recent dates."""
        matches = self.dashboard.search_memory(metric_keyword, days=days)
        return {
            "metric": metric_keyword,
            "window_days": days,
            "note_count": len(matches),
            "notes": matches,
        }

    def memory_timeline(self, days: int = 30) -> List[Dict[str, Any]]:
        """Flat timeline of all recent active notes."""
        return self.dashboard.memory_timeline(days=days)
