"""WP4.1 — Policy Engine.

Explicit, configurable policy evaluation for autonomous actions.
Policies define:
- action scope
- threshold
- risk level
- automatic vs approval-required behavior
- limits, cooldown, rate limit
- rollback requirements
- approval authority

Every policy decision is auditable. The engine is deterministic and does not
contain universal examples as hardcoded rules; examples are loaded from a default
policy set that can be overridden.
"""

from commerceos.shared.value_objects.primitives import utc_now

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PolicyRule:
    """A single policy rule for an action category."""

    action: str
    scope: str  # e.g., "campaign", "sku", "store", "global"
    threshold_pct: float
    risk_level: str  # low, medium, high, critical
    auto_approve: bool
    approval_authority: str  # system, operator, executive
    limit_value: Optional[float] = None  # absolute limit (e.g., max budget change)
    cooldown_minutes: int = 0
    rate_limit_per_hour: int = 10
    requires_rollback_plan: bool = True
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "scope": self.scope,
            "threshold_pct": self.threshold_pct,
            "risk_level": self.risk_level,
            "auto_approve": self.auto_approve,
            "approval_authority": self.approval_authority,
            "limit_value": self.limit_value,
            "cooldown_minutes": self.cooldown_minutes,
            "rate_limit_per_hour": self.rate_limit_per_hour,
            "requires_rollback_plan": self.requires_rollback_plan,
            "enabled": self.enabled,
        }


@dataclass
class PolicyEvaluation:
    """Result of evaluating a proposed action against a policy rule."""

    action: str
    scope: str
    proposed_change_pct: float
    rule: PolicyRule
    allowed: bool
    auto_approve: bool
    reason: str
    risk_level: str
    approval_authority: str
    cooldown_remaining_minutes: Optional[float] = None
    rate_limit_remaining: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "scope": self.scope,
            "proposed_change_pct": self.proposed_change_pct,
            "rule": self.rule.to_dict(),
            "allowed": self.allowed,
            "auto_approve": self.auto_approve,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "approval_authority": self.approval_authority,
            "cooldown_remaining_minutes": self.cooldown_remaining_minutes,
            "rate_limit_remaining": self.rate_limit_remaining,
            "metadata": self.metadata,
        }


DEFAULT_POLICIES = [
    PolicyRule(
        action="adjust_budget",
        scope="campaign",
        threshold_pct=5.0,
        risk_level="low",
        auto_approve=True,
        approval_authority="system",
        limit_value=1_000_000.0,
        cooldown_minutes=30,
        rate_limit_per_hour=6,
        requires_rollback_plan=True,
    ),
    PolicyRule(
        action="adjust_budget",
        scope="campaign",
        threshold_pct=15.0,
        risk_level="medium",
        auto_approve=False,
        approval_authority="operator",
        limit_value=5_000_000.0,
        cooldown_minutes=60,
        rate_limit_per_hour=4,
        requires_rollback_plan=True,
    ),
    PolicyRule(
        action="adjust_budget",
        scope="campaign",
        threshold_pct=50.0,
        risk_level="high",
        auto_approve=False,
        approval_authority="executive",
        limit_value=None,
        cooldown_minutes=240,
        rate_limit_per_hour=2,
        requires_rollback_plan=True,
    ),
    PolicyRule(
        action="update_price",
        scope="sku",
        threshold_pct=3.0,
        risk_level="low",
        auto_approve=True,
        approval_authority="system",
        limit_value=50_000.0,
        cooldown_minutes=60,
        rate_limit_per_hour=10,
        requires_rollback_plan=True,
    ),
    PolicyRule(
        action="update_price",
        scope="sku",
        threshold_pct=10.0,
        risk_level="medium",
        auto_approve=False,
        approval_authority="operator",
        limit_value=200_000.0,
        cooldown_minutes=240,
        rate_limit_per_hour=4,
        requires_rollback_plan=True,
    ),
    PolicyRule(
        action="pause_campaign",
        scope="campaign",
        threshold_pct=0.0,
        risk_level="low",
        auto_approve=True,
        approval_authority="system",
        limit_value=0.0,
        cooldown_minutes=15,
        rate_limit_per_hour=12,
        requires_rollback_plan=True,
    ),
    PolicyRule(
        action="resume_campaign",
        scope="campaign",
        threshold_pct=0.0,
        risk_level="low",
        auto_approve=True,
        approval_authority="system",
        limit_value=0.0,
        cooldown_minutes=15,
        rate_limit_per_hour=12,
        requires_rollback_plan=True,
    ),
    PolicyRule(
        action="update_stock",
        scope="variant",
        threshold_pct=0.0,
        risk_level="low",
        auto_approve=True,
        approval_authority="system",
        limit_value=0.0,
        cooldown_minutes=15,
        rate_limit_per_hour=20,
        requires_rollback_plan=True,
    ),
    PolicyRule(
        action="record_manual_adjustment",
        scope="store",
        threshold_pct=0.0,
        risk_level="low",
        auto_approve=False,
        approval_authority="operator",
        limit_value=None,
        cooldown_minutes=0,
        rate_limit_per_hour=100,
        requires_rollback_plan=False,
    ),
]


