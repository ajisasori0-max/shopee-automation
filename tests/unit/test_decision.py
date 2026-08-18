"""Unit tests for the Decision Engine."""

import pytest

from commerceos.decision.approval import ApprovalWorkflow
from commerceos.decision.constants import (
    DecisionCategory,
    DecisionConfidence,
    DecisionSeverity,
    DecisionStatus,
    can_transition,
    severity_rank,
    worst_severity,
)
from commerceos.decision.dashboard import DecisionDashboard, allowed_transitions
from commerceos.decision.estimators.impact import (
    estimate_advertising_impact,
    estimate_finance_debt_impact,
    estimate_inventory_reorder_impact,
    estimate_pricing_impact,
)
from commerceos.decision.models import Decision, DecisionEvidence, DecisionHistory
from commerceos.decision.recommendation import Recommendation
from commerceos.decision.rules.advertising import AdvertisingRules
from commerceos.decision.rules.finance import FinanceRules
from commerceos.decision.rules.inventory import InventoryRules
from commerceos.decision.rules.pricing import PricingRules


class TestStatusTransitions:
    def test_proposed_to_approved(self):
        assert can_transition(DecisionStatus.PROPOSED, DecisionStatus.APPROVED) is True

    def test_proposed_to_executed_invalid(self):
        assert can_transition(DecisionStatus.PROPOSED, DecisionStatus.EXECUTED) is False

    def test_approved_to_executed(self):
        assert can_transition(DecisionStatus.APPROVED, DecisionStatus.EXECUTED) is True

    def test_rejected_is_terminal(self):
        assert can_transition(DecisionStatus.REJECTED, DecisionStatus.APPROVED) is False

    def test_allowed_transitions_helper(self):
        assert "approved" in allowed_transitions("proposed")
        assert "executed" in allowed_transitions("approved")
        assert allowed_transitions("executed") == []


class TestSeverityRanking:
    def test_worst_severity(self):
        assert worst_severity([DecisionSeverity.WARNING, DecisionSeverity.HIGH]) == DecisionSeverity.HIGH

    def test_severity_rank_order(self):
        assert severity_rank(DecisionSeverity.INFO) < severity_rank(DecisionSeverity.HIGH)


class TestRecommendation:
    def test_to_dict(self):
        rec = Recommendation(
            category=DecisionCategory.ADVERTISING.value,
            severity=DecisionSeverity.HIGH.value,
            title="T",
            description="D",
            rationale="R",
            recommended_action="A",
            expected_impact={"x": 1},
            confidence=DecisionConfidence.HIGH.value,
            evidence=[],
        )
        d = rec.to_dict()
        assert d["category"] == "advertising"
        assert d["confidence"] == "high"


class TestAdvertisingRules:
    def test_roas_critical(self):
        rule = AdvertisingRules()
        recs = rule.evaluate(
            insights=[{"category": "advertising", "title": "ROAS fell", "explanation": "ROAS 0.5"}],
            kpis={"roas": 0.5},
        )
        assert len(recs) == 1
        assert recs[0].severity == DecisionSeverity.CRITICAL.value

    def test_roas_high(self):
        rule = AdvertisingRules()
        recs = rule.evaluate(
            insights=[{"category": "advertising", "title": "ROAS low", "explanation": "ROAS 1.5"}],
            kpis={"roas": 1.5},
        )
        assert len(recs) == 1
        assert recs[0].severity == DecisionSeverity.HIGH.value

    def test_spend_surge(self):
        rule = AdvertisingRules()
        recs = rule.evaluate(
            insights=[],
            kpis={"ad_spend": 150, "ad_spend_baseline": 100},
        )
        assert len(recs) == 1
        assert recs[0].category == DecisionCategory.ADVERTISING.value


class TestPricingRules:
    def test_margin_pressure(self):
        rule = PricingRules()
        recs = rule.evaluate(insights=[], kpis={"gross_margin_pct": 0.05})
        assert len(recs) == 1
        assert recs[0].category == DecisionCategory.PRICING.value

    def test_aov_drop(self):
        rule = PricingRules()
        recs = rule.evaluate(insights=[], kpis={"aov": 80, "aov_baseline": 100})
        assert len(recs) == 1


class TestInventoryRules:
    def test_low_coverage(self):
        rule = InventoryRules()
        recs = rule.evaluate(insights=[], kpis={"inventory_coverage_days": 3})
        assert len(recs) == 1

    def test_zero_stock(self):
        rule = InventoryRules()
        recs = rule.evaluate(insights=[], kpis={"zero_stock_skus": 5})
        assert len(recs) == 1
        assert recs[0].severity == DecisionSeverity.HIGH.value


class TestFinanceRules:
    def test_idle_cash(self):
        rule = FinanceRules()
        recs = rule.evaluate(insights=[], kpis={"cash_balance": 15_000_000})
        assert len(recs) == 1
        assert recs[0].category == DecisionCategory.FINANCE.value

    def test_high_refund_rate(self):
        rule = FinanceRules()
        recs = rule.evaluate(insights=[], kpis={"refund_rate": 0.08})
        assert len(recs) == 1
        assert recs[0].severity == DecisionSeverity.HIGH.value

    def test_revenue_falling(self):
        rule = FinanceRules()
        recs = rule.evaluate(insights=[], kpis={"gross_sales": 80, "gross_sales_baseline": 100})
        assert len(recs) == 1


