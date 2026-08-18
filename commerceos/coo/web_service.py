"""Web COO Dashboard service orchestration layer.

Provides a single, cached, read-only interface for all Web COO pages.
Pages never touch SQLAlchemy models or marketplace APIs directly.

Responsibilities:
- Open one canonical database session per page load and close it.
- Construct all existing dashboard services and expose a unified query surface.
- Degrade gracefully when a subsystem is missing or empty.
"""
from commerceos.shared.value_objects.primitives import utc_now

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.analytics.dashboard import AnalyticsDashboard
from commerceos.config.settings import get_settings
from commerceos.coo.dashboard import COODashboard
from commerceos.coo.interface import COOInterface
from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.decision.approval import ApprovalWorkflow
from commerceos.decision.dashboard import DecisionDashboard
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.events.dashboard import EventsDashboard
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork
from commerceos.execution.dashboard import ExecutionDashboard
from commerceos.execution.sqlalchemy_repositories import SQLAlchemyExecutionUnitOfWork
from commerceos.intelligence.dashboard import IntelligenceDashboard
from commerceos.intelligence.sqlalchemy_repositories import SQLAlchemyIntelligenceUnitOfWork
from commerceos.jobs.factory import register_default_jobs
from commerceos.jobs.health import JobHealthReporter
from commerceos.jobs.runner import JobRunner
from commerceos.knowledge.dashboard import KnowledgeDashboard
from commerceos.knowledge.sqlalchemy_repositories import SQLAlchemyKnowledgeUnitOfWork
from commerceos.monitoring.dashboard import MonitoringDashboard
from commerceos.monitoring.sqlalchemy_repositories import SQLAlchemyMonitoringUnitOfWork
from commerceos.policy.autonomous_execution import AutonomousExecutionService
from commerceos.policy.engine import DEFAULT_POLICIES, PolicyEngine
from commerceos.policy.experiment_engine import ExperimentEngine
from commerceos.sop.engine import DEFAULT_SOP_DEFINITIONS, SOPDefinition
from commerceos.sop.sqlalchemy_repositories import SQLAlchemySOPUnitOfWork


STORE_ID = "store-ppm-001"


def _safe(value: Any, default: Any) -> Any:
    return value if value is not None else default


@dataclass
class CommandCenterData:
    """Everything the Command Center landing page needs in one bundle."""

    generated_at: str
    overall_status: str
    business_today: Dict[str, Any] = field(default_factory=dict)
    health: Dict[str, Any] = field(default_factory=dict)
    attention: Dict[str, Any] = field(default_factory=dict)
    coo_brief: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "business_today": self.business_today,
            "health": self.health,
            "attention": self.attention,
            "coo_brief": self.coo_brief,
            "errors": self.errors,
        }


