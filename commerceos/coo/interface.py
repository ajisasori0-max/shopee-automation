"""COO Interface — deterministic query router and response builder.

WP3.5 turns the existing knowledge, decision, monitoring, and execution
infrastructure into an actual interactive COO interface. It supports questions
such as:

- What matters today?
- What changed this week?
- Why did revenue fall?
- What should I approve?
- What are we waiting on?
- What happened with [project/campaign/SKU]?
- Show me relevant history.
- What did we try before?
- What decisions are unresolved?

Architecture:
User query → intent classification → context retrieval → business state +
intelligence + knowledge → structured response with source references.

The COO Interface does NOT dump the entire knowledge base into context. It uses
deterministic retrieval and rule-based routing first. LLM functionality is used
only where it provides clear value, and factual answers are always grounded in
CommerceOS data. Uncertain answers explicitly state uncertainty.
"""

from commerceos.shared.value_objects.primitives import utc_now

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from commerceos.config.settings import Settings, get_settings
from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.decision.constants import DecisionCategory, DecisionSeverity
from commerceos.decision.dashboard import DecisionDashboard
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.events.dashboard import EventsDashboard
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork
from commerceos.execution.dashboard import ExecutionDashboard
from commerceos.execution.sqlalchemy_repositories import SQLAlchemyExecutionUnitOfWork
from commerceos.intelligence.dashboard import IntelligenceDashboard
from commerceos.knowledge.dashboard import KnowledgeDashboard
from commerceos.knowledge.sqlalchemy_repositories import SQLAlchemyKnowledgeUnitOfWork
from commerceos.monitoring.dashboard import MonitoringDashboard
from commerceos.monitoring.sqlalchemy_repositories import SQLAlchemyMonitoringUnitOfWork


STORE_ID = "store-ppm-001"


@dataclass
class COOQuery:
    """A normalized COO query after intent classification."""

    raw: str
    intent: str = "unknown"
    entities: Dict[str, List[str]] = field(default_factory=dict)
    time_window_days: int = 7
    needs_approval_context: bool = False
    needs_history: bool = False


@dataclass
class COOResponse:
    """A structured response from the COO Interface."""

    answer: str
    intent: str
    sources: List[Dict[str, Any]] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "intent": self.intent,
            "sources": self.sources,
            "data": self.data,
            "warnings": self.warnings,
            "suggested_actions": self.suggested_actions,
        }


class COOIntentClassifier:
    """Rule-based intent classifier for COO questions.

    Uses deterministic keyword matching. No LLM is required for classification.
    """

    INTENTS: Dict[str, List[str]] = {
        "what_matters_today": ["what matters", "what matters today", "what is urgent", "what needs attention", "top priorities"],
        "what_changed": ["what changed", "what changed this week", "what is different", "what happened recently"],
        "why_revenue_fell": ["why did revenue fall", "why revenue dropped", "revenue drop", "sales dropped", "why sales down"],
        "what_to_approve": ["what should i approve", "what needs approval", "what is waiting for approval", "pending approvals"],
        "what_waiting": ["what are we waiting on", "what is blocked", "what is pending", "waiting on"],
        "project_history": ["what happened with", "tell me about", "history of", "what did we do about"],
        "show_history": ["show me relevant history", "relevant history", "recent history", "show history"],
        "what_tried_before": ["what did we try before", "previous experiments", "lessons learned", "what worked before"],
        "unresolved_decisions": ["unresolved decisions", "open decisions", "what decisions are unresolved", "pending decisions"],
        "help": ["what can you do", "help", "commands", "what questions can i ask"],
    }

    def classify(self, query: str) -> Tuple[str, Dict[str, List[str]]]:
        lower = query.lower().strip()
        for intent, phrases in self.INTENTS.items():
            for phrase in phrases:
                if phrase in lower:
                    return intent, self._extract_entities(lower)
        return "unknown", self._extract_entities(lower)

    @staticmethod
    def _extract_entities(query: str) -> Dict[str, List[str]]:
        """Extract simple project/campaign/SKU entities from the query."""
        entities: Dict[str, List[str]] = {}
        # SKU patterns: W-001, SKU-123, etc.
        import re
        skus = re.findall(r"\b[A-Z]{1,3}-\d{2,6}\b", query.upper())
        if skus:
            entities["sku"] = skus
        # Campaign/project names: quoted strings
        quoted = re.findall(r'"([^"]+)"', query)
        if quoted:
            entities["project"] = quoted
        return entities


