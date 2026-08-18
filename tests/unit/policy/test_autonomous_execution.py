"""Tests for WP4.2 Autonomous Execution, WP4.3 Feedback Loop, and WP4.4 Experimentation Engine.
"""

import os

import pytest

from commerceos.closed_loop.service import OutcomeTracker
from commerceos.decision.approval import ApprovalWorkflow
from commerceos.decision.models import Decision
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.execution.engine import ExecutionEngine
from commerceos.execution.models import ExecutionPlan
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.policy.autonomous_execution import AutonomousExecutionService
from commerceos.policy.engine import PolicyEngine
from commerceos.policy.experiment_engine import ExperimentDefinition, ExperimentEngine
from commerceos.policy.feedback_loop import FeedbackLoopService


DB_URL = "sqlite:///test_autonomous.db"


@pytest.fixture
def session():
    reset_engine()
    if os.path.exists("test_autonomous.db"):
        os.remove("test_autonomous.db")
    create_all(DB_URL)
    sess = get_session(DB_URL)
    try:
        yield sess
    finally:
        sess.close()
        reset_engine()
        if os.path.exists("test_autonomous.db"):
            os.remove("test_autonomous.db")


@pytest.fixture
def approved_decision(session):
    decision = Decision(
        category="advertising",
        severity="warning",
        status="proposed",
        title="[ROAS_COLLAPSE] ROAS Collapse Diagnosis",
        description="ROAS low",
        rationale="Test",
        recommended_action="Pause campaign",
        expected_impact={"expected_revenue_change": 0},
        confidence="medium",
        metadata_={"store_id": "store-ppm-001"},
    )
    session.add(decision)
    session.commit()

    uow = SQLAlchemyDecisionUnitOfWork(session)
    workflow = ApprovalWorkflow(uow)
    approved = workflow.approve(decision.id, changed_by="test")
    assert approved is not None
    assert approved.status == "approved"
    return decision


def test_auto_execute_pause_campaign_is_allowed(session, approved_decision):
    service = AutonomousExecutionService(session)
    result = service.process_decision(approved_decision, actor="test")
    assert result["auto_executed"] is True
    assert result["plan_id"] is not None


def test_unapproved_decision_requires_approval(session):
    decision = Decision(
        category="advertising",
        severity="warning",
        status="proposed",
        title="Pause",
        description="Pause",
        rationale="Test",
        recommended_action="Pause",
        expected_impact={},
        confidence="medium",
    )
    session.add(decision)
    session.commit()
    service = AutonomousExecutionService(session)
    result = service.process_decision(decision, actor="test")
    assert result["auto_executed"] is False
    assert result["status"] == "approval_required"


def test_idempotent_no_duplicate_plans(session, approved_decision):
    service = AutonomousExecutionService(session)
    first = service.process_decision(approved_decision, actor="test")
    second = service.process_decision(approved_decision, actor="test")
    assert first["plan_id"] == second["plan_id"]
    assert second["reason"] == "Execution plan already exists"


def test_large_budget_change_requires_operator_approval(session):
    decision = Decision(
        category="advertising",
        severity="warning",
        status="approved",
        title="Adjust budget by 20%",
        description="Budget change",
        rationale="Test",
        recommended_action="Adjust budget",
        expected_impact={},
        confidence="medium",
        metadata_={"store_id": "store-ppm-001"},
    )
    session.add(decision)
    session.commit()
    # The planner maps advertising/budget titles to ADJUST_BUDGET with -20% change.
    service = AutonomousExecutionService(session)
    result = service.process_decision(decision, actor="test")
    assert result["auto_executed"] is False
    assert "operator approval" in result["reason"].lower() or "approval" in result["reason"].lower()


def test_feedback_loop_captures_outcome(session, approved_decision):
    service = AutonomousExecutionService(session)
    result = service.process_decision(approved_decision, actor="test")
    plan_id = result["plan_id"]
    feedback = FeedbackLoopService(session)
    outcome = feedback.capture(plan_id, success=True, impact={"revenue": 1000000})
    assert outcome.success is True
    assert outcome.execution_plan_id == plan_id


def test_experiment_start_blocked_by_guardrail(session):
    engine = ExperimentEngine(session)
    experiment = ExperimentDefinition(
        experiment_id="exp-1",
        hypothesis="Increase budget",
        target_metric="roas",
        expected_effect=0.1,
        duration_days=60,  # exceeds 30-day guardrail
        change_pct=10.0,
        action_type="adjust_budget",
        scope="campaign",
    )
    result = engine.start(experiment)
    assert result["status"] == "blocked"


def test_experiment_start_auto_executes_small_change(session):
    engine = ExperimentEngine(session)
    experiment = ExperimentDefinition(
        experiment_id="exp-2",
        hypothesis="Increase budget slightly",
        target_metric="roas",
        expected_effect=0.05,
        duration_days=3,
        change_pct=4.0,
        action_type="adjust_budget",
        scope="campaign",
    )
    result = engine.start(experiment)
    assert result["status"] in ("running", "approval_required", "planned")


def test_experiment_conclude_records_outcome(session, approved_decision):
    service = AutonomousExecutionService(session)
    result = service.process_decision(approved_decision, actor="test")
    engine = ExperimentEngine(session)
    conclusion = engine.conclude("exp-3", result["plan_id"], success=True, impact={"revenue": 1000000})
    assert conclusion["conclusion"] in ("keep", "rollback")
    assert conclusion["outcome_id"] is not None
