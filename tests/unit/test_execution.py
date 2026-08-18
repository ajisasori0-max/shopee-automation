"""Unit tests for the Execution Engine."""

import pytest

from commerceos.decision.constants import DecisionCategory, DecisionSeverity, DecisionStatus
from commerceos.decision.models import Decision
from commerceos.execution.audit import ExecutionAuditLogger
from commerceos.execution.constants import (
    ActionType,
    AuditEvent,
    ExecutionResult,
    ExecutionStatus,
    ExecutionStepStatus,
    is_retryable_error,
)
from commerceos.execution.engine import ExecutionEngine, ExecutionLifecycleService
from commerceos.execution.executors.base import (
    AdvertisingExecutor,
    FinanceExecutor,
    InventoryExecutor,
    PricingExecutor,
    get_executor,
)
from commerceos.execution.models import ExecutionHistory, ExecutionPlan, ExecutionStep
from commerceos.execution.planner import ExecutionPlanner
from commerceos.execution.retry import RetryManager
from commerceos.execution.rollback import RollbackManager
from commerceos.execution.validators import ExecutionValidator, ValidationResult


class TestConstants:
    def test_is_retryable_transient(self):
        assert is_retryable_error("timeout") is True
        assert is_retryable_error("rate_limit") is True

    def test_is_retryable_non_retryable(self):
        assert is_retryable_error("auth") is False
        assert is_retryable_error("validation") is False


class TestExecutionResult:
    def test_to_dict(self):
        r = ExecutionResult(success=True, action_type=ActionType.PAUSE_CAMPAIGN.value, entity_id="x")
        d = r.to_dict()
        assert d["success"] is True
        assert d["action_type"] == ActionType.PAUSE_CAMPAIGN.value


class TestExecutionPlanner:
    def test_plan_requires_approved(self):
        decision = Decision(
            category=DecisionCategory.ADVERTISING.value,
            severity=DecisionSeverity.HIGH.value,
            status=DecisionStatus.PROPOSED.value,
            title="Reduce advertising spend",
            description="D",
            rationale="R",
            recommended_action="Pause",
        )
        planner = ExecutionPlanner()
        with pytest.raises(ValueError):
            planner.plan(decision)

    def test_plan_advertising(self):
        decision = Decision(
            category=DecisionCategory.ADVERTISING.value,
            severity=DecisionSeverity.HIGH.value,
            status=DecisionStatus.APPROVED.value,
            title="Reduce advertising spend",
            description="D",
            rationale="R",
            recommended_action="Pause campaign",
        )
        planner = ExecutionPlanner()
        plan = planner.plan(decision)
        assert plan.action_type == ActionType.PAUSE_CAMPAIGN.value
        assert plan.checksum
        assert len(plan.steps) == 3
        assert plan.payload["rollback_strategy"]["supported"] is True

    def test_plan_pricing(self):
        decision = Decision(
            category=DecisionCategory.PRICING.value,
            severity=DecisionSeverity.HIGH.value,
            status=DecisionStatus.APPROVED.value,
            title="Review pricing",
            description="D",
            rationale="R",
            recommended_action="Raise price",
        )
        planner = ExecutionPlanner()
        plan = planner.plan(decision)
        assert plan.action_type == ActionType.UPDATE_PRICE.value


class TestValidators:
    def test_valid_approved_decision(self, sqlite_both_uows):
        with sqlite_both_uows.decision:
            decision = Decision(
                category=DecisionCategory.ADVERTISING.value,
                severity=DecisionSeverity.HIGH.value,
                status=DecisionStatus.APPROVED.value,
                title="T",
                description="D",
                rationale="R",
                recommended_action="A",
            )
            sqlite_both_uows.decision.decisions().save(decision)
            plan = ExecutionPlanner().plan(decision)
            sqlite_both_uows.execution.plans().save(plan)
        validator = ExecutionValidator(auth_valid=True, marketplace_available=True)
        result = validator.validate(decision, plan)
        assert result.ok is True

    def test_invalid_not_approved(self, sqlite_both_uows):
        with sqlite_both_uows.decision:
            decision = Decision(
                category=DecisionCategory.ADVERTISING.value,
                severity=DecisionSeverity.HIGH.value,
                status=DecisionStatus.PROPOSED.value,
                title="T",
                description="D",
                rationale="R",
                recommended_action="A",
            )
            sqlite_both_uows.decision.decisions().save(decision)
        plan = ExecutionPlan(
            decision_id=decision.id,
            action_type=ActionType.PAUSE_CAMPAIGN.value,
            status=ExecutionStatus.PLANNED.value,
            payload={},
            checksum="c",
        )
        validator = ExecutionValidator()
        result = validator.validate(decision, plan)
        assert result.ok is False
        assert "not approved" in result.errors[0]

    def test_checksum_mismatch(self, sqlite_both_uows):
        with sqlite_both_uows.decision:
            decision = Decision(
                category=DecisionCategory.ADVERTISING.value,
                severity=DecisionSeverity.HIGH.value,
                status=DecisionStatus.APPROVED.value,
                title="T",
                description="D",
                rationale="R",
                recommended_action="A",
            )
            sqlite_both_uows.decision.decisions().save(decision)
            plan = ExecutionPlanner().plan(decision)
            plan.checksum = "bad"
        validator = ExecutionValidator(auth_valid=True, marketplace_available=True)
        result = validator.validate(decision, plan)
        assert result.ok is False
        assert "checksum" in result.errors[0]


