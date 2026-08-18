"""Integration tests for the Execution Engine."""

import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from commerceos.commerce.models import KPI
from commerceos.decision.constants import DecisionCategory, DecisionSeverity, DecisionStatus
from commerceos.decision.engine import DecisionEngine, DecisionLifecycleService
from commerceos.decision.models import Decision
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.execution.constants import ActionType, ExecutionStatus
from commerceos.execution.dashboard import ExecutionDashboard
from commerceos.execution.engine import ExecutionEngine, ExecutionLifecycleService
from commerceos.execution.models import ExecutionPlan
from commerceos.execution.sqlalchemy_repositories import SQLAlchemyExecutionUnitOfWork
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.platform.database.models import new_uuid


DB_URL = "sqlite:///test_execution_integration.db"


@pytest.fixture
def sess():
    reset_engine()
    if os.path.exists("test_execution_integration.db"):
        os.remove("test_execution_integration.db")
    create_all(DB_URL)
    session = get_session(DB_URL)
    yield session
    session.close()
    reset_engine()


@pytest.fixture
def execution_uow(sess):
    return SQLAlchemyExecutionUnitOfWork(sess)


@pytest.fixture
def decision_uow(sess):
    return SQLAlchemyDecisionUnitOfWork(sess)


def _make_decision(uow, category=DecisionCategory.ADVERTISING.value, action_title="Pause campaign", status=DecisionStatus.APPROVED.value):
    decision = Decision(
        category=category,
        severity=DecisionSeverity.HIGH.value,
        status=status,
        title=action_title,
        description="D",
        rationale="R",
        recommended_action="Pause",
    )
    with uow:
        uow.decisions().save(decision)
    return decision


class TestExecutionLifecycleIntegration:
    def test_create_and_execute_plan(self, execution_uow, decision_uow, sess):
        decision = _make_decision(decision_uow)
        engine = ExecutionEngine(sess, execution_uow=execution_uow, decision_uow=decision_uow)
        plan = engine.create_plan(decision.id, actor="tester")
        assert plan is not None
        assert plan.status == ExecutionStatus.PLANNED.value

        result = engine.execute(plan.id, actor="tester")
        assert result["success"] is True
        assert result["status"] == ExecutionStatus.SUCCEEDED.value

        with execution_uow:
            loaded = execution_uow.plans().get(plan.id)
            assert loaded.status == ExecutionStatus.SUCCEEDED.value
            assert len(loaded.steps) == 3
            assert all(s.status == "succeeded" for s in loaded.steps)
            assert execution_uow.audit().list_for_plan(plan.id)

    def test_dry_run_does_not_change_status(self, execution_uow, decision_uow, sess):
        decision = _make_decision(decision_uow)
        engine = ExecutionEngine(sess, execution_uow=execution_uow, decision_uow=decision_uow)
        plan = engine.create_plan(decision.id, actor="tester")
        dry = engine.dry_run(plan.id, actor="tester")
        assert dry["success"] is True

        with execution_uow:
            loaded = execution_uow.plans().get(plan.id)
            assert loaded.status == ExecutionStatus.PLANNED.value

    def test_dashboard_api(self, execution_uow, decision_uow, sess):
        decision = _make_decision(decision_uow)
        engine = ExecutionEngine(sess, execution_uow=execution_uow, decision_uow=decision_uow)
        plan = engine.create_plan(decision.id, actor="tester")
        engine.execute(plan.id, actor="tester")

        dash = ExecutionDashboard(execution_uow)
        summary = dash.get_execution_summary()
        assert summary["counts_by_status"][ExecutionStatus.SUCCEEDED.value] == 1

        recent = dash.get_recent_executions(hours=24)
        assert len(recent) == 1

        full = dash.get_execution(plan.id)
        assert full["status"] == ExecutionStatus.SUCCEEDED.value
        assert full["steps"]
        assert full["audit"]
        assert full["history"]

    def test_cancel_and_expire(self, execution_uow, decision_uow, sess):
        decision = _make_decision(decision_uow)
        engine = ExecutionEngine(sess, execution_uow=execution_uow, decision_uow=decision_uow)
        plan = engine.create_plan(decision.id, actor="tester")

        service = ExecutionLifecycleService(execution_uow)
        cancelled = service.cancel(plan.id, actor="tester")
        assert cancelled.status == ExecutionStatus.CANCELLED.value

        # Create a new plan for expire test
        plan2 = engine.create_plan(decision.id, actor="tester")
        expired = service.expire(plan2.id, actor="tester")
        assert expired.status == ExecutionStatus.EXPIRED.value

    def test_decision_engine_to_execution_pipeline(self, execution_uow, decision_uow, sess):
        # Create a KPI so decision engine has data to evaluate
        kpi = KPI(
            id=new_uuid(),
            code="roas",
            name="ROAS",
            value=Decimal("1.2"),
            confidence=Decimal("1.0"),
            freshness=datetime.now(timezone.utc),
            organization_id="org-1",
            business_id="biz-1",
            store_id="store-1",
        )
        sess.add(kpi)
        sess.commit()

        decision_engine = DecisionEngine(sess, uow=decision_uow)
        insights = [{"category": "advertising", "title": "ROAS low", "explanation": "ROAS 1.2"}]
        result = decision_engine.refresh("store-1", insights=insights)
        assert result["decision_count"] >= 1

        # Approve the generated decision
        lifecycle = DecisionLifecycleService(decision_uow)
        decision_id = result["decisions"][0]["id"]
        lifecycle.approve(decision_id, changed_by="tester")

        # Execute via execution engine
        exec_engine = ExecutionEngine(sess, execution_uow=execution_uow, decision_uow=decision_uow)
        plan = exec_engine.create_plan(decision_id, actor="tester")
        exec_result = exec_engine.execute(plan.id, actor="tester")
        assert exec_result["success"] is True
