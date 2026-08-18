"""Decision Engine approval workflow.

No automatic approval. State transitions are explicit and audited.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import Optional

from commerceos.decision.constants import DecisionStatus, can_transition
from commerceos.decision.models import Decision, DecisionHistory
from commerceos.decision.repositories import DecisionUnitOfWork


class ApprovalWorkflow:
    """Manages the lifecycle of a Decision."""

    def __init__(self, uow: DecisionUnitOfWork):
        self.uow = uow

    def _record(self, decision: Decision, old_status: Optional[str], new_status: str, changed_by: Optional[str], notes: Optional[str]) -> None:
        with self.uow:
            self.uow.history().record(
                DecisionHistory(
                    decision_id=decision.id,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=changed_by,
                    notes=notes,
                )
            )

    def approve(self, decision_id: str, changed_by: Optional[str] = None, notes: Optional[str] = None) -> Optional[Decision]:
        with self.uow:
            decision = self.uow.decisions().get(decision_id)
            if decision is None:
                return None
            old_status = decision.status
            new_status = DecisionStatus.APPROVED.value
            if not can_transition(DecisionStatus(old_status), DecisionStatus(new_status)):
                raise ValueError(f"Cannot approve a decision in status {old_status}")
            decision.status = new_status
            decision.approved_at = utc_now()
            self.uow.decisions().save(decision)

        self._record(decision, old_status, new_status, changed_by, notes)
        return decision

    def reject(self, decision_id: str, changed_by: Optional[str] = None, notes: Optional[str] = None) -> Optional[Decision]:
        with self.uow:
            decision = self.uow.decisions().get(decision_id)
            if decision is None:
                return None
            old_status = decision.status
            new_status = DecisionStatus.REJECTED.value
            if not can_transition(DecisionStatus(old_status), DecisionStatus(new_status)):
                raise ValueError(f"Cannot reject a decision in status {old_status}")
            decision.status = new_status
            decision.rejected_at = utc_now()
            self.uow.decisions().save(decision)

        self._record(decision, old_status, new_status, changed_by, notes)
        return decision

    def expire(self, decision_id: str, changed_by: Optional[str] = None, notes: Optional[str] = None) -> Optional[Decision]:
        with self.uow:
            decision = self.uow.decisions().get(decision_id)
            if decision is None:
                return None
            old_status = decision.status
            new_status = DecisionStatus.EXPIRED.value
            if not can_transition(DecisionStatus(old_status), DecisionStatus(new_status)):
                raise ValueError(f"Cannot expire a decision in status {old_status}")
            decision.status = new_status
            decision.expires_at = utc_now()
            self.uow.decisions().save(decision)

        self._record(decision, old_status, new_status, changed_by, notes)
        return decision

    def record_execution(self, decision_id: str, changed_by: Optional[str] = None, notes: Optional[str] = None) -> Optional[Decision]:
        with self.uow:
            decision = self.uow.decisions().get(decision_id)
            if decision is None:
                return None
            old_status = decision.status
            new_status = DecisionStatus.EXECUTED.value
            if not can_transition(DecisionStatus(old_status), DecisionStatus(new_status)):
                raise ValueError(f"Cannot record execution for a decision in status {old_status}")
            decision.status = new_status
            decision.executed_at = utc_now()
            self.uow.decisions().save(decision)

        self._record(decision, old_status, new_status, changed_by, notes)
        return decision
