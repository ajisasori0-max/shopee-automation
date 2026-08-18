"""Tests for WP4.1 Policy Engine.

Covers boundary conditions, conflicting policies, missing policy, disabled policy,
rate limits, cooldown, and approval escalation.
"""

import pytest

from commerceos.policy.engine import PolicyEngine, PolicyRule, DEFAULT_POLICIES


def test_budget_5pct_auto_approved():
    engine = PolicyEngine()
    result = engine.evaluate("adjust_budget", "campaign", 4.0, absolute_change=500_000)
    assert result.allowed is True
    assert result.auto_approve is True
    assert result.approval_authority == "system"


def test_budget_15pct_requires_operator_approval():
    engine = PolicyEngine()
    result = engine.evaluate("adjust_budget", "campaign", 20.0, absolute_change=2_000_000)
    assert result.allowed is True
    assert result.auto_approve is False
    assert result.approval_authority == "operator"


def test_budget_50pct_requires_executive_approval():
    engine = PolicyEngine()
    result = engine.evaluate("adjust_budget", "campaign", 60.0, absolute_change=10_000_000)
    assert result.allowed is True
    assert result.auto_approve is False
    assert result.approval_authority == "executive"


def test_budget_absolute_limit_exceeded():
    engine = PolicyEngine()
    # 4% change is within the 5% threshold, but absolute change exceeds 1M limit.
    result = engine.evaluate("adjust_budget", "campaign", 4.0, absolute_change=2_000_000)
    assert result.allowed is False
    assert "limit" in result.reason.lower()


def test_price_3pct_auto_approved():
    engine = PolicyEngine()
    result = engine.evaluate("update_price", "sku", 2.0, absolute_change=20_000)
    assert result.allowed is True
    assert result.auto_approve is True


def test_price_10pct_requires_operator_approval():
    engine = PolicyEngine()
    result = engine.evaluate("update_price", "sku", 12.0, absolute_change=100_000)
    assert result.allowed is True
    assert result.auto_approve is False
    assert result.approval_authority == "operator"


def test_pause_campaign_auto_approved():
    engine = PolicyEngine()
    result = engine.evaluate("pause_campaign", "campaign", 0.0)
    assert result.allowed is True
    assert result.auto_approve is True


def test_missing_policy():
    engine = PolicyEngine()
    result = engine.evaluate("delete_store", "store", 100.0)
    assert result.allowed is False
    assert result.reason == "No matching policy found"


def test_disabled_policy():
    policies = [PolicyRule(action="test", scope="test", threshold_pct=0.0, risk_level="low", auto_approve=True, approval_authority="system", enabled=False)]
    engine = PolicyEngine(policies=policies)
    result = engine.evaluate("test", "test", 0.0)
    assert result.allowed is False
    assert result.reason == "No matching policy found"


def test_cooldown_blocks_repeat():
    now = __import__("datetime").datetime.utcnow()
    recent = [{"action": "adjust_budget", "scope": "campaign", "executed_at": now}]
    engine = PolicyEngine(policies=DEFAULT_POLICIES, recent_executions=recent)
    result = engine.evaluate("adjust_budget", "campaign", 4.0, absolute_change=500_000)
    assert result.allowed is False
    assert result.cooldown_remaining_minutes is not None
    assert result.cooldown_remaining_minutes > 0


def test_rate_limit_blocks_after_threshold():
    now = __import__("datetime").datetime.utcnow()
    recent = [{"action": "adjust_budget", "scope": "campaign", "executed_at": now} for _ in range(6)]
    engine = PolicyEngine(policies=DEFAULT_POLICIES, recent_executions=recent)
    result = engine.evaluate("adjust_budget", "campaign", 4.0, absolute_change=500_000)
    assert result.allowed is False
    assert result.rate_limit_remaining == 0


def test_conflicting_policy_takes_highest_threshold():
    # If multiple rules match, the one with highest threshold <= change_pct wins.
    engine = PolicyEngine()
    result = engine.evaluate("adjust_budget", "campaign", 25.0)
    assert result.approval_authority == "operator"  # 15% rule applies, not 5% or 50% (since 25 < 50)


def test_manual_adjustment_never_auto():
    engine = PolicyEngine()
    result = engine.evaluate("record_manual_adjustment", "store", 0.0)
    assert result.allowed is True
    assert result.auto_approve is False
    assert result.approval_authority == "operator"
