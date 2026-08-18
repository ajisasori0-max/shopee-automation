"""Decision Engine dashboard read API.

Stable interface for Streamlit and other dashboard consumers. All reads go
through the Decision Unit of Work; no direct SQLAlchemy model access.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from commerceos.decision.constants import DecisionCategory, DecisionSeverity, can_transition, severity_rank, worst_severity
from commerceos.decision.models import Decision
from commerceos.decision.repositories import DecisionUnitOfWork


class DecisionDashboard:
    """Stable read-only dashboard API for the Decision Engine."""

    def __init__(self, uow: DecisionUnitOfWork):
        self.uow = uow

    def get_open_decisions(self, category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Return open (proposed) decisions, optionally filtered by category."""
        decisions = self.uow.decisions().get_open(category=category, limit=limit)
        return [_decision_to_dict(d) for d in decisions]

    def get_high_priority(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return highest-severity open decisions."""
        decisions = self.uow.decisions().get_open(limit=100)
        ranked = sorted(
            decisions,
            key=lambda d: severity_rank(d.severity),
            reverse=True,
        )
        return [_decision_to_dict(d) for d in ranked[:limit]]

    def get_decision_history(self, decision_id: str) -> List[Dict[str, Any]]:
        """Return status-change history for a decision."""
        entries = self.uow.decisions().get_history(decision_id)
        return [
            {
                "id": e.id,
                "decision_id": e.decision_id,
                "old_status": e.old_status,
                "new_status": e.new_status,
                "changed_at": e.changed_at.isoformat() if e.changed_at else None,
                "changed_by": e.changed_by,
                "notes": e.notes,
            }
            for e in entries
        ]

    def get_decision_summary(self) -> Dict[str, Any]:
        """Return aggregate counts and worst severity by category."""
        all_decisions = self.uow.decisions().list(limit=1000)
        by_status: Dict[str, int] = {}
        by_category: Dict[str, Dict[str, Any]] = {}
        for d in all_decisions:
            by_status[d.status] = by_status.get(d.status, 0) + 1
            cat = by_category.setdefault(d.category, {"count": 0, "worst_severity": DecisionSeverity.INFO})
            cat["count"] += 1
            if severity_rank(d.severity) > severity_rank(cat["worst_severity"]):
                cat["worst_severity"] = DecisionSeverity(d.severity)

        open_decisions = [d for d in all_decisions if d.status == "proposed"]
        overall_severity = worst_severity([d.severity for d in open_decisions]).value if open_decisions else DecisionSeverity.INFO.value

        return {
            "overall_severity": overall_severity,
            "counts_by_status": by_status,
            "categories": {
                cat: {
                    "count": data["count"],
                    "worst_severity": data["worst_severity"].value,
                }
                for cat, data in by_category.items()
            },
            "generated_at": utc_now().isoformat(),
        }

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Return a single decision by ID with full evidence and history."""
        decision = self.uow.decisions().get(decision_id)
        if decision is None:
            return None
        result = _decision_to_dict(decision)
        result["history"] = self.get_decision_history(decision_id)
        return result


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


def get_open_decisions(uow: DecisionUnitOfWork, category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    return DecisionDashboard(uow).get_open_decisions(category=category, limit=limit)


def get_high_priority(uow: DecisionUnitOfWork, limit: int = 5) -> List[Dict[str, Any]]:
    return DecisionDashboard(uow).get_high_priority(limit=limit)


def get_decision_history(uow: DecisionUnitOfWork, decision_id: str) -> List[Dict[str, Any]]:
    return DecisionDashboard(uow).get_decision_history(decision_id)


def get_decision_summary(uow: DecisionUnitOfWork) -> Dict[str, Any]:
    return DecisionDashboard(uow).get_decision_summary()


def get_decision(uow: DecisionUnitOfWork, decision_id: str) -> Optional[Dict[str, Any]]:
    return DecisionDashboard(uow).get_decision(decision_id)


def allowed_transitions(status: str) -> List[str]:
    """Return allowed next statuses for a given status."""
    from commerceos.decision.constants import DecisionStatus, STATUS_TRANSITIONS
    return [s.value for s in STATUS_TRANSITIONS.get(DecisionStatus(status), set())]