class TestImpactEstimators:
    def test_advertising_impact(self):
        impact = estimate_advertising_impact(100, 2.0, -0.20)
        assert impact["expected_cash_change"] == 20.0
        assert impact["confidence"] == DecisionConfidence.HIGH.value

    def test_pricing_impact(self):
        impact = estimate_pricing_impact(1000, 0.20, 0.05)
        assert impact["expected_revenue_change"] is not None
        assert impact["confidence"] == DecisionConfidence.MEDIUM.value

    def test_inventory_impact(self):
        impact = estimate_inventory_reorder_impact(5, 100, 7)
        assert impact["expected_revenue_change"] == 3500.0
        assert impact["expected_cash_change"] < 0

    def test_finance_debt_impact(self):
        impact = estimate_finance_debt_impact(1_000_000, 0.18)
        assert impact["expected_profit_change"] == 180_000.0
        assert impact["confidence"] == DecisionConfidence.HIGH.value


class TestApprovalWorkflow:
    def test_lifecycle_happy_path(self, sqlite_uow):
        decision = Decision(
            category=DecisionCategory.ADVERTISING.value,
            severity=DecisionSeverity.HIGH.value,
            status=DecisionStatus.PROPOSED.value,
            title="Test",
            description="D",
            rationale="R",
            recommended_action="A",
        )
        with sqlite_uow:
            sqlite_uow.decisions().save(decision)

        workflow = ApprovalWorkflow(sqlite_uow)
        approved = workflow.approve(decision.id, changed_by="user", notes="ok")
        assert approved.status == DecisionStatus.APPROVED.value

        executed = workflow.record_execution(decision.id, changed_by="user")
        assert executed.status == DecisionStatus.EXECUTED.value

        history = workflow.uow.decisions().get_history(decision.id)
        assert len(history) == 2
        assert history[0].new_status == DecisionStatus.EXECUTED.value

    def test_reject_invalid_transition(self, sqlite_uow):
        decision = Decision(
            category=DecisionCategory.ADVERTISING.value,
            severity=DecisionSeverity.HIGH.value,
            status=DecisionStatus.REJECTED.value,
            title="Test",
            description="D",
            rationale="R",
            recommended_action="A",
        )
        with sqlite_uow:
            sqlite_uow.decisions().save(decision)
        workflow = ApprovalWorkflow(sqlite_uow)
        with pytest.raises(ValueError):
            workflow.approve(decision.id)


class TestDashboard:
    def test_open_decisions(self, sqlite_uow):
        decision = Decision(
            category=DecisionCategory.INVENTORY.value,
            severity=DecisionSeverity.WARNING.value,
            status=DecisionStatus.PROPOSED.value,
            title="Stock",
            description="D",
            rationale="R",
            recommended_action="A",
        )
        with sqlite_uow:
            sqlite_uow.decisions().save(decision)
        dash = DecisionDashboard(sqlite_uow)
        open_d = dash.get_open_decisions()
        assert len(open_d) == 1
        assert open_d[0]["title"] == "Stock"

    def test_high_priority(self, sqlite_uow):
        with sqlite_uow:
            for sev in [DecisionSeverity.INFO.value, DecisionSeverity.HIGH.value]:
                sqlite_uow.decisions().save(
                    Decision(
                        category=DecisionCategory.OPERATIONS.value,
                        severity=sev,
                        status=DecisionStatus.PROPOSED.value,
                        title=f"{sev}",
                        description="D",
                        rationale="R",
                        recommended_action="A",
                    )
                )
        dash = DecisionDashboard(sqlite_uow)
        high = dash.get_high_priority(limit=1)
        assert high[0]["severity"] == DecisionSeverity.HIGH.value

    def test_decision_summary(self, sqlite_uow):
        with sqlite_uow:
            sqlite_uow.decisions().save(
                Decision(
                    category=DecisionCategory.FINANCE.value,
                    severity=DecisionSeverity.NOTICE.value,
                    status=DecisionStatus.PROPOSED.value,
                    title="Cash",
                    description="D",
                    rationale="R",
                    recommended_action="A",
                )
            )
        dash = DecisionDashboard(sqlite_uow)
        summary = dash.get_decision_summary()
        assert summary["counts_by_status"]["proposed"] == 1
        assert "finance" in summary["categories"]

    def test_decision_not_found(self, sqlite_uow):
        dash = DecisionDashboard(sqlite_uow)
        assert dash.get_decision("missing") is None

    def test_decision_history(self, sqlite_uow):
        decision = Decision(
            category=DecisionCategory.ADVERTISING.value,
            severity=DecisionSeverity.HIGH.value,
            status=DecisionStatus.PROPOSED.value,
            title="Ad",
            description="D",
            rationale="R",
            recommended_action="A",
        )
        with sqlite_uow:
            sqlite_uow.decisions().save(decision)
            sqlite_uow.history().record(
                DecisionHistory(
                    decision_id=decision.id,
                    old_status=None,
                    new_status=DecisionStatus.PROPOSED.value,
                    changed_by="system",
                    notes="created",
                )
            )
        dash = DecisionDashboard(sqlite_uow)
        hist = dash.get_decision_history(decision.id)
        assert len(hist) == 1
        assert hist[0]["new_status"] == DecisionStatus.PROPOSED.value
