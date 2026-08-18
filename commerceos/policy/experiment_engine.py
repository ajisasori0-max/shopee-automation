"""WP4.4 — Experimentation Engine.

Controlled experiments with hypothesis, baseline, treatment, target metric,
expected effect, duration, guardrails, start/end, result, conclusion, and
keep/rollback decision.

Integrates: Experiment → Policy → Execution → Measurement → Outcome → Knowledge.
"""

from commerceos.shared.value_objects.primitives import utc_now

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.decision.constants import DecisionCategory, DecisionSeverity
from commerceos.decision.models import Decision
from commerceos.execution.engine import ExecutionEngine
from commerceos.execution.models import ExecutionPlan
from commerceos.policy.autonomous_execution import AutonomousExecutionService
from commerceos.policy.engine import PolicyEngine
from commerceos.policy.feedback_loop import FeedbackLoopService


@dataclass
class ExperimentDefinition:
    """Definition of a controlled business experiment."""

    experiment_id: str
    hypothesis: str
    target_metric: str
    expected_effect: float
    duration_days: int
    baseline_value: Optional[float] = None
    treatment_value: Optional[float] = None
    guardrails: Dict[str, Any] = field(default_factory=dict)
    action_type: str = "adjust_budget"
    scope: str = "campaign"
    change_pct: float = 0.0
    absolute_change: Optional[float] = None
    rollback_on_failure: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "target_metric": self.target_metric,
            "expected_effect": self.expected_effect,
            "duration_days": self.duration_days,
            "baseline_value": self.baseline_value,
            "treatment_value": self.treatment_value,
            "guardrails": self.guardrails,
            "action_type": self.action_type,
            "scope": self.scope,
            "change_pct": self.change_pct,
            "absolute_change": self.absolute_change,
            "rollback_on_failure": self.rollback_on_failure,
        }


class ExperimentEngine:
    """Run controlled experiments that integrate with policy and execution."""

    def __init__(
        self,
        session: Session,
        policy_engine: Optional[PolicyEngine] = None,
        execution_engine: Optional[ExecutionEngine] = None,
    ):
        self.session = session
        self.policy_engine = policy_engine or PolicyEngine()
        self.execution_engine = execution_engine or ExecutionEngine(session)
        self.autonomous = AutonomousExecutionService(
            session,
            execution_engine=self.execution_engine,
            policy_engine=self.policy_engine,
        )
        self.feedback = FeedbackLoopService(session)

    def start(
        self,
        experiment: ExperimentDefinition,
        actor: Optional[str] = None,
        marketplace_fn: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Start an experiment by creating a proposed decision and, if policy allows, executing it."""
        # Guardrail checks
        guardrail_violations = self._check_guardrails(experiment)
        if guardrail_violations:
            return {
                "experiment_id": experiment.experiment_id,
                "status": "blocked",
                "reason": "Guardrail violations: " + ", ".join(guardrail_violations),
                "decision_id": None,
                "plan_id": None,
            }

        # Policy check before creating a decision
        policy_result = self.policy_engine.evaluate(
            experiment.action_type,
            experiment.scope,
            experiment.change_pct,
            experiment.absolute_change,
        )
        if not policy_result.allowed:
            return {
                "experiment_id": experiment.experiment_id,
                "status": "blocked",
                "reason": policy_result.reason,
                "policy": policy_result.to_dict(),
                "decision_id": None,
                "plan_id": None,
            }

        # Create a decision representing the experiment
        decision = Decision(
            category=DecisionCategory.OPERATIONS.value,
            severity=DecisionSeverity.NOTICE.value,
            status="approved" if policy_result.auto_approve else "proposed",
            title=f"Experiment: {experiment.experiment_id}",
            description=experiment.hypothesis,
            rationale=f"Controlled experiment: {experiment.target_metric} expected {experiment.expected_effect*100:+.1f}% over {experiment.duration_days} days.",
            recommended_action=f"Apply {experiment.action_type} ({experiment.change_pct:+.1f}% change) and measure {experiment.target_metric}.",
            expected_impact={
                "target_metric": experiment.target_metric,
                "expected_effect": experiment.expected_effect,
                "duration_days": experiment.duration_days,
                "baseline_value": experiment.baseline_value,
                "treatment_value": experiment.treatment_value,
            },
            confidence="medium",
            metadata_={"experiment_id": experiment.experiment_id, "source": "experiment_engine"},
        )
        self.session.add(decision)
        self.session.flush()

        # If not auto-approved, stop and wait for human approval
        if not policy_result.auto_approve:
            return {
                "experiment_id": experiment.experiment_id,
                "status": "approval_required",
                "reason": f"Policy requires {policy_result.approval_authority} approval",
                "policy": policy_result.to_dict(),
                "decision_id": decision.id,
                "plan_id": None,
            }

        # Auto-execute via the autonomous execution service
        result = self.autonomous.process_decision(decision, actor=actor, marketplace_fn=marketplace_fn)
        return {
            "experiment_id": experiment.experiment_id,
            "status": "running" if result.get("auto_executed") else result.get("status"),
            "reason": result.get("reason"),
            "policy": policy_result.to_dict(),
            "decision_id": decision.id,
            "plan_id": result.get("plan_id"),
        }

    def conclude(
        self,
        experiment_id: str,
        plan_id: str,
        success: bool,
        impact: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Conclude an experiment and record the outcome."""
        outcome = self.feedback.capture(plan_id, success=success, impact=impact, measurement_window_days=1)
        return {
            "experiment_id": experiment_id,
            "plan_id": plan_id,
            "outcome_id": outcome.id,
            "success": outcome.success,
            "impact_score": outcome.impact_score,
            "actual_outcome": outcome.actual_outcome,
            "conclusion": "keep" if success else "rollback",
        }

    def _check_guardrails(self, experiment: ExperimentDefinition) -> List[str]:
        violations = []
        if experiment.duration_days <= 0:
            violations.append("duration_days must be positive")
        if experiment.duration_days > 30:
            violations.append("duration_days must be <= 30")
        if abs(experiment.change_pct) > 50:
            violations.append("change_pct must be <= 50%")
        max_budget = experiment.guardrails.get("max_budget_change", 10_000_000)
        if experiment.absolute_change and abs(experiment.absolute_change) > max_budget:
            violations.append(f"absolute_change exceeds max_budget_change {max_budget:,.0f}")
        return violations
