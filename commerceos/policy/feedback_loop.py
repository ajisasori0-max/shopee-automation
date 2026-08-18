"""WP4.3 — Feedback Loop.

Strengthens the existing OutcomeTracker. For every executed decision:
- Expected result vs actual result
- Baseline KPI, expected delta, actual delta, measurement window, confidence,
  outcome classification, financial/operational impact.
- Outcome → lesson → knowledge memory (only when evidence is sufficient).
"""

from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from commerceos.closed_loop.models import DecisionOutcome
from commerceos.closed_loop.service import OutcomeTracker
from commerceos.decision.models import Decision
from commerceos.execution.models import ExecutionPlan
from commerceos.kpi.engine import KPIEngine
from commerceos.commerce.models import KPI as KPIModel
from commerceos.knowledge.organizational_memory import OrganizationalMemory


class FeedbackLoopService:
    """Measure outcomes of executed decisions and promote lessons to memory."""

    def __init__(
        self,
        session: Session,
        outcome_tracker: Optional[OutcomeTracker] = None,
        org_memory: Optional[OrganizationalMemory] = None,
    ):
        self.session = session
        self.outcome_tracker = outcome_tracker or OutcomeTracker(session, org_memory=org_memory)

    def capture(
        self,
        plan_id: str,
        success: bool,
        impact: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        measurement_window_days: int = 7,
    ) -> DecisionOutcome:
        """Capture the outcome of an execution plan and compute deltas."""
        plan = self.session.query(ExecutionPlan).filter_by(id=plan_id).first()
        if plan is None:
            raise ValueError(f"ExecutionPlan {plan_id} not found")

        decision = self.session.query(Decision).filter_by(id=plan.decision_id).first()
        expected = decision.expected_impact if decision else {}
        actual = dict(impact or {})
        if error:
            actual["error"] = error

        # Compute actual vs baseline KPI deltas if possible.
        baseline = self._load_baseline(plan, days=measurement_window_days)
        actual_metrics = self._load_current(plan, days=measurement_window_days)
        deltas = self._compute_deltas(baseline, actual_metrics)

        outcome = self.outcome_tracker.record(
            decision_id=plan.decision_id,
            execution_plan_id=plan_id,
            expected_outcome=expected,
            actual_outcome={
                **actual,
                "baseline": baseline,
                "current": actual_metrics,
                "deltas": deltas,
                "measurement_window_days": measurement_window_days,
            },
            success=success,
            impact_score=self._compute_impact_score(expected, actual, deltas),
            lessons=[],
            notes=f"Measured over {measurement_window_days} days",
        )

        # Promote to memory only if there is sufficient evidence.
        if self._sufficient_evidence(outcome):
            self.outcome_tracker.promote_to_memory(outcome.id)

        return outcome

    def _load_baseline(self, plan: ExecutionPlan, days: int) -> Dict[str, Any]:
        """Load KPIs before the plan was executed."""
        if plan.completed_at is None:
            return {}
        start = plan.completed_at - timedelta(days=days)
        end = plan.completed_at
        return self._load_kpis(start, end)

    def _load_current(self, plan: ExecutionPlan, days: int) -> Dict[str, Any]:
        """Load KPIs after the plan was executed."""
        if plan.completed_at is None:
            return {}
        start = plan.completed_at
        end = plan.completed_at + timedelta(days=days)
        return self._load_kpis(start, end)

    def _load_kpis(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Aggregate KPIs over a window."""
        # Default store; could be parameterized.
        store_id = "store-ppm-001"
        kpis = (
            self.session.query(KPIModel)
            .filter(
                KPIModel.store_id == store_id,
                KPIModel.freshness >= start,
                KPIModel.freshness <= end,
            )
            .all()
        )
        if not kpis:
            return {}
        by_code: Dict[str, List[float]] = {}
        for kpi in kpis:
            by_code.setdefault(kpi.code, []).append(float(kpi.value))
        return {code: round(sum(values) / len(values), 2) for code, values in by_code.items()}

    def _compute_deltas(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        deltas = {}
        for key in set(baseline.keys()) | set(current.keys()):
            b = baseline.get(key)
            c = current.get(key)
            if isinstance(b, (int, float)) and isinstance(c, (int, float)) and b != 0:
                deltas[key] = round((c - b) / b, 4)
            else:
                deltas[key] = None
        return deltas

    def _compute_impact_score(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
        deltas: Dict[str, Any],
    ) -> Optional[float]:
        comparable = []
        for key in ("roas", "revenue", "profit", "conversion_rate", "gross_sales"):
            exp = expected.get(key)
            if exp is None:
                exp = expected.get("expected_revenue_change") if key == "revenue" else None
            act = actual.get(key)
            if isinstance(exp, (int, float)) and exp != 0 and isinstance(act, (int, float)):
                comparable.append(min(act / exp, 2.0))
            delta = deltas.get(key)
            if isinstance(delta, (int, float)) and delta is not None:
                comparable.append(min(1.0 + delta, 2.0))
        if not comparable:
            return None
        return round(sum(comparable) / len(comparable), 3)

    def _sufficient_evidence(self, outcome: DecisionOutcome) -> bool:
        """Only promote successful outcomes with measurable deltas."""
        if outcome.success is not True:
            return False
        actual = outcome.actual_outcome or {}
        deltas = actual.get("deltas", {})
        has_measurable_delta = any(isinstance(v, (int, float)) and v is not None for v in deltas.values())
        return has_measurable_delta
