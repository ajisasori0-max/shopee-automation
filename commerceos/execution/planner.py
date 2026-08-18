"""Execution plan builder.

An ExecutionPlan is immutable and created only from an APPROVED Decision.
It contains the exact action, parameters, target entity, expected outcome,
rollback strategy, retry policy, and a checksum.
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from commerceos.decision.constants import DecisionCategory
from commerceos.decision.models import Decision
from commerceos.execution.constants import ActionType, ExecutionStatus
from commerceos.execution.models import ExecutionPlan, ExecutionStep


class ExecutionPlanner:
    """Build immutable execution plans from approved decisions."""

    def plan(self, decision: Decision) -> ExecutionPlan:
        if decision.status != "approved":
            raise ValueError(f"Decision {decision.id} is not approved (status={decision.status})")

        action = self._decision_to_action(decision)
        payload = self._build_payload(decision, action)
        steps = self._build_steps(action, payload)

        plan_payload = {
            "action_type": action.value,
            "target_entity": payload.get("target_entity"),
            "parameters": payload.get("parameters", {}),
            "expected_outcome": payload.get("expected_outcome", {}),
            "rollback_strategy": payload.get("rollback_strategy", {}),
            "retry_policy": payload.get("retry_policy", {}),
        }
        payload["checksum_input"] = plan_payload
        checksum = self._checksum(payload)

        plan = ExecutionPlan(
            decision_id=decision.id,
            action_type=action.value,
            status=ExecutionStatus.PLANNED.value,
            payload=payload,
            checksum=checksum,
            metadata_={"source_decision": decision.id, "category": decision.category},
        )
        plan.steps = steps
        return plan

    def _decision_to_action(self, decision: Decision) -> ActionType:
        category = decision.category
        title = decision.title.lower()
        if category == DecisionCategory.ADVERTISING.value:
            if "pause" in title or "reduce" in title or "roas" in title:
                return ActionType.PAUSE_CAMPAIGN
            if "resume" in title:
                return ActionType.RESUME_CAMPAIGN
            if "budget" in title:
                return ActionType.ADJUST_BUDGET
            return ActionType.PAUSE_CAMPAIGN
        if category == DecisionCategory.PRICING.value:
            return ActionType.UPDATE_PRICE
        if category == DecisionCategory.INVENTORY.value:
            return ActionType.UPDATE_STOCK
        if category == DecisionCategory.FINANCE.value or category == DecisionCategory.OPERATIONS.value:
            return ActionType.RECORD_MANUAL_ADJUSTMENT
        return ActionType.RECORD_MANUAL_ADJUSTMENT

    def _build_payload(self, decision: Decision, action: ActionType) -> Dict[str, Any]:
        base = {
            "decision_id": decision.id,
            "category": decision.category,
            "severity": decision.severity,
            "title": decision.title,
            "description": decision.description,
            "recommended_action": decision.recommended_action,
            "expected_impact": decision.expected_impact,
            "confidence": decision.confidence,
            "reasoning": decision.rationale,
        }
        base["target_entity"] = self._infer_target_entity(decision, action)
        base["parameters"] = self._infer_parameters(decision, action)
        base["expected_outcome"] = {
            "metric": decision.category,
            "impact": decision.expected_impact,
        }
        base["rollback_strategy"] = self._infer_rollback_strategy(action)
        base["retry_policy"] = {
            "max_attempts": 3,
            "backoff_seconds": 5,
            "retryable_errors": ["timeout", "rate_limit", "network", "temporary"],
        }
        return base

    def _infer_target_entity(self, decision: Decision, action: ActionType) -> Dict[str, Any]:
        if action in {ActionType.PAUSE_CAMPAIGN, ActionType.RESUME_CAMPAIGN, ActionType.ADJUST_BUDGET}:
            return {"type": "campaign", "id": "shop-total"}
        if action == ActionType.UPDATE_PRICE:
            return {"type": "product", "id": None}
        if action == ActionType.UPDATE_STOCK:
            return {"type": "variant", "id": None}
        return {"type": "manual", "id": None}

    def _infer_parameters(self, decision: Decision, action: ActionType) -> Dict[str, Any]:
        if action in {ActionType.PAUSE_CAMPAIGN, ActionType.RESUME_CAMPAIGN}:
            return {"target_status": "paused" if action == ActionType.PAUSE_CAMPAIGN else "active"}
        if action == ActionType.ADJUST_BUDGET:
            return {"change_pct": -0.20}
        if action == ActionType.UPDATE_PRICE:
            return {"change_pct": 0.05}
        if action == ActionType.UPDATE_STOCK:
            return {"adjustment": 0}
        return {"notes": decision.recommended_action}

    def _infer_rollback_strategy(self, action: ActionType) -> Dict[str, Any]:
        if action == ActionType.PAUSE_CAMPAIGN:
            return {"action": "resume_campaign", "supported": True}
        if action == ActionType.RESUME_CAMPAIGN:
            return {"action": "pause_campaign", "supported": True}
        if action == ActionType.ADJUST_BUDGET:
            return {"action": "reverse_budget_change", "supported": True}
        if action == ActionType.UPDATE_PRICE:
            return {"action": "restore_price", "supported": True}
        if action == ActionType.UPDATE_STOCK:
            return {"action": "restore_stock", "supported": True}
        return {"action": "none", "supported": False}

    def _build_steps(self, action: ActionType, payload: Dict[str, Any]) -> List[ExecutionStep]:
        steps = [
            ExecutionStep(
                step_number=1,
                action=f"validate_{action.value}",
                rollback_supported=False,
            ),
            ExecutionStep(
                step_number=2,
                action=action.value,
                rollback_supported=payload.get("rollback_strategy", {}).get("supported", False),
            ),
            ExecutionStep(
                step_number=3,
                action="publish_result",
                rollback_supported=False,
            ),
        ]
        return steps

    def _checksum(self, payload: Dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
