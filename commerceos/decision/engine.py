"""Decision Engine: generates and persists recommendations from signals.

The engine consumes existing platform services only: KPIs, CommerceState,
insights, and monitoring alerts. It never calls Shopee APIs.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.commerce.models import CommerceState, KPI
from commerceos.decision.approval import ApprovalWorkflow
from commerceos.decision.constants import DecisionCategory, DecisionConfidence, DecisionSeverity, EvidenceSource
from commerceos.decision.models import Decision, DecisionEvidence, DecisionHistory
from commerceos.decision.recommendation import Recommendation
from commerceos.decision.repositories import DecisionUnitOfWork
from commerceos.decision.rules.advertising import AdvertisingRules
from commerceos.decision.rules.finance import FinanceRules
from commerceos.decision.rules.inventory import InventoryRules
from commerceos.decision.rules.pricing import PricingRules
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.kpi.engine import KPIEngine


RULE_REGISTRY = {
    DecisionCategory.ADVERTISING: AdvertisingRules,
    DecisionCategory.PRICING: PricingRules,
    DecisionCategory.INVENTORY: InventoryRules,
    DecisionCategory.FINANCE: FinanceRules,
    DecisionCategory.OPERATIONS: FinanceRules,
}

CORE_KPIS = [
    "gross_sales",
    "net_sales",
    "order_count",
    "aov",
    "gross_profit",
    "gross_margin_pct",
    "shopee_fees",
    "ad_spend",
    "ad_revenue",
    "roas",
    "ctr",
]


class DecisionEngine:
    """Generate deterministic business decisions from existing platform state."""

    def __init__(
        self,
        session: Session,
        uow: Optional[DecisionUnitOfWork] = None,
    ):
        self.session = session
        self.uow = uow or SQLAlchemyDecisionUnitOfWork(session)

    def refresh(
        self,
        store_id: str,
        insights: Optional[List[Dict[str, Any]]] = None,
        monitoring_alerts: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate decisions from current signals and persist them."""
        kpis = self._load_latest_kpis(store_id)
        state = self._load_commerce_state(store_id)
        insights = insights or []
        monitoring_alerts = monitoring_alerts or []

        recommendations = self._evaluate_rules(insights, kpis, state, monitoring_alerts)
        decisions = self._persist_recommendations(store_id, recommendations)

        return {
            "store_id": store_id,
            "decision_count": len(decisions),
            "decisions": [_decision_to_dict(d) for d in decisions],
        }

    def _load_latest_kpis(self, store_id: str) -> Dict[str, Any]:
        """Return latest KPI value per code, plus day-over-day baselines."""
        kpis_by_code: Dict[str, List[KPI]] = {}
        for kpi in (
            self.session.query(KPI)
            .filter_by(store_id=store_id)
            .order_by(KPI.freshness.asc())
            .all()
        ):
            kpis_by_code.setdefault(kpi.code, []).append(kpi)

        latest: Dict[str, Any] = {}
        for code, values in kpis_by_code.items():
            latest[code] = float(values[-1].value) if values else None
            if len(values) >= 2:
                latest[f"{code}_baseline"] = float(values[-2].value)
        return latest

    def _load_commerce_state(self, store_id: str) -> Optional[Dict[str, Any]]:
        state = KPIEngine.latest_commerce_state(self.session, store_id)
        if state is None:
            return None
        return {
            "data_quality_score": float(state.data_quality_score) if state.data_quality_score is not None else None,
            "sources_stale": state.sources_stale or [],
            "summary": state.summary or {},
            "alerts": state.alerts or [],
            "risks": state.risks or [],
        }

    def _evaluate_rules(
        self,
        insights: List[Dict[str, Any]],
        kpis: Dict[str, Any],
        state: Optional[Dict[str, Any]],
        monitoring_alerts: List[Dict[str, Any]],
    ) -> List[Recommendation]:
        all_recommendations: List[Recommendation] = []
        for category, rule_class in RULE_REGISTRY.items():
            rule = rule_class()
            all_recommendations.extend(rule.evaluate(insights, kpis, state))

        return self._deduplicate(all_recommendations)

    def _deduplicate(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        seen = set()
        out = []
        for rec in recommendations:
            key = (rec.category, rec.title)
            if key in seen:
                continue
            seen.add(key)
            out.append(rec)
        return out

    def _persist_recommendations(
        self,
        store_id: str,
        recommendations: List[Recommendation],
        source: str = "rule_engine",
    ) -> List[Decision]:
        decisions = []
        with self.uow:
            for rec in recommendations:
                decision = Decision(
                    category=rec.category,
                    severity=rec.severity,
                    status="proposed",
                    title=rec.title,
                    description=rec.description,
                    rationale=rec.rationale,
                    recommended_action=rec.recommended_action,
                    expected_impact=rec.expected_impact,
                    confidence=rec.confidence,
                    metadata_={"store_id": store_id, "source": source},
                )
                self.uow.decisions().save(decision)
                evidence = [
                    DecisionEvidence(
                        decision_id=decision.id,
                        source_type=e["source_type"],
                        source_id=e.get("source_id"),
                        description=e["description"],
                    )
                    for e in rec.evidence
                ]
                if evidence:
                    self.uow.evidence().save_many(evidence)
                decisions.append(decision)
        return decisions

    def refresh_sop_recommendations(
        self,
        store_id: str,
        sop_result: Dict[str, Any],
    ) -> List[Decision]:
        """Persist SOP-derived recommendations that have not already been proposed."""
        from commerceos.sop.engine import Recommendation as SOPRecommendation

        recommendations = [SOPRecommendation(**r) for r in sop_result.get("recommendations", [])]
        # Only persist decisions for SOPs that are not already open with the same title.
        open_titles = {d.title for d in self.uow.decisions().get_open(limit=1000)}
        new_recommendations = [r for r in recommendations if r.title not in open_titles]
        return self._persist_recommendations(store_id, new_recommendations, source="sop_engine")


class DecisionLifecycleService:
    """Thin service wrapper around ApprovalWorkflow for use by dashboards."""

    def __init__(self, uow: DecisionUnitOfWork):
        self.uow = uow
        self.workflow = ApprovalWorkflow(uow)

    def approve(self, decision_id: str, changed_by: Optional[str] = None, notes: Optional[str] = None) -> Optional[Decision]:
        return self.workflow.approve(decision_id, changed_by, notes)

    def reject(self, decision_id: str, changed_by: Optional[str] = None, notes: Optional[str] = None) -> Optional[Decision]:
        return self.workflow.reject(decision_id, changed_by, notes)

    def expire(self, decision_id: str, changed_by: Optional[str] = None, notes: Optional[str] = None) -> Optional[Decision]:
        return self.workflow.expire(decision_id, changed_by, notes)

    def record_execution(self, decision_id: str, changed_by: Optional[str] = None, notes: Optional[str] = None) -> Optional[Decision]:
        return self.workflow.record_execution(decision_id, changed_by, notes)


def _decision_to_dict(decision: Decision) -> Dict[str, Any]:
    return {
        "id": decision.id,
        "category": decision.category,
        "severity": decision.severity,
        "status": decision.status,
        "title": decision.title,
        "description": decision.description,
        "rationale": decision.rationale,
        "recommended_action": decision.recommended_action,
        "expected_impact": decision.expected_impact,
        "confidence": decision.confidence,
        "created_at": decision.created_at.isoformat() if decision.created_at else None,
        "approved_at": decision.approved_at.isoformat() if decision.approved_at else None,
        "rejected_at": decision.rejected_at.isoformat() if decision.rejected_at else None,
        "executed_at": decision.executed_at.isoformat() if decision.executed_at else None,
        "expires_at": decision.expires_at.isoformat() if decision.expires_at else None,
        "evidence": [
            {
                "source_type": e.source_type,
                "source_id": e.source_id,
                "description": e.description,
            }
            for e in decision.evidence
        ],
    }
