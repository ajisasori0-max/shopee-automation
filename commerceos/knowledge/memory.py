"""Operational memory collection for the knowledge layer.

Reads from existing CommerceOS service APIs only. No direct SQL, no marketplace
calls. Domain access is isolated behind small private methods so future domain
export services can replace them without changing the public interface.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.decision.dashboard import DecisionDashboard
from commerceos.events.dashboard import EventsDashboard
from commerceos.execution.dashboard import ExecutionDashboard
from commerceos.intelligence.dashboard import IntelligenceDashboard
from commerceos.monitoring.dashboard import MonitoringDashboard


STORE_ID = "store-ppm-001"


class KnowledgeMemory:
    """Collect operational signals from existing dashboards into structured memory."""

    def __init__(
        self,
        query_service: DashboardQueryService,
        monitoring: MonitoringDashboard,
        intelligence: IntelligenceDashboard,
        decisions: DecisionDashboard,
        executions: ExecutionDashboard,
        events: EventsDashboard,
        store_id: str = STORE_ID,
    ):
        self.query_service = query_service
        self.monitoring = monitoring
        self.intelligence = intelligence
        self.decisions = decisions
        self.executions = executions
        self.events = events
        self.store_id = store_id

    def generate_daily(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """Return structured daily memory for the target date."""
        target_date = target_date or date.today()
        start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
        end = start + timedelta(days=1, seconds=-1)

        return {
            "note_id": self._daily_note_id(target_date),
            "note_type": "daily",
            "note_date": target_date.isoformat(),
            "generated_at": utc_now().isoformat(),
            "business_state": self._collect_business_state(start, end),
            "kpis": self._collect_kpis(start, end),
            "events": self._collect_events(),
            "decisions": self._collect_decisions(),
            "executions": self._collect_executions(),
            "alerts": self._collect_alerts(),
            "insights": self._collect_insights(),
            "lessons": self._derive_lessons(),
            "follow_ups": self._derive_follow_ups(),
        }

    def _collect_business_state(self, start: datetime, end: datetime) -> Dict[str, Any]:
        try:
            state = self.query_service.get_commerce_state(self.store_id) or {}
        except Exception:
            state = {}

        try:
            pl = self.query_service.get_pl_summary(self.store_id, start, end) or {}
        except Exception:
            pl = {}

        try:
            ads = self.query_service.get_ad_performance_summary(self.store_id, start, end) or {}
        except Exception:
            ads = {}

        try:
            freshness = self.query_service.get_freshness(self.store_id) or {}
        except Exception:
            freshness = {}

        return {
            "store_id": self.store_id,
            "overall_health": self._safe_overall_health(),
            "revenue": pl.get("net_sales"),
            "gross_profit": pl.get("gross_profit"),
            "orders": pl.get("orders"),
            "roas": ads.get("roas"),
            "spend": ads.get("spend"),
            "data_quality_score": state.get("data_quality_score"),
            "freshness": freshness,
        }

    def _collect_kpis(self, start: datetime, end: datetime) -> List[Dict[str, Any]]:
        try:
            sales = self.query_service.get_daily_sales(self.store_id, start, end) or []
        except Exception:
            sales = []

        kpis = []
        for row in sales[-7:]:
            kpis.append({
                "date": row.get("date"),
                "revenue": row.get("revenue"),
                "orders": row.get("orders"),
            })
        return kpis

    def _collect_events(self) -> List[Dict[str, Any]]:
        try:
            events = self.events.get_recent_events(hours=24, limit=20) or []
        except Exception:
            events = []
        # Filter to business-relevant events: completed/failed workflows, dead letters.
        return [
            {
                "event_type": e.get("event_type"),
                "status": e.get("status"),
                "aggregate_type": e.get("aggregate_type"),
                "aggregate_id": e.get("aggregate_id"),
            }
            for e in events
            if e.get("status") in ("completed", "failed", "dead_lettered")
        ]

    def _collect_decisions(self) -> Dict[str, Any]:
        try:
            open_decisions = self.decisions.get_open_decisions(limit=20) or []
        except Exception:
            open_decisions = []
        try:
            summary = self.decisions.get_decision_summary() or {}
        except Exception:
            summary = {}
        return {
            "open": [
                {
                    "id": d.get("id"),
                    "title": d.get("title"),
                    "category": d.get("category"),
                    "severity": d.get("severity"),
                    "status": d.get("status"),
                    "recommended_action": d.get("recommended_action"),
                }
                for d in open_decisions
            ],
            "summary": summary.get("counts_by_status", {}),
        }

    def _collect_executions(self) -> List[Dict[str, Any]]:
        try:
            recent = self.executions.get_recent_executions(hours=24, limit=20) or []
        except Exception:
            recent = []
        return [
            {
                "id": e.get("id"),
                "action_type": e.get("action_type"),
                "status": e.get("status"),
                "decision_id": e.get("decision_id"),
                "completed_at": e.get("completed_at"),
            }
            for e in recent
        ]

    def _collect_alerts(self) -> List[Dict[str, Any]]:
        try:
            alerts = self.monitoring.get_open_alerts() or []
        except Exception:
            alerts = []
        return [
            {
                "id": a.get("id") if isinstance(a, dict) else a.id,
                "title": a.get("title") if isinstance(a, dict) else a.title,
                "severity": a.get("severity") if isinstance(a, dict) else a.severity,
                "category": a.get("category") if isinstance(a, dict) else a.category,
                "description": a.get("description") if isinstance(a, dict) else a.description,
            }
            for a in alerts
        ]

    def _collect_insights(self) -> List[Dict[str, Any]]:
        try:
            insights = self.intelligence.get_priority_insights(limit=10) or []
        except Exception:
            insights = []
        return [
            {
                "id": i.get("id"),
                "title": i.get("title"),
                "category": i.get("category"),
                "severity": i.get("severity"),
                "explanation": i.get("explanation"),
            }
            for i in insights
        ]

    def _derive_lessons(self) -> List[Dict[str, Any]]:
        # Placeholder for deterministic lesson extraction. Phase C v1 leaves this
        # empty unless a previous execution succeeded or failed today.
        return []

    def _derive_follow_ups(self) -> List[Dict[str, Any]]:
        # Placeholder for unresolved items carried forward.
        return []

    def _safe_overall_health(self) -> Optional[str]:
        try:
            snapshot = self.monitoring.get_health_snapshot()
            return snapshot.get("overall_status") if snapshot else None
        except Exception:
            return None

    def _daily_note_id(self, target_date: date) -> str:
        return f"kn-{target_date.isoformat()}"
