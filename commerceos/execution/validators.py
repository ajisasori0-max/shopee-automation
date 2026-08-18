"""Execution Engine validators.

Checks preconditions before any marketplace-facing action is taken.
"""

from typing import Any, Dict, List, Optional

from commerceos.decision.models import Decision
from commerceos.execution.models import ExecutionPlan


class ValidationResult:
    def __init__(self, ok: bool, errors: Optional[List[str]] = None, warnings: Optional[List[str]] = None):
        self.ok = ok
        self.errors = errors if errors is not None else []
        self.warnings = warnings if warnings is not None else []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class ExecutionValidator:
    """Validate execution preconditions deterministically."""

    def __init__(
        self,
        connector_health: Optional[Dict[str, Any]] = None,
        auth_valid: Optional[bool] = None,
        marketplace_available: Optional[bool] = None,
    ):
        self.connector_health = connector_health or {}
        self.auth_valid = auth_valid
        self.marketplace_available = marketplace_available

    def validate(
        self,
        decision: Decision,
        plan: ExecutionPlan,
        existing_plans: Optional[List[ExecutionPlan]] = None,
    ) -> ValidationResult:
        errors = []
        warnings = []

        if decision.status != "approved":
            errors.append(f"Decision not approved (status={decision.status})")

        if plan.status not in {"planned", "ready"}:
            errors.append(f"Plan not executable (status={plan.status})")

        expected_checksum = self._compute_checksum(plan)
        if plan.checksum != expected_checksum:
            errors.append("Plan checksum mismatch — plan may have been tampered with")

        if existing_plans:
            for p in existing_plans:
                if p.status == "running" and p.decision_id == decision.id:
                    errors.append("Duplicate execution: another plan is already running for this decision")

        if self.auth_valid is False:
            errors.append("Authentication invalid")
        if self.marketplace_available is False:
            errors.append("Marketplace unavailable")

        health_status = self.connector_health.get("status")
        if health_status and health_status not in {"healthy", "degraded"}:
            errors.append(f"Connector health is {health_status}")

        return ValidationResult(ok=not errors, errors=errors, warnings=warnings)

    def _compute_checksum(self, plan: ExecutionPlan) -> str:
        from commerceos.execution.planner import ExecutionPlanner
        return ExecutionPlanner()._checksum(plan.payload)
