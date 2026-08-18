"""WP4.2 — Autonomous Execution.

Integrates Policy Engine with Execution Engine. The flow is:
Decision → Policy evaluation → Risk classification → Automatic OR approval
→ Execution → Audit → Outcome tracking.

Automatic actions remain idempotent, bounded, auditable, reversible where possible,
rate limited, and policy constrained. Marketplace mutations continue through the
canonical ExecutionEngine.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.decision.models import Decision
from commerceos.execution.constants import ExecutionStatus
from commerceos.execution.engine import ExecutionEngine
from commerceos.execution.models import ExecutionPlan
from commerceos.policy.engine import PolicyEngine, PolicyEvaluation


class AutonomousExecutionService:
    """Evaluate whether a proposed/approved decision should be auto-executed."""

    def __init__(
        self,
        session: Session,
        execution_engine: Optional[ExecutionEngine] = None,
        policy_engine: Optional[PolicyEngine] = None,
    ):
        self.session = session
        self.execution_engine = execution_engine or ExecutionEngine(session)
        self.policy_engine = policy_engine or PolicyEngine()

    def process_decision(
        self,
        decision: Decision,
        actor: Optional[str] = None,
        marketplace_fn: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Route a decision through policy and either auto-execute or request approval.

        This method is idempotent: if an execution plan already exists for the
        decision, it returns the existing plan status.
        """
        # Check for existing plan
        existing = self.execution_engine.execution_uow.plans().list(decision_id=decision.id, limit=1)
        if existing:
            plan = existing[0]
            return {
                "decision_id": decision.id,
                "plan_id": plan.id,
                "status": plan.status,
                "auto_executed": False,
                "reason": "Execution plan already exists",
            }

        # Build plan from approved decision (requires approval first if not approved)
        if decision.status != "approved":
            return {
                "decision_id": decision.id,
                "plan_id": None,
                "status": "approval_required",
                "auto_executed": False,
                "reason": "Decision is not approved",
            }

        plan = self.execution_engine.create_plan(decision.id, actor=actor)
        if plan is None:
            return {
                "decision_id": decision.id,
                "plan_id": None,
                "status": "failed",
                "auto_executed": False,
                "reason": "Could not create execution plan",
            }

        # Evaluate policy against the plan
        policy_results = self.policy_engine.evaluate_plan(plan)
        policy = policy_results[0] if policy_results else None
        if policy is None or not policy.allowed:
            return {
                "decision_id": decision.id,
                "plan_id": plan.id,
                "status": plan.status,
                "auto_executed": False,
                "policy": policy.to_dict() if policy else None,
                "reason": policy.reason if policy else "No policy evaluation",
            }

        if not policy.auto_approve:
            return {
                "decision_id": decision.id,
                "plan_id": plan.id,
                "status": plan.status,
                "auto_executed": False,
                "policy": policy.to_dict(),
                "reason": f"Policy requires {policy.approval_authority} approval",
            }

        # Auto-execute
        result = self.execution_engine.execute(plan.id, actor=actor, marketplace_fn=marketplace_fn)
        return {
            "decision_id": decision.id,
            "plan_id": plan.id,
            "status": result.get("status"),
            "auto_executed": result.get("success", False),
            "policy": policy.to_dict(),
            "step_results": result.get("step_results", []),
            "reason": "Auto-executed under policy",
        }

    def process_decision_id(
        self,
        decision_id: str,
        actor: Optional[str] = None,
        marketplace_fn: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Convenience wrapper that loads the decision and processes it."""
        decision = self.session.query(Decision).filter_by(id=decision_id).first()
        if decision is None:
            return {
                "decision_id": decision_id,
                "plan_id": None,
                "status": "failed",
                "auto_executed": False,
                "reason": "Decision not found",
            }
        return self.process_decision(decision, actor=actor, marketplace_fn=marketplace_fn)