class WebCOODashboardService:
    """Single orchestration service for all Web COO dashboard pages."""

    def __init__(self, session: Session, store_id: str = STORE_ID):
        self.session = session
        self.store_id = store_id
        self.settings = get_settings()
        self.now = utc_now()
        self.today_start = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        self.today_end = self.today_start + timedelta(days=1, seconds=-1)

        # Existing query / dashboard services
        self.query_service = DashboardQueryService(session=session)
        self.monitoring_dashboard = MonitoringDashboard(SQLAlchemyMonitoringUnitOfWork(session))
        self.intelligence_dashboard = IntelligenceDashboard(SQLAlchemyIntelligenceUnitOfWork(session))
        self.decision_dashboard = DecisionDashboard(SQLAlchemyDecisionUnitOfWork(session))
        self.execution_dashboard = ExecutionDashboard(SQLAlchemyExecutionUnitOfWork(session))
        self.events_dashboard = EventsDashboard(SQLAlchemyEventsUnitOfWork(session))
        self.knowledge_dashboard = KnowledgeDashboard(
            SQLAlchemyKnowledgeUnitOfWork(session).notes(),
            vault_dir=self.settings.obsidian_vault_path,
        )
        self.coo_dashboard = COODashboard(session, self.settings)
        self.analytics_dashboard = AnalyticsDashboard(session, store_id)

        # Operational helpers
        self.approval_workflow = ApprovalWorkflow(SQLAlchemyDecisionUnitOfWork(session))
        self.autonomous_service = AutonomousExecutionService(session)
        self.experiment_engine = ExperimentEngine(session)
        self.job_registry = register_default_jobs(session=session, settings=self.settings)
        self.job_runner = JobRunner(session, registry=self.job_registry)
        self.job_health = JobHealthReporter(session, registry=self.job_registry)
        self.sop_uow = SQLAlchemySOPUnitOfWork(session)

    # ------------------------------------------------------------------
    # Command Center
    # ------------------------------------------------------------------

    def get_command_center(self) -> CommandCenterData:
        errors: List[str] = []

        try:
            snapshot = self.monitoring_dashboard.get_health_snapshot() or {}
            overall = snapshot.get("overall_status", "unknown")
        except Exception as exc:
            snapshot = {}
            overall = "unknown"
            errors.append(f"Health snapshot: {exc}")

        try:
            commerce_state = self.query_service.get_commerce_state(self.store_id) or {}
        except Exception as exc:
            commerce_state = {}
            errors.append(f"Commerce state: {exc}")

        try:
            pl_today = self.query_service.get_pl_summary(self.store_id, self.today_start, self.today_end) or {}
        except Exception as exc:
            pl_today = {}
            errors.append(f"P&L today: {exc}")

        try:
            ads_today = self.query_service.get_ad_performance_summary(self.store_id, self.today_start, self.today_end) or {}
        except Exception as exc:
            ads_today = {}
            errors.append(f"Ads today: {exc}")

        try:
            orders_today = self.query_service.get_order_list(self.store_id, self.today_start, self.today_end) or []
        except Exception as exc:
            orders_today = []
            errors.append(f"Orders today: {exc}")

        try:
            freshness = self.query_service.get_freshness(self.store_id) or {}
        except Exception as exc:
            freshness = {}
            errors.append(f"Freshness: {exc}")

        try:
            open_alerts = self.monitoring_dashboard.get_open_alerts() or []
        except Exception as exc:
            open_alerts = []
            errors.append(f"Open alerts: {exc}")

        try:
            system_health = self.monitoring_dashboard.get_system_health(since_hours=24) or {"components": []}
        except Exception as exc:
            system_health = {"components": []}
            errors.append(f"System health: {exc}")

        try:
            priority_decisions = self.decision_dashboard.get_high_priority(limit=5) or []
        except Exception as exc:
            priority_decisions = []
            errors.append(f"Priority decisions: {exc}")

        try:
            priority_insights = self.intelligence_dashboard.get_priority_insights(limit=5) or []
        except Exception as exc:
            priority_insights = []
            errors.append(f"Priority insights: {exc}")

        try:
            inventory = self.analytics_dashboard.inventory_recommendations() or {}
            at_risk = [r for r in inventory.get("recommendations", []) if r.get("coverage_days", 999) < 14]
        except Exception as exc:
            inventory = {}
            at_risk = []
            errors.append(f"Inventory intelligence: {exc}")

        try:
            running_executions = self.execution_dashboard.get_running(limit=10) or []
        except Exception as exc:
            running_executions = []
            errors.append(f"Running executions: {exc}")

        try:
            running_workflows = self.events_dashboard.get_running_workflows(limit=10) or []
        except Exception as exc:
            running_workflows = []
            errors.append(f"Running workflows: {exc}")

        try:
            failed_jobs = self.job_health.recent_failures(hours=24)
        except Exception as exc:
            failed_jobs = []
            errors.append(f"Job failures: {exc}")

        try:
            decision_summary = self.decision_dashboard.get_decision_summary() or {}
        except Exception as exc:
            decision_summary = {}
            errors.append(f"Decision summary: {exc}")

        try:
            coo_brief = self.coo_dashboard.what_matters_today()
        except Exception as exc:
            coo_brief = {
                "answer": "COO brief unavailable.",
                "intent": "error",
                "warnings": [str(exc)],
            }
            errors.append(f"COO brief: {exc}")

        latest_sync = "—"
        if freshness:
            latest_sync = max(
                (info["last_sync"][:19] for info in freshness.values() if info.get("last_sync")),
                default="—",
            )

        stale_entities = [
            entity for entity, info in freshness.items() if not info.get("is_fresh")
        ]

        business_today = {
            "revenue": pl_today.get("net_sales", 0),
            "gross_profit": pl_today.get("gross_profit", 0),
            "orders": len(orders_today),
            "ad_spend": ads_today.get("total_spend", 0),
            "roas": ads_today.get("roas", 0),
            "aov": pl_today.get("aov", 0),
            "data_quality_score": commerce_state.get("data_quality_score", 0),
            "temporary": pl_today.get("temporary", True) or ads_today.get("temporary", True),
        }

        health = {
            "overall_status": overall,
            "snapshot_generated_at": snapshot.get("generated_at", "—"),
            "open_alerts_count": len(open_alerts),
            "stale_entities": stale_entities,
            "system_components_count": len(system_health.get("components", [])),
            "latest_sync": latest_sync,
            "failed_jobs_count": len(failed_jobs),
        }

        attention = {
            "critical_alerts": [a for a in open_alerts if a.get("severity") == "critical"],
            "high_alerts": [a for a in open_alerts if a.get("severity") == "high"],
            "priority_decisions": priority_decisions,
            "priority_insights": priority_insights,
            "low_stock_skus": at_risk[:10],
            "running_executions": running_executions,
            "running_workflows": running_workflows,
            "failed_jobs": failed_jobs,
            "open_decisions_count": decision_summary.get("counts_by_status", {}).get("proposed", 0),
        }

        return CommandCenterData(
            generated_at=self.now.isoformat(),
            overall_status=overall,
            business_today=business_today,
            health=health,
            attention=attention,
            coo_brief=coo_brief,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Intelligence
    # ------------------------------------------------------------------

    def get_intelligence(self, days: int = 7) -> Dict[str, Any]:
        errors: List[str] = []
        end = self.now
        start = end - timedelta(days=days)

        try:
            insights = self.intelligence_dashboard.get_priority_insights(limit=20) or []
        except Exception as exc:
            insights = []
            errors.append(f"Insights: {exc}")

        try:
            trends = self.intelligence_dashboard.get_trend_summary() or []
        except Exception as exc:
            trends = []
            errors.append(f"Trends: {exc}")

        try:
            business_summary = self.intelligence_dashboard.get_business_summary() or {}
        except Exception as exc:
            business_summary = {}
            errors.append(f"Business summary: {exc}")

        try:
            pl = self.query_service.get_pl_summary(self.store_id, start, end) or {}
        except Exception as exc:
            pl = {}
            errors.append(f"P&L: {exc}")

        try:
            ads = self.query_service.get_ad_performance_summary(self.store_id, start, end) or {}
        except Exception as exc:
            ads = {}
            errors.append(f"Ads: {exc}")

        try:
            daily_sales = self.query_service.get_daily_sales(self.store_id, start, end) or []
        except Exception as exc:
            daily_sales = []
            errors.append(f"Daily sales: {exc}")

        try:
            analytics_summary = self.analytics_dashboard.summary(days=days)
        except Exception as exc:
            analytics_summary = {}
            errors.append(f"Analytics summary: {exc}")

        try:
            what_changed = self.coo_dashboard.what_changed_this_week()
        except Exception as exc:
            what_changed = {}
            errors.append(f"What changed: {exc}")

        return {
            "generated_at": self.now.isoformat(),
            "days": days,
            "business_summary": business_summary,
            "insights": insights,
            "trends": trends,
            "pl": pl,
            "ads": ads,
            "daily_sales": daily_sales,
            "analytics_summary": analytics_summary,
            "what_changed": what_changed,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def get_decisions(self, status: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            decisions = self.decision_dashboard.get_open_decisions(category=category, limit=50) or []
        except Exception as exc:
            decisions = []
            errors.append(f"Decisions: {exc}")

        try:
            summary = self.decision_dashboard.get_decision_summary() or {}
        except Exception as exc:
            summary = {}
            errors.append(f"Decision summary: {exc}")

        return {
            "generated_at": self.now.isoformat(),
            "status_filter": status or "open",
            "category_filter": category,
            "decisions": decisions,
            "summary": summary,
            "errors": errors,
        }

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        return self.decision_dashboard.get_decision(decision_id)

    def approve_decision(self, decision_id: str) -> Dict[str, Any]:
        try:
            self.approval_workflow.approve(decision_id, changed_by="web-coo", notes="Approved from Web COO Dashboard")
            return {"success": True, "decision_id": decision_id, "status": "approved"}
        except Exception as exc:
            return {"success": False, "decision_id": decision_id, "error": str(exc)}

    def reject_decision(self, decision_id: str) -> Dict[str, Any]:
        try:
            self.approval_workflow.reject(decision_id, changed_by="web-coo", notes="Rejected from Web COO Dashboard")
            return {"success": True, "decision_id": decision_id, "status": "rejected"}
        except Exception as exc:
            return {"success": False, "decision_id": decision_id, "error": str(exc)}

    # ------------------------------------------------------------------
    # Executions
    # ------------------------------------------------------------------

    def get_executions(self) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            queue = self.execution_dashboard.get_execution_queue(limit=50) or []
        except Exception as exc:
            queue = []
            errors.append(f"Queue: {exc}")

        try:
            running = self.execution_dashboard.get_running(limit=50) or []
        except Exception as exc:
            running = []
            errors.append(f"Running: {exc}")

        try:
            recent = self.execution_dashboard.get_recent_executions(hours=24, limit=50) or []
        except Exception as exc:
            recent = []
            errors.append(f"Recent: {exc}")

        try:
            summary = self.execution_dashboard.get_execution_summary() or {}
        except Exception as exc:
            summary = {}
            errors.append(f"Summary: {exc}")

        return {
            "generated_at": self.now.isoformat(),
            "queue": queue,
            "running": running,
            "recent": recent,
            "summary": summary,
            "errors": errors,
        }

    def get_execution(self, plan_id: str) -> Optional[Dict[str, Any]]:
        return self.execution_dashboard.get_execution(plan_id)

    # ------------------------------------------------------------------
    # Knowledge
    # ------------------------------------------------------------------

    def get_knowledge(self, days: int = 30) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            timeline = self.knowledge_dashboard.memory_timeline(days=days) or []
        except Exception as exc:
            timeline = []
            errors.append(f"Timeline: {exc}")

        try:
            recent_lessons = self.knowledge_dashboard.recent_lessons(days=days, limit=20) or []
        except Exception as exc:
            recent_lessons = []
            errors.append(f"Lessons: {exc}")

        try:
            recent_decisions = self.knowledge_dashboard.recent_decisions(days=days, limit=20) or []
        except Exception as exc:
            recent_decisions = []
            errors.append(f"Decision notes: {exc}")

        try:
            latest_weekly = self.knowledge_dashboard.latest_summary("weekly")
            latest_daily = self.knowledge_dashboard.latest_summary("daily")
        except Exception as exc:
            latest_weekly = None
            latest_daily = None
            errors.append(f"Latest summaries: {exc}")

        return {
            "generated_at": self.now.isoformat(),
            "days": days,
            "timeline": timeline,
            "recent_lessons": recent_lessons,
            "recent_decisions": recent_decisions,
            "latest_weekly": latest_weekly,
            "latest_daily": latest_daily,
            "errors": errors,
        }

    def search_knowledge(self, query: str, days: int = 90) -> Dict[str, Any]:
        try:
            results = self.knowledge_dashboard.search_memory(query, days=days) or []
            return {"query": query, "results": results}
        except Exception as exc:
            return {"query": query, "results": [], "error": str(exc)}

    def read_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        return self.knowledge_dashboard.read_note(note_id)

    # ------------------------------------------------------------------
    # SOP / Rules
    # ------------------------------------------------------------------

    def get_sop_rules(self) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            definitions = [
                sop.to_dict() for sop in DEFAULT_SOP_DEFINITIONS
            ]
        except Exception as exc:
            definitions = []
            errors.append(f"SOP definitions: {exc}")

        try:
            executions = self.sop_uow.executions().list(store_id=self.store_id, limit=20) or []
            execution_rows = [
                {
                    "sop_code": e.sop_code,
                    "execution_id": e.execution_id,
                    "applies": e.applies,
                    "executed_at": e.executed_at.isoformat() if e.executed_at else None,
                }
                for e in executions
            ]
        except Exception as exc:
            execution_rows = []
            errors.append(f"SOP executions: {exc}")

        try:
            policy_rules = [rule.to_dict() for rule in DEFAULT_POLICIES]
        except Exception as exc:
            policy_rules = []
            errors.append(f"Policy rules: {exc}")

        return {
            "generated_at": self.now.isoformat(),
            "sops": definitions,
            "policy_rules": policy_rules,
            "recent_executions": execution_rows,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Experiments
    # ------------------------------------------------------------------

    def get_experiments(self) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            # Experiments are decisions/plans with experiment metadata. We surface
            # recent decisions that came from the experiment engine plus any recent
            # execution plans carrying experiment metadata.
            decisions = self.decision_dashboard.get_open_decisions(limit=100) or []
            all_decisions = decisions  # open only
            experiment_decisions = [
                d for d in all_decisions
                if d.get("metadata", {}).get("source") == "experiment_engine"
            ]
            recent_executions = self.execution_dashboard.get_recent_executions(hours=168, limit=50) or []
            experiment_plans = [
                p for p in recent_executions
                if p.get("payload", {}).get("metadata", {}).get("source") == "experiment_engine"
            ]
        except Exception as exc:
            experiment_decisions = []
            experiment_plans = []
            errors.append(f"Experiments: {exc}")

        return {
            "generated_at": self.now.isoformat(),
            "experiment_decisions": experiment_decisions,
            "experiment_plans": experiment_plans,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Operations / System Health
    # ------------------------------------------------------------------

    def get_operations(self) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            freshness = self.query_service.get_freshness(self.store_id) or {}
        except Exception as exc:
            freshness = {}
            errors.append(f"Freshness: {exc}")

        try:
            sync_health = self.query_service.get_sync_health(self.store_id) or []
        except Exception as exc:
            sync_health = []
            errors.append(f"Sync health: {exc}")

        try:
            data_quality = self.query_service.get_data_quality_summary(self.store_id) or {}
        except Exception as exc:
            data_quality = {}
            errors.append(f"Data quality: {exc}")

        try:
            system_health = self.monitoring_dashboard.get_system_health(since_hours=24) or {"components": []}
        except Exception as exc:
            system_health = {"components": []}
            errors.append(f"System health: {exc}")

        try:
            open_alerts = self.monitoring_dashboard.get_open_alerts() or []
        except Exception as exc:
            open_alerts = []
            errors.append(f"Open alerts: {exc}")

        try:
            job_summary = self.job_health.summary(hours=24)
            job_latest = self.job_runner.health_summary()
        except Exception as exc:
            job_summary = {}
            job_latest = []
            errors.append(f"Job health: {exc}")

        try:
            dead_letters = self.events_dashboard.get_dead_letters(limit=20) or []
        except Exception as exc:
            dead_letters = []
            errors.append(f"Dead letters: {exc}")

        try:
            snapshot = self.monitoring_dashboard.get_health_snapshot() or {}
        except Exception as exc:
            snapshot = {}
            errors.append(f"Snapshot: {exc}")

        return {
            "generated_at": self.now.isoformat(),
            "sync": {
                "freshness": freshness,
                "sync_health": sync_health,
            },
            "data_quality": data_quality,
            "system_health": system_health,
            "open_alerts": open_alerts,
            "jobs": {
                "summary": job_summary,
                "latest": job_latest,
            },
            "dead_letters": dead_letters,
            "snapshot": snapshot,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            summary = self.analytics_dashboard.summary(days=days) or {}
        except Exception as exc:
            summary = {}
            errors.append(f"Analytics summary: {exc}")

        try:
            financial = self.analytics_dashboard.financial_summary(days=days) or {}
        except Exception as exc:
            financial = {}
            errors.append(f"Financial summary: {exc}")

        try:
            inventory = self.analytics_dashboard.inventory_recommendations() or {}
        except Exception as exc:
            inventory = {}
            errors.append(f"Inventory: {exc}")

        try:
            sales_forecast = self.analytics_dashboard.forecasting.sales_forecast(horizon_days=14).to_dict()
        except Exception as exc:
            sales_forecast = {}
            errors.append(f"Sales forecast: {exc}")

        return {
            "generated_at": self.now.isoformat(),
            "days": days,
            "summary": summary,
            "financial": financial,
            "inventory": inventory,
            "sales_forecast": sales_forecast,
            "errors": errors,
        }

    def run_scenario(self, scenario_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self.analytics_dashboard.run_scenario(scenario_type, parameters)
        except Exception as exc:
            return {"scenario_type": scenario_type, "parameters": parameters, "error": str(exc)}

    # ------------------------------------------------------------------
    # Business Timeline
    # ------------------------------------------------------------------

    def get_timeline(self, hours: int = 24) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            events = self.events_dashboard.get_recent_events(hours=hours, limit=100) or []
        except Exception as exc:
            events = []
            errors.append(f"Events: {exc}")

        try:
            recent_executions = self.execution_dashboard.get_recent_executions(hours=hours, limit=50) or []
        except Exception as exc:
            recent_executions = []
            errors.append(f"Executions: {exc}")

        try:
            decisions = self.decision_dashboard.get_open_decisions(limit=100) or []
        except Exception as exc:
            decisions = []
            errors.append(f"Decisions: {exc}")

        try:
            knowledge = self.knowledge_dashboard.memory_timeline(days=max(1, hours // 24)) or []
        except Exception as exc:
            knowledge = []
            errors.append(f"Knowledge: {exc}")

        try:
            sync_runs = self.query_service.get_sync_health(self.store_id) or []
            recent_sync = sync_runs[:20]
        except Exception as exc:
            recent_sync = []
            errors.append(f"Sync runs: {exc}")

        # Normalize into a single timeline.
        timeline_items: List[Dict[str, Any]] = []
        for event in events:
            timeline_items.append({
                "timestamp": event.get("created_at") or event.get("published_at"),
                "type": "event",
                "title": event.get("event_type", "Event"),
                "status": event.get("status"),
                "id": event.get("id"),
                "details": event,
            })
        for plan in recent_executions:
            timeline_items.append({
                "timestamp": plan.get("created_at") or plan.get("started_at"),
                "type": "execution",
                "title": plan.get("action_type", "Execution"),
                "status": plan.get("status"),
                "id": plan.get("id"),
                "details": plan,
            })
        for d in decisions:
            timeline_items.append({
                "timestamp": d.get("created_at"),
                "type": "decision",
                "title": d.get("title", "Decision"),
                "status": d.get("status"),
                "id": d.get("id"),
                "details": d,
            })
        for note in knowledge:
            timeline_items.append({
                "timestamp": note.get("note_date"),
                "type": "knowledge",
                "title": note.get("title", "Note"),
                "status": "active" if not note.get("archived_at") else "archived",
                "id": note.get("note_id"),
                "details": note,
            })
        for sync in recent_sync:
            timeline_items.append({
                "timestamp": sync.get("completed_at") or sync.get("created_at"),
                "type": "sync",
                "title": sync.get("entity_type", "Sync"),
                "status": sync.get("status"),
                "id": sync.get("id"),
                "details": sync,
            })

        timeline_items = [i for i in timeline_items if i.get("timestamp")]
        timeline_items.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "generated_at": self.now.isoformat(),
            "hours": hours,
            "items": timeline_items[:100],
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Helper for COO ask box
    # ------------------------------------------------------------------

    def ask_coo(self, query: str) -> Dict[str, Any]:
        try:
            return self.coo_dashboard.ask(query)
        except Exception as exc:
            return {
                "answer": f"Sorry, I could not answer that right now. ({exc})",
                "intent": "error",
                "warnings": [str(exc)],
            }
