"""Tests for closed-loop outcome tracking."""

import os

import pytest

from commerceos.closed_loop.service import OutcomeTracker
from commerceos.decision.constants import DecisionStatus
from commerceos.decision.models import Decision
from commerceos.execution.models import ExecutionPlan
from commerceos.platform.database.connection import create_all, get_session, reset_engine


@pytest.fixture
def closed_loop_session():
    reset_engine()
    db_path = "test_closed_loop_unit.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    vault_dir = "test_closed_loop_unit_vault"
    if os.path.exists(vault_dir):
        import shutil
        shutil.rmtree(vault_dir)
    db_url = f"sqlite:///{db_path}"
    create_all(db_url)
    session = get_session(db_url)
    yield session
    session.close()
    reset_engine()
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(vault_dir):
        import shutil
        shutil.rmtree(vault_dir)


@pytest.fixture
def seed_decision_and_plan(closed_loop_session):
    decision = Decision(
        category="revenue",
        severity="high",
        title="Test budget increase",
        description="Increase campaign budget by 20%.",
        rationale="ROAS is above target.",
        recommended_action="Increase budget.",
        expected_impact={"roas": 2.0, "revenue": 1.2},
        status=DecisionStatus.APPROVED.value,
    )
    closed_loop_session.add(decision)
    closed_loop_session.flush()

    plan = ExecutionPlan(
        decision_id=decision.id,
        action_type="ads_budget",
        status="succeeded",
        payload={"budget_delta": 0.2},
    )
    closed_loop_session.add(plan)
    closed_loop_session.flush()
    return decision, plan


def test_capture_execution_feedback(closed_loop_session, seed_decision_and_plan):
    _, plan = seed_decision_and_plan
    tracker = OutcomeTracker(session=closed_loop_session)
    outcome = tracker.capture_execution_feedback(
        execution_plan_id=plan.id,
        success=True,
        impact={"roas": 2.18, "revenue": 1.15},
    )
    assert outcome.decision_id == plan.decision_id
    assert outcome.execution_plan_id == plan.id
    assert outcome.success is True
    assert outcome.impact_score is not None
    assert outcome.impact_score > 0


def test_record_outcome(closed_loop_session, seed_decision_and_plan):
    decision, _ = seed_decision_and_plan
    tracker = OutcomeTracker(session=closed_loop_session)
    outcome = tracker.record(
        decision_id=decision.id,
        actual_outcome={"roas": 2.1},
        expected_outcome={"roas": 2.0},
        success=True,
        impact_score=1.05,
        lessons=["Lesson one"],
    )
    assert outcome.success is True
    assert outcome.lessons == ["Lesson one"]

    tracker.update_lessons(outcome.id, ["Lesson one", "Lesson two"])
    from commerceos.closed_loop.models import DecisionOutcome

    refreshed = closed_loop_session.query(DecisionOutcome).filter_by(id=outcome.id).first()
    assert "Lesson one" in refreshed.lessons
    assert "Lesson two" in refreshed.lessons


def test_promote_to_memory_only_for_success(closed_loop_session, seed_decision_and_plan):
    _, plan = seed_decision_and_plan
    tracker = OutcomeTracker(session=closed_loop_session)

    success = tracker.capture_execution_feedback(plan.id, success=True, impact={"roas": 2.2})
    memory = tracker.promote_to_memory(success.id)
    assert memory is not None
    assert "note_id" in memory

    failed = tracker.capture_execution_feedback(plan.id, success=False, impact={"roas": 1.5})
    memory_failed = tracker.promote_to_memory(failed.id)
    assert memory_failed is None


def test_compute_impact_score_no_comparable_metrics(closed_loop_session):
    tracker = OutcomeTracker(session=closed_loop_session)
    score = tracker._compute_impact_score({"foo": 1}, {"foo": 1})
    assert score is None