class PolicyEngine:
    """Evaluate proposed actions against policy rules and execution history."""

    def __init__(
        self,
        policies: Optional[List[PolicyRule]] = None,
        recent_executions: Optional[List[Dict[str, Any]]] = None,
    ):
        self.policies = policies or DEFAULT_POLICIES
        self.recent_executions = recent_executions or []

    def evaluate(
        self,
        action: str,
        scope: str,
        change_pct: float,
        absolute_change: Optional[float] = None,
    ) -> PolicyEvaluation:
        """Evaluate a single proposed action against matching policies."""
        matching = [
            p for p in self.policies
            if p.enabled and p.action == action and p.scope == scope
        ]
        if not matching:
            return PolicyEvaluation(
                action=action,
                scope=scope,
                proposed_change_pct=change_pct,
                rule=PolicyRule(action=action, scope=scope, threshold_pct=0.0, risk_level="unknown", auto_approve=False, approval_authority="operator"),
                allowed=False,
                auto_approve=False,
                reason="No matching policy found",
                risk_level="unknown",
                approval_authority="operator",
            )

        # Sort by threshold ascending; the highest threshold that is <= change_pct wins.
        matching.sort(key=lambda p: p.threshold_pct)
        selected = None
        for rule in matching:
            if abs(change_pct) >= rule.threshold_pct:
                selected = rule
        if selected is None:
            selected = matching[0]

        cooldown = self._check_cooldown(action, scope, selected.cooldown_minutes)
        rate = self._check_rate_limit(action, scope, selected.rate_limit_per_hour)

        # Absolute limit check
        if selected.limit_value is not None and absolute_change is not None and abs(absolute_change) > selected.limit_value:
            allowed = False
            reason = f"Absolute change {absolute_change:,.0f} exceeds policy limit {selected.limit_value:,.0f}"
        elif cooldown["remaining_minutes"] > 0:
            allowed = False
            reason = f"Cooldown active: {cooldown['remaining_minutes']:.0f} minutes remaining"
        elif rate["remaining"] <= 0:
            allowed = False
            reason = f"Rate limit reached ({selected.rate_limit_per_hour}/hour)"
        else:
            allowed = True
            reason = "Policy allows action"

        return PolicyEvaluation(
            action=action,
            scope=scope,
            proposed_change_pct=change_pct,
            rule=selected,
            allowed=allowed,
            auto_approve=allowed and selected.auto_approve,
            reason=reason,
            risk_level=selected.risk_level,
            approval_authority=selected.approval_authority,
            cooldown_remaining_minutes=cooldown["remaining_minutes"] if cooldown["remaining_minutes"] > 0 else None,
            rate_limit_remaining=rate["remaining"] if rate["remaining"] >= 0 else None,
            metadata={
                "rate_limit_per_hour": selected.rate_limit_per_hour,
                "absolute_change": absolute_change,
            },
        )

    def evaluate_plan(self, plan: Any) -> List[PolicyEvaluation]:
        """Evaluate an ExecutionPlan's action/parameters against policies."""
        action = plan.action_type
        payload = plan.payload or {}
        target = payload.get("target_entity", {})
        scope = target.get("type", "global")
        parameters = payload.get("parameters", {})
        change_pct = abs(parameters.get("change_pct", 0.0)) * 100
        absolute_change = parameters.get("absolute_change")
        return [self.evaluate(action, scope, change_pct, absolute_change)]

    def _check_cooldown(self, action: str, scope: str, cooldown_minutes: int) -> Dict[str, Any]:
        if cooldown_minutes <= 0:
            return {"remaining_minutes": 0.0}
        cutoff = utc_now() - timedelta(minutes=cooldown_minutes)
        recent = []
        for e in self.recent_executions:
            if e.get("action") == action and e.get("scope") == scope:
                ts = e.get("executed_at")
                if isinstance(ts, datetime):
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts > cutoff:
                        recent.append(e)
        if not recent:
            return {"remaining_minutes": 0.0}
        latest = max(e.get("executed_at", datetime.min) for e in recent)
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        remaining = cooldown_minutes - (utc_now() - latest).total_seconds() / 60
        return {"remaining_minutes": max(0.0, remaining)}

    def _check_rate_limit(self, action: str, scope: str, limit_per_hour: int) -> Dict[str, Any]:
        if limit_per_hour <= 0:
            return {"remaining": 999}
        cutoff = utc_now() - timedelta(hours=1)
        count = 0
        for e in self.recent_executions:
            if e.get("action") == action and e.get("scope") == scope:
                ts = e.get("executed_at")
                if isinstance(ts, datetime):
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts > cutoff:
                        count += 1
        return {"remaining": max(0, limit_per_hour - count), "count": count}

    def list_policies(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.policies]