class TestExecutors:
    def test_advertising_dry_run(self):
        ex = AdvertisingExecutor()
        result = ex.dry_run({"target_status": "paused"}, {"id": "camp-1"})
        assert result.success is True
        assert "DRY RUN" in result.message

    def test_advertising_execute(self):
        ex = AdvertisingExecutor()
        result = ex.execute({"target_status": "paused"}, {"id": "camp-1"})
        assert result.success is True
        assert "paused" in result.message

    def test_advertising_rollback(self):
        ex = AdvertisingExecutor()
        result = ex.rollback({"target_status": "paused"}, {"id": "camp-1"})
        assert result.success is True

    def test_pricing_execute(self):
        ex = PricingExecutor()
        result = ex.execute({"change_pct": 0.05}, {"id": "item-1"})
        assert result.success is True

    def test_inventory_rollback(self):
        ex = InventoryExecutor()
        result = ex.rollback({"adjustment": 10}, {"id": "var-1"})
        assert result.success is True
        assert "-10" in result.message

    def test_finance_rollback_not_supported(self):
        ex = FinanceExecutor()
        result = ex.rollback({}, {})
        assert result.success is False

    def test_get_executor(self):
        assert get_executor(ActionType.PAUSE_CAMPAIGN.value) is not None
        assert get_executor("nonexistent") is None


class TestRetryManager:
    def test_success_on_first_attempt(self):
        rm = RetryManager(max_attempts=3)
        result = rm.run(lambda p, t, m: ExecutionResult(success=True, action_type="x"), {}, {}, None)
        assert result.success is True

    def test_no_retry_on_non_retryable(self):
        rm = RetryManager(max_attempts=3, backoff_seconds=0)
        calls = []

        def fail_once(p, t, m):
            calls.append(1)
            return ExecutionResult(success=False, action_type="x", error_code="validation")

        result = rm.run(fail_once, {}, {}, None)
        assert result.success is False
        assert len(calls) == 1

    def test_retry_on_transient(self):
        rm = RetryManager(max_attempts=3, backoff_seconds=0)
        attempts = []

        def fail_then_succeed(p, t, m):
            attempts.append(len(attempts) + 1)
            if len(attempts) < 2:
                return ExecutionResult(success=False, action_type="x", error_code="timeout")
            return ExecutionResult(success=True, action_type="x")

        result = rm.run(fail_then_succeed, {}, {}, None)
        assert result.success is True
        assert len(attempts) == 2


class TestAuditLogger:
    def test_log_events(self, sqlite_both_uows):
        logger = ExecutionAuditLogger(sqlite_both_uows.execution)
        with sqlite_both_uows.execution:
            plan = ExecutionPlan(
                decision_id="d-1",
                action_type=ActionType.PAUSE_CAMPAIGN.value,
                status=ExecutionStatus.PLANNED.value,
                payload={},
                checksum="c",
            )
            sqlite_both_uows.execution.plans().save(plan)
        entry = logger.started(plan.id, actor="tester")
        assert entry.event == AuditEvent.STARTED.value
        with sqlite_both_uows.execution:
            assert sqlite_both_uows.execution.audit().list_for_plan(plan.id)


class TestExecutionLifecycle:
    def test_cancel_running(self, sqlite_both_uows):
        with sqlite_both_uows.execution:
            plan = ExecutionPlan(
                decision_id="d-1",
                action_type=ActionType.PAUSE_CAMPAIGN.value,
                status=ExecutionStatus.RUNNING.value,
                payload={},
                checksum="c",
            )
            sqlite_both_uows.execution.plans().save(plan)
        service = ExecutionLifecycleService(sqlite_both_uows.execution)
        cancelled = service.cancel(plan.id, actor="tester")
        assert cancelled.status == ExecutionStatus.CANCELLED.value

    def test_expire_planned(self, sqlite_both_uows):
        with sqlite_both_uows.execution:
            plan = ExecutionPlan(
                decision_id="d-1",
                action_type=ActionType.PAUSE_CAMPAIGN.value,
                status=ExecutionStatus.PLANNED.value,
                payload={},
                checksum="c",
            )
            sqlite_both_uows.execution.plans().save(plan)
        service = ExecutionLifecycleService(sqlite_both_uows.execution)
        expired = service.expire(plan.id, actor="tester")
        assert expired.status == ExecutionStatus.EXPIRED.value


