"""Reporters for the knowledge layer.

Wires memory generation, summarization, writing, and indexing into a single
operational cycle. Produces full Markdown notes for Obsidian and concise text
for Telegram.
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from commerceos.config.settings import get_settings
from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.decision.dashboard import DecisionDashboard
from commerceos.events.dashboard import EventsDashboard
from commerceos.execution.dashboard import ExecutionDashboard
from commerceos.intelligence.dashboard import IntelligenceDashboard
from commerceos.knowledge.dashboard import KnowledgeDashboard
from commerceos.knowledge.index import KnowledgeIndex
from commerceos.knowledge.links import LinkBuilder
from commerceos.knowledge.memory import KnowledgeMemory
from commerceos.knowledge.models import KnowledgeNote
from commerceos.knowledge.retention import RetentionPolicy
from commerceos.knowledge.summarizer import MemorySummarizer
from commerceos.knowledge.vault import ObsidianVault
from commerceos.knowledge.writer import ObsidianWriter
from commerceos.monitoring.dashboard import MonitoringDashboard


STORE_ID = "store-ppm-001"


class KnowledgeReporter:
    """Generate daily/weekly/monthly/yearly notes and update the index."""

    def __init__(
        self,
        vault_dir: Optional[Path] = None,
        query_service: Optional[DashboardQueryService] = None,
        monitoring: Optional[MonitoringDashboard] = None,
        intelligence: Optional[IntelligenceDashboard] = None,
        decisions: Optional[DecisionDashboard] = None,
        executions: Optional[ExecutionDashboard] = None,
        events: Optional[EventsDashboard] = None,
        knowledge_dashboard: Optional[KnowledgeDashboard] = None,
        summarizer: Optional[MemorySummarizer] = None,
    ):
        settings = get_settings()
        self.vault_dir = vault_dir or settings.obsidian_vault_path
        self.vault = ObsidianVault(self.vault_dir)
        self.writer = ObsidianWriter(self.vault_dir)
        self.knowledge_dashboard = knowledge_dashboard
        self.index = KnowledgeIndex(
            self.vault_dir,
            repository=self.knowledge_dashboard.repository if self.knowledge_dashboard and self.knowledge_dashboard.repository else None,
        )

        self.memory = KnowledgeMemory(
            query_service=query_service or DashboardQueryService(),
            monitoring=monitoring or MonitoringDashboard.__new__(MonitoringDashboard),
            intelligence=intelligence or IntelligenceDashboard.__new__(IntelligenceDashboard),
            decisions=decisions or DecisionDashboard.__new__(DecisionDashboard),
            executions=executions or ExecutionDashboard.__new__(ExecutionDashboard),
            events=events or EventsDashboard.__new__(EventsDashboard),
            store_id=STORE_ID,
        )
        self.summarizer = summarizer or MemorySummarizer(store_id=STORE_ID)

    def generate_daily(self, target_date: Optional[date] = None, persist: bool = True) -> Dict[str, Any]:
        """Generate a daily COO brief and write to Obsidian."""
        target_date = target_date or date.today()
        memory = self.memory.generate_daily(target_date)
        body = self.summarizer.daily_body(memory)

        links = LinkBuilder(memory["note_id"])
        for decision in memory.get("decisions", {}).get("open", []):
            links.add_namespace("decision", decision.get("id", ""))
        for execution in memory.get("executions", []):
            links.add_namespace("execution", execution.get("id", ""))
        for alert in memory.get("alerts", []):
            links.add_namespace("alert", alert.get("id", ""))

        tags = ["daily", "business", "operations", "coo"]
        for insight in memory.get("insights", []):
            category = insight.get("category")
            if category and category.lower() not in tags:
                tags.append(category.lower())
        for a in memory.get("alerts", []):
            severity = a.get("severity")
            if severity and severity.lower() not in tags:
                tags.append(severity.lower())

        path = self.writer.write(
            note_type="daily",
            note_id=memory["note_id"],
            title=f"Daily COO Brief — {target_date.isoformat()}",
            body=body,
            note_date=target_date,
            tags=tags,
            links=links.build_note_ids(),
            source_domains=["intelligence", "monitoring", "decision", "execution", "events"],
        )

        if persist and self.knowledge_dashboard is not None:
            self._persist_metadata(memory["note_id"], "daily", target_date, path, tags, links.build_note_ids(), ["intelligence", "monitoring", "decision", "execution", "events"])
            self.index.generate()

        return {
            "note_id": memory["note_id"],
            "path": str(path),
            "memory": memory,
        }

    def generate_weekly(self, week_date: Optional[date] = None, persist: bool = True) -> Dict[str, Any]:
        """Generate a weekly summary from recent daily notes."""
        week_date = week_date or (date.today() - timedelta(days=date.today().weekday()))
        start = week_date
        end = start + timedelta(days=6)
        dailies = []
        if self.knowledge_dashboard is not None:
            dailies = self.knowledge_dashboard.get_business_timeline(start, end)

        weekly = self.summarizer.synthesize_weekly(dailies, week_date)
        path = self.writer.write(
            note_type="weekly",
            note_id=weekly["note_id"],
            title=weekly["title"],
            body=weekly["body"],
            note_date=week_date,
            tags=weekly["tags"],
            links=weekly["links"],
            source_domains=weekly["source_domains"],
        )
        if persist and self.knowledge_dashboard is not None:
            self._persist_metadata(weekly["note_id"], "weekly", week_date, path, weekly["tags"], weekly["links"], weekly["source_domains"])
            self.index.generate()
        return {"note_id": weekly["note_id"], "path": str(path)}

    def generate_monthly(self, month_date: Optional[date] = None, persist: bool = True) -> Dict[str, Any]:
        """Generate a monthly summary from recent weekly notes."""
        month_date = month_date or date.today().replace(day=1)
        if self.knowledge_dashboard is None:
            return {"note_id": None, "path": None}
        weeklies = self.knowledge_dashboard.get_recent_memory(days=60, note_type="weekly")
        monthly = self.summarizer.synthesize_monthly(weeklies, month_date)
        path = self.writer.write(
            note_type="monthly",
            note_id=monthly["note_id"],
            title=monthly["title"],
            body=monthly["body"],
            note_date=month_date,
            tags=monthly["tags"],
            links=monthly["links"],
            source_domains=monthly["source_domains"],
        )
        if persist:
            self._persist_metadata(monthly["note_id"], "monthly", month_date, path, monthly["tags"], monthly["links"], monthly["source_domains"])
            self.index.generate()
        return {"note_id": monthly["note_id"], "path": str(path)}

    def generate_yearly(self, year: Optional[int] = None, persist: bool = True) -> Dict[str, Any]:
        """Generate a yearly summary from recent monthly notes."""
        year = year or date.today().year
        if self.knowledge_dashboard is None:
            return {"note_id": None, "path": None}
        monthlies = self.knowledge_dashboard.get_recent_memory(days=400, note_type="monthly")
        yearly = self.summarizer.synthesize_yearly(monthlies, year)
        path = self.writer.write(
            note_type="yearly",
            note_id=yearly["note_id"],
            title=yearly["title"],
            body=yearly["body"],
            note_date=date(year, 1, 1),
            tags=yearly["tags"],
            links=yearly["links"],
            source_domains=yearly["source_domains"],
        )
        if persist:
            self._persist_metadata(yearly["note_id"], "yearly", date(year, 1, 1), path, yearly["tags"], yearly["links"], yearly["source_domains"])
            self.index.generate()
        return {"note_id": yearly["note_id"], "path": str(path)}

    def update_index(self) -> Path:
        """Regenerate the index from current metadata."""
        return self.index.generate()

    def apply_retention(self) -> Dict[str, List[str]]:
        """Archive old notes according to retention policy."""
        if self.knowledge_dashboard is None:
            return {"daily": [], "weekly": [], "monthly": []}
        policy = RetentionPolicy(self.knowledge_dashboard.repository, self.vault_dir)
        return {
            "daily": policy.archive_daily_notes(),
            "weekly": policy.archive_weekly_notes(),
            "monthly": policy.archive_monthly_notes(),
        }

    def _persist_metadata(
        self,
        note_id: str,
        note_type: str,
        note_date: date,
        path: Path,
        tags: List[str],
        links: List[str],
        source_domains: List[str],
    ) -> None:
        """Persist note metadata, updating an existing record if present."""
        repo = self.knowledge_dashboard.repository
        existing = repo.get_by_note_id(note_id)
        if existing is not None:
            existing.note_type = note_type
            existing.note_date = note_date
            existing.title = path.stem
            existing.path = str(path.relative_to(self.vault_dir))
            existing.tags = list(tags)
            existing.links = list(links)
            existing.source_domains = list(source_domains)
            existing.archived_at = None
            repo.save(existing)
            return

        note = KnowledgeNote(
            note_id=note_id,
            note_type=note_type,
            note_date=note_date,
            title=path.stem,
            path=str(path.relative_to(self.vault_dir)),
            tags=tags,
            links=links,
            source_domains=source_domains,
        )
        repo.save(note)


def concise_daily_summary(memory: Dict[str, Any]) -> str:
    """Return a concise Telegram-friendly summary from daily memory."""
    bs = memory.get("business_state", {})
    lines = [
        f"🧠 COO Brief — {memory.get('note_date', 'today')}",
        f"Health: {bs.get('overall_health', '—')}",
        f"Revenue: Rp {bs.get('revenue', 0):,.0f}",
        f"Profit: Rp {bs.get('gross_profit', 0):,.0f}",
        f"ROAS: {bs.get('roas', 0):.2f}x",
    ]
    alerts = memory.get("alerts", [])
    if alerts:
        lines.append(f"Alerts: {len(alerts)} open")
    decisions = memory.get("decisions", {}).get("open", [])
    if decisions:
        lines.append(f"Decisions: {len(decisions)} pending")
    return "\n".join(lines)


def concise_weekly_summary(weekly: Dict[str, Any]) -> str:
    """Return a concise Telegram-friendly weekly summary."""
    return f"📅 Weekly Review\n{weekly.get('title', '—')}\nSee Obsidian for full analysis."