class COOContextEngine:
    """Gather only the relevant context needed for a classified query.

    Each gather method returns a small, deterministic data structure. The methods
    are invoked lazily based on the query intent.
    """

    def __init__(
        self,
        session: Session,
        settings: Optional[Settings] = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.query_service = DashboardQueryService(session=session, database_url=self.settings.database_url)
        self.knowledge_uow = SQLAlchemyKnowledgeUnitOfWork(session)
        self.knowledge_dashboard = KnowledgeDashboard(self.knowledge_uow.notes(), vault_dir=self.settings.obsidian_vault_path)
        self.decision_uow = SQLAlchemyDecisionUnitOfWork(session)
        self.decision_dashboard = DecisionDashboard(self.decision_uow)
        self.monitoring_uow = SQLAlchemyMonitoringUnitOfWork(session)
        self.monitoring_dashboard = MonitoringDashboard(self.monitoring_uow)
        self.intelligence_dashboard = IntelligenceDashboard(None)  # type: ignore
        self.events_dashboard = EventsDashboard(SQLAlchemyEventsUnitOfWork(session))
        self.execution_dashboard = ExecutionDashboard(SQLAlchemyExecutionUnitOfWork(session))

    def today_matters(self) -> Dict[str, Any]:
        """Return what matters today: open decisions, recent alerts, stale data."""
        end = utc_now()
        start = end - timedelta(days=1)
        decisions = self.decision_dashboard.get_high_priority(limit=5)
        state = self.query_service.get_commerce_state(STORE_ID)
        alerts = state.get("alerts", [])
        recent_events = self.events_dashboard.get_recent_events(hours=24, limit=10)
        return {
            "high_priority_decisions": decisions,
            "alerts": alerts,
            "recent_events": recent_events,
            "data_freshness": self.query_service.get_freshness(STORE_ID),
        }

    def what_changed(self, days: int = 7) -> Dict[str, Any]:
        """Return week-over-week changes in key business metrics."""
        end = utc_now()
        start = end - timedelta(days=days)
        current = self.query_service.get_pl_summary(STORE_ID, start, end)
        baseline_start = start - timedelta(days=days)
        baseline_end = start
        baseline = self.query_service.get_pl_summary(STORE_ID, baseline_start, baseline_end)

        current_ad = self.query_service.get_ad_performance_summary(STORE_ID, start, end)
        baseline_ad = self.query_service.get_ad_performance_summary(STORE_ID, baseline_start, baseline_end)

        return {
            "window_days": days,
            "current": current,
            "baseline": baseline,
            "revenue_delta_pct": _pct_delta(current.get("gross_sales"), baseline.get("gross_sales")),
            "orders_delta_pct": _pct_delta(current.get("order_count"), baseline.get("order_count")),
            "ad_spend_delta_pct": _pct_delta(current_ad.get("total_spend"), baseline_ad.get("total_spend")),
            "roas_delta_pct": _pct_delta(current_ad.get("roas"), baseline_ad.get("roas")),
        }

    def why_revenue_fell(self, days: int = 7) -> Dict[str, Any]:
        """Diagnose a revenue drop using available metrics."""
        changed = self.what_changed(days)
        revenue_delta = changed.get("revenue_delta_pct")
        result = {
            "window_days": days,
            "revenue_delta_pct": revenue_delta,
            "current": changed["current"],
            "baseline": changed["baseline"],
            "traffic_delta_pct": changed.get("ad_spend_delta_pct"),  # proxy for traffic direction
            "causes": [],
            "missing_inputs": [],
        }
        if revenue_delta is None:
            result["missing_inputs"].append("revenue")
        elif revenue_delta >= 0:
            result["causes"].append("Revenue did not fall in the selected window.")
        else:
            if changed.get("orders_delta_pct", 0) < -0.10:
                result["causes"].append("Order volume dropped.")
            if changed.get("ad_spend_delta_pct", 0) < -0.20:
                result["causes"].append("Ad spend was significantly reduced.")
            if changed.get("roas_delta_pct", 0) < -0.20:
                result["causes"].append("ROAS declined, reducing ad efficiency.")
            # Out-of-stock check
            zero_stock = self._zero_stock_skus()
            if zero_stock:
                result["causes"].append(f"{len(zero_stock)} SKU(s) out of stock: {', '.join(zero_stock[:5])}.")
            result["missing_inputs"].extend(["price history", "traffic source breakdown"])
        return result

    def what_to_approve(self) -> Dict[str, Any]:
        """Return open decisions that are awaiting approval."""
        return {
            "pending_approvals": self.decision_dashboard.get_open_decisions(limit=50),
            "high_priority": self.decision_dashboard.get_high_priority(limit=5),
        }

    def what_waiting(self) -> Dict[str, Any]:
        """Return blocked items: open decisions, recent failures, unresolved events."""
        return {
            "open_decisions": self.decision_dashboard.get_open_decisions(limit=20),
            "recent_failures": self.events_dashboard.get_failed_events(limit=10),
            "stale_data": self.query_service.get_freshness(STORE_ID),
        }

    def project_history(self, entity: str, days: int = 30) -> Dict[str, Any]:
        """Return notes, decisions, and events related to a project/campaign/SKU."""
        notes = self.knowledge_dashboard.search_memory(entity, days=days)
        events = self.events_dashboard.get_recent_events(hours=days * 24, limit=50)
        events = [e for e in events if entity.lower() in str(e.get("payload", {})).lower() or entity.lower() in (e.get("aggregate_id") or "").lower()]
        decisions = self.decision_dashboard.get_open_decisions(limit=100)
        related_decisions = [d for d in decisions if entity.lower() in d["title"].lower() or entity.lower() in d["description"].lower()]
        return {
            "entity": entity,
            "window_days": days,
            "notes": notes,
            "events": events,
            "decisions": related_decisions,
        }

    def show_history(self, days: int = 14) -> Dict[str, Any]:
        """Return recent memory timeline."""
        return {
            "memory_timeline": self.knowledge_dashboard.memory_timeline(days=days),
            "recent_lessons": self.knowledge_dashboard.recent_lessons(days=days),
            "recent_decisions": self.knowledge_dashboard.recent_decisions(days=days),
        }

    def what_tried_before(self, topic: Optional[str] = None, days: int = 90) -> Dict[str, Any]:
        """Return recent lessons and experiment-like notes."""
        lessons = self.knowledge_dashboard.recent_lessons(days=days, limit=20)
        if topic:
            lessons = [l for l in lessons if topic.lower() in l.get("title", "").lower() or topic.lower() in " ".join(l.get("tags", [])).lower()]
        return {
            "topic": topic,
            "lessons": lessons,
        }

    def unresolved_decisions(self) -> Dict[str, Any]:
        """Return all unresolved / open decisions."""
        return {
            "open_decisions": self.decision_dashboard.get_open_decisions(limit=100),
            "summary": self.decision_dashboard.get_decision_summary(),
        }

    def _zero_stock_skus(self) -> List[str]:
        from commerceos.commerce.models import Inventory, Variant

        rows = (
            self.session.query(Variant.sku)
            .join(Inventory, Inventory.variant_id == Variant.id)
            .filter(Inventory.store_id == STORE_ID, Inventory.quantity_available <= 0)
            .all()
        )
        return [r.sku for r in rows if r.sku]


def _pct_delta(current: Optional[float], baseline: Optional[float]) -> Optional[float]:
    if baseline is None or current is None or baseline == 0:
        return None
    return (current - baseline) / baseline


class COOFormatter:
    """Render deterministic, human-readable answers from gathered context."""

    def format_what_matters_today(self, data: Dict[str, Any]) -> str:
        decisions = data.get("high_priority_decisions", [])
        alerts = data.get("alerts", [])
        lines = ["**What matters today**"]
        if decisions:
            lines.append(f"- {len(decisions)} high-priority decision(s) require attention.")
            for d in decisions[:3]:
                lines.append(f"  - [{d['severity'].upper()}] {d['title']}: {d['recommended_action']}")
        else:
            lines.append("- No high-priority decisions pending.")
        if alerts:
            lines.append(f"- {len(alerts)} active alert(s).")
        else:
            lines.append("- No active alerts.")
        return "\n".join(lines)

    def format_what_changed(self, data: Dict[str, Any]) -> str:
        lines = [f"**What changed this week ({data['window_days']} days)**"]
        rev = data.get("revenue_delta_pct")
        lines.append(f"- Revenue: {rev*100:.1f}% vs prior period" if rev is not None else "- Revenue: no baseline available")
        orders = data.get("orders_delta_pct")
        if orders is not None:
            lines.append(f"- Orders: {orders*100:.1f}% vs prior period")
        roas = data.get("roas_delta_pct")
        if roas is not None:
            lines.append(f"- ROAS: {roas*100:.1f}% vs prior period")
        return "\n".join(lines)

    def format_why_revenue_fell(self, data: Dict[str, Any]) -> str:
        lines = ["**Revenue diagnosis**"]
        rev = data.get("revenue_delta_pct")
        if rev is None:
            lines.append("Revenue data is unavailable for the selected window.")
        elif rev >= 0:
            lines.append(f"Revenue did not fall; it is up {rev*100:.1f}% vs baseline.")
        else:
            lines.append(f"Revenue is down {rev*100:.1f}% vs baseline.")
            if data.get("causes"):
                lines.append("Likely causes:")
                for cause in data["causes"]:
                    lines.append(f"- {cause}")
            else:
                lines.append("No strong causal signal found in the available data.")
        if data.get("missing_inputs"):
            lines.append(f"Missing inputs: {', '.join(set(data['missing_inputs']))}.")
        return "\n".join(lines)

    def format_what_to_approve(self, data: Dict[str, Any]) -> str:
        pending = data.get("pending_approvals", [])
        lines = [f"**Pending approvals: {len(pending)}**"]
        for d in pending[:5]:
            lines.append(f"- [{d['severity'].upper()}] {d['title']}\n  Action: {d['recommended_action']}")
        return "\n".join(lines)

    def format_what_waiting(self, data: Dict[str, Any]) -> str:
        open_decisions = data.get("open_decisions", [])
        failures = data.get("recent_failures", [])
        lines = [f"**Waiting on: {len(open_decisions)} open decision(s)**"]
        if failures:
            lines.append(f"Recent failures: {len(failures)}")
        return "\n".join(lines)

    def format_project_history(self, data: Dict[str, Any]) -> str:
        lines = [f"**History for '{data['entity']}' ({data['window_days']} days)**"]
        notes = data.get("notes", [])
        events = data.get("events", [])
        decisions = data.get("decisions", [])
        lines.append(f"- Notes: {len(notes)}, Events: {len(events)}, Decisions: {len(decisions)}")
        if notes:
            lines.append("Recent notes:")
            for n in notes[:3]:
                lines.append(f"  - {n.get('title')} ({n.get('note_date')})")
        return "\n".join(lines)

    def format_show_history(self, data: Dict[str, Any]) -> str:
        timeline = data.get("memory_timeline", [])
        lessons = data.get("recent_lessons", [])
        lines = [f"**Recent history ({len(timeline)} notes, {len(lessons)} lessons)**"]
        for n in timeline[:5]:
            lines.append(f"- {n.get('note_date')} {n.get('title')}")
        return "\n".join(lines)

    def format_what_tried_before(self, data: Dict[str, Any]) -> str:
        lessons = data.get("lessons", [])
        topic = data.get("topic")
        lines = [f"**Lessons learned{f' for {topic}' if topic else ''}: {len(lessons)}**"]
        for l in lessons[:5]:
            lines.append(f"- {l.get('title')} ({l.get('note_date')})")
        return "\n".join(lines)

    def format_unresolved_decisions(self, data: Dict[str, Any]) -> str:
        decisions = data.get("open_decisions", [])
        summary = data.get("summary", {})
        lines = [f"**Unresolved decisions: {len(decisions)}**"]
        for d in decisions[:5]:
            lines.append(f"- [{d['severity'].upper()}] {d['title']}")
        lines.append(f"Overall severity: {summary.get('overall_severity', 'info')}")
        return "\n".join(lines)

    def format_help(self) -> str:
        return (
            "I can answer questions like:\n"
            "- What matters today?\n"
            "- What changed this week?\n"
            "- Why did revenue fall?\n"
            "- What should I approve?\n"
            "- What are we waiting on?\n"
            "- What happened with [project/campaign/SKU]?\n"
            "- Show me relevant history.\n"
            "- What did we try before?\n"
            "- What decisions are unresolved?"
        )

    def format_unknown(self) -> str:
        return (
            "I'm not sure how to answer that. Try one of these:\n"
            "- What matters today?\n"
            "- What changed this week?\n"
            "- What should I approve?\n"
            "- What decisions are unresolved?"
        )


class COOInterface:
    """Main entry point for the COO Interface.

    Given a natural-language query, classify the intent, gather minimal relevant
    context, and return a structured, grounded response.
    """

    def __init__(
        self,
        session: Session,
        settings: Optional[Settings] = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.classifier = COOIntentClassifier()
        self.context_engine = COOContextEngine(session, settings)
        self.formatter = COOFormatter()

    def ask(self, query: str) -> COOResponse:
        intent, entities = self.classifier.classify(query)
        data: Dict[str, Any] = {}
        warnings: List[str] = []

        if intent == "what_matters_today":
            data = self.context_engine.today_matters()
            answer = self.formatter.format_what_matters_today(data)
        elif intent == "what_changed":
            data = self.context_engine.what_changed()
            answer = self.formatter.format_what_changed(data)
        elif intent == "why_revenue_fell":
            data = self.context_engine.why_revenue_fell()
            answer = self.formatter.format_why_revenue_fell(data)
        elif intent == "what_to_approve":
            data = self.context_engine.what_to_approve()
            answer = self.formatter.format_what_to_approve(data)
        elif intent == "what_waiting":
            data = self.context_engine.what_waiting()
            answer = self.formatter.format_what_waiting(data)
        elif intent == "project_history":
            entity = (entities.get("sku") or entities.get("project") or [None])[0]
            if entity:
                data = self.context_engine.project_history(entity)
                answer = self.formatter.format_project_history(data)
            else:
                answer = "Please specify a project, campaign, or SKU."
                warnings.append("No entity found in query")
        elif intent == "show_history":
            data = self.context_engine.show_history()
            answer = self.formatter.format_show_history(data)
        elif intent == "what_tried_before":
            topic = (entities.get("project") or [None])[0]
            data = self.context_engine.what_tried_before(topic)
            answer = self.formatter.format_what_tried_before(data)
        elif intent == "unresolved_decisions":
            data = self.context_engine.unresolved_decisions()
            answer = self.formatter.format_unresolved_decisions(data)
        elif intent == "help":
            answer = self.formatter.format_help()
        else:
            answer = self.formatter.format_unknown()
            warnings.append("Intent not recognized; response is generic")

        sources = self._build_sources(intent, data)
        suggested_actions = self._suggest_actions(intent, data)

        return COOResponse(
            answer=answer,
            intent=intent,
            sources=sources,
            data=data,
            warnings=warnings,
            suggested_actions=suggested_actions,
        )

    def _build_sources(self, intent: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Attach source references to the response for traceability."""
        sources = []
        if intent in ("what_matters_today", "what_to_approve", "unresolved_decisions", "what_waiting"):
            sources.append({"type": "decision_engine", "description": "Open decisions from DecisionEngine"})
        if intent in ("what_changed", "why_revenue_fell"):
            sources.append({"type": "kpi", "description": "Materialized KPIs and P&L summary"})
            sources.append({"type": "ad_performance", "description": "Ad performance summary"})
        if intent in ("what_matters_today", "what_waiting"):
            sources.append({"type": "events", "description": "Recent system events"})
            sources.append({"type": "monitoring", "description": "CommerceState alerts and data freshness"})
        if intent in ("show_history", "what_tried_before", "project_history"):
            sources.append({"type": "knowledge", "description": "Knowledge vault metadata"})
        if intent == "project_history":
            sources.append({"type": "events", "description": "Events related to entity"})
        return sources

    def _suggest_actions(self, intent: str, data: Dict[str, Any]) -> List[str]:
        """Suggest concrete next actions based on the response data."""
        actions = []
        if intent == "what_matters_today":
            decisions = data.get("high_priority_decisions", [])
            if decisions:
                actions.append("Review the top high-priority decision in the dashboard.")
        if intent == "why_revenue_fell":
            if data.get("causes"):
                actions.append("Run the REVENUE_DROP SOP to create a structured decision.")
        if intent == "what_to_approve":
            actions.append("Approve or reject the oldest pending decision first.")
        if intent == "unresolved_decisions":
            actions.append("Schedule a weekly decision review to clear stale proposals.")
        return actions


# Convenience function for scripts/dashboards.
def ask_coo(session: Session, query: str, settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Ask the COO Interface a question and return a dict response."""
    interface = COOInterface(session, settings)
    return interface.ask(query).to_dict()