class TestExecutionEngine:
    def test_create_plan_from_approved(self, sqlite_both_uows):
        with sqlite_both_uows.decision:
            decision = Decision(
                category=DecisionCategory.ADVERTISING.value,
                severity=DecisionSeverity.HIGH.value,
                status=DecisionStatus.APPROVED.value,
                title="Pause campaign",
                description="D",
                rationale="R",
                recommended_action="Pause",
            )
            sqlite_both_uows.decision.decisions().save(decision)
        engine = ExecutionEngine(sqlite_both_uows.session, execution_uow=sqlite_both_uows.execution, decision_uow=sqlite_both_uows.decision)
        plan = engine.create_plan(decision.id, actor="tester")
        assert plan is not None
        assert plan.action_type == ActionType.PAUSE_CAMPAIGN.value

    def test_execute_success(self, sqlite_both_uows):
        with sqlite_both_uows.decision:
            decision = Decision(
                category=DecisionCategory.ADVERTISING.value,
                severity=DecisionSeverity.HIGH.value,
                status=DecisionStatus.APPROVED.value,
                title="Pause campaign",
                description="D",
                rationale="R",
                recommended_action="Pause",
            )
            sqlite_both_uows.decision.decisions().save(decision)
        engine = ExecutionEngine(sqlite_both_uows.session, execution_uow=sqlite_both_uows.execution, decision_uow=sqlite_both_uows.decision)
        plan = engine.create_plan(decision.id, actor="tester")
        assert plan is not None
        result = engine.execute(plan.id, actor="tester", skip_validation=True)
        assert result["success"] is True
        assert result["status"] == ExecutionStatus.SUCCEEDED.value

    def test_execute_validation_rejects_non_approved(self, sqlite_both_uows):
        with sqlite_both_uows.decision:
            decision = Decision(
                category=DecisionCategory.ADVERTISING.value,
                severity=DecisionSeverity.HIGH.value,
                status=DecisionStatus.PROPOSED.value,
                title="Pause campaign",
                description="D",
                rationale="R",
                recommended_action="Pause",
            )
            sqlite_both_uows.decision.decisions().save(decision)
            plan = ExecutionPlan(
                decision_id=decision.id,
                action_type=ActionType.PAUSE_CAMPAIGN.value,
                status=ExecutionStatus.PLANNED.value,
                payload={},
                checksum="c",
            )
            sqlite_both_uows.execution.plans().save(plan)
            for i in range(1, 4):
                step = ExecutionStep(
                    plan_id=plan.id,
                    step_number=i,
                    action=f"step_{i}",
                )
                sqlite_both_uows.execution.steps().save(step)
        engine = ExecutionEngine(sqlite_both_uows.session, execution_uow=sqlite_both_uows.execution, decision_uow=sqlite_both_uows.decision)
        result = engine.execute(plan.id, actor="tester")
        assert result["success"] is False

    def test_dry_run(self, sqlite_both_uows):
        with sqlite_both_uows.decision:
            decision = Decision(
                category=DecisionCategory.ADVERTISING.value,
                severity=DecisionSeverity.HIGH.value,
                status=DecisionStatus.APPROVED.value,
                title="Pause campaign",
                description="D",
                rationale="R",
                recommended_action="Pause",
            )
            sqlite_both_uows.decision.decisions().save(decision)
        engine = ExecutionEngine(sqlite_both_uows.session, execution_uow=sqlite_both_uows.execution, decision_uow=sqlite_both_uows.decision)
        plan = engine.create_plan(decision.id, actor="tester")
        assert plan is not None
        result = engine.dry_run(plan.id, actor="tester")
        assert result["success"] is True
        assert result["dry_run"] is True


class TestDashboard:
    def test_get_execution_summary(self, sqlite_both_uows):
        with sqlite_both_uows.execution:
            for status in [ExecutionStatus.PLANNED.value, ExecutionStatus.SUCCEEDED.value]:
                sqlite_both_uows.execution.plans().save(
                    ExecutionPlan(
                        decision_id="d-1",
                        action_type=ActionType.PAUSE_CAMPAIGN.value,
                        status=status,
                        payload={},
                        checksum="c",
                    )
                )
        from commerceos.execution.dashboard import ExecutionDashboard

        dash = ExecutionDashboard(sqlite_both_uows.execution)
        summary = dash.get_execution_summary()
        assert summary["total"] == 2
        assert summary["counts_by_status"][ExecutionStatus.PLANNED.value] == 1
