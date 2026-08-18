"""WP4.5 — Closed Operational Loop Foundation service.

Tracks decision outcomes and turns successful outcomes into organizational memory.
"""
from __future__ import annotations
from commerceos.shared.value_objects.primitives import utc_now


from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.closed_loop.models import DecisionOutcome
from commerceos.decision.models import Decision
from commerceos.execution.models import ExecutionPlan
from commerceos.knowledge.organizational_memory import OrganizationalMemory
from commerceos.knowledge.sqlalchemy_repositories import SQLAlchemyKnowledgeUnitOfWork
from commerceos.platform.database.models import new_uuid


class OutcomeTracker:
    """Record outcomes and link them to memory."""

    def __init__(
        self,
        session: Session,
        org_memory: Optional[OrganizationalMemory] = None,
        vault_dir=None,
    ):
        self.session = session
        if org_memory is None:
            from commerceos.config.settings import get_settings

            settings = get_settings()
            knowledge_uow = SQLAlchemyKnowledgeUnitOfWork(session)
            org_memory = OrganizationalMemory(
                repository=knowledge_uow.notes(),
                vault_dir=vault_dir or settings.obsidian_vault_path,
            )
        self.org_memory = org_memory

    def record(
        self,
        decision_id: str,
        actual_outcome: Dict[str, Any],
        expected_outcome: Optional[Dict[str, Any]] = None,
        execution_plan_id: Optional[str] = None,
        success: Optional[bool] = None,
        impact_score: Optional[float] = None,
        lessons: Optional[List[str]] = None,
        recorded_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> DecisionOutcome:
        """Record a new outcome for a decision."""
        outcome = DecisionOutcome(
            id=new_uuid(),
            decision_id=decision_id,
            execution_plan_id=execution_plan_id,
            recorded_at=utc_now(),
            expected_outcome=expected_outcome or {},
            actual_outcome=actual_outcome,
            success=success,
            impact_score=impact_score,
            lessons=lessons or [],
            recorded_by=recorded_by,
            notes=notes,
        )
        self.session.add(outcome)
        self.session.flush()
        return outcome

    def update_lessons(
        self,
        outcome_id: str,
        lessons: List[str],
    ) -> Optional[DecisionOutcome]:
        """Append lessons to an existing outcome."""
        outcome = self.session.query(DecisionOutcome).filter_by(id=outcome_id).first()
        if outcome is None:
            return None
        outcome.lessons = list(set(outcome.lessons + lessons))
        self.session.flush()
        return outcome

    def capture_execution_feedback(
        self,
        execution_plan_id: str,
        success: bool,
        impact: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> DecisionOutcome:
        """Capture outcome after an execution plan finishes."""
        plan = self.session.query(ExecutionPlan).filter_by(id=execution_plan_id).first()
        if plan is None:
            raise ValueError(f"ExecutionPlan {execution_plan_id} not found")

        decision = self.session.query(Decision).filter_by(id=plan.decision_id).first()
        expected = decision.expected_impact if decision else {}

        actual = dict(impact or {})
        if error:
            actual["error"] = error

        return self.record(
            decision_id=plan.decision_id,
            actual_outcome=actual,
            expected_outcome=expected,
            execution_plan_id=execution_plan_id,
            success=success,
            impact_score=self._compute_impact_score(expected, actual),
            lessons=[],
        )

    def _compute_impact_score(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> Optional[float]:
        """Simple impact ratio. Returns None if no comparable metrics."""
        comparable = []
        for key in ("roas", "revenue", "profit", "conversion_rate"):
            exp = expected.get(key)
            act = actual.get(key)
            if isinstance(exp, (int, float)) and exp != 0 and isinstance(act, (int, float)):
                comparable.append(min(act / exp, 2.0))  # cap at 2x
        if not comparable:
            return None
        return round(sum(comparable) / len(comparable), 3)

    def promote_to_memory(
        self,
        outcome_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Turn a successful outcome into a lesson note."""
        outcome = self.session.query(DecisionOutcome).filter_by(id=outcome_id).first()
        if outcome is None:
            return None
        if outcome.success is not True:
            return None

        decision = self.session.query(Decision).filter_by(id=outcome.decision_id).first()
        title = f"Outcome: {decision.title if decision else outcome.decision_id}"
        text = (
            f"Decision: {decision.title if decision else outcome.decision_id}\n"
            f"Expected: {outcome.expected_outcome}\n"
            f"Actual: {outcome.actual_outcome}\n"
            f"Impact score: {outcome.impact_score}"
        )
        note = self.org_memory.create_lesson(
            title=title,
            text=text,
            related_note_ids=[],
        )
        return {"note_id": note["note_id"], "path": note["path"]}
