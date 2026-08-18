"""SQLAlchemy implementations of Execution Engine repositories."""

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from commerceos.execution.models import ExecutionAudit, ExecutionHistory, ExecutionPlan, ExecutionStep
from commerceos.execution.repositories import (
    ExecutionAuditRepository,
    ExecutionHistoryRepository,
    ExecutionPlanRepository,
    ExecutionStepRepository,
    ExecutionUnitOfWork,
)


class SQLAlchemyExecutionPlanRepository(ExecutionPlanRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, plan: ExecutionPlan) -> ExecutionPlan:
        self.session.add(plan)
        self.session.flush()
        return plan

    def get(self, plan_id: str) -> Optional[ExecutionPlan]:
        return (
            self.session.query(ExecutionPlan)
            .options(joinedload(ExecutionPlan.steps))
            .filter_by(id=plan_id)
            .first()
        )

    def list(
        self,
        status: Optional[str] = None,
        decision_id: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExecutionPlan]:
        query = self.session.query(ExecutionPlan).order_by(ExecutionPlan.created_at.desc())
        if status:
            query = query.filter_by(status=status)
        if decision_id:
            query = query.filter_by(decision_id=decision_id)
        if action_type:
            query = query.filter_by(action_type=action_type)
        return query.limit(limit).all()

    def get_by_decision(self, decision_id: str) -> Optional[ExecutionPlan]:
        return (
            self.session.query(ExecutionPlan)
            .filter_by(decision_id=decision_id)
            .order_by(ExecutionPlan.created_at.desc())
            .first()
        )


class SQLAlchemyExecutionStepRepository(ExecutionStepRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, step: ExecutionStep) -> ExecutionStep:
        self.session.add(step)
        self.session.flush()
        return step

    def save_many(self, steps: List[ExecutionStep]) -> List[ExecutionStep]:
        for step in steps:
            self.session.add(step)
        self.session.flush()
        return steps

    def list_for_plan(self, plan_id: str) -> List[ExecutionStep]:
        return (
            self.session.query(ExecutionStep)
            .filter_by(plan_id=plan_id)
            .order_by(ExecutionStep.step_number)
            .all()
        )


class SQLAlchemyExecutionHistoryRepository(ExecutionHistoryRepository):
    def __init__(self, session: Session):
        self.session = session

    def record(self, entry: ExecutionHistory) -> ExecutionHistory:
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_for_plan(self, plan_id: str) -> List[ExecutionHistory]:
        return (
            self.session.query(ExecutionHistory)
            .filter_by(plan_id=plan_id)
            .order_by(ExecutionHistory.changed_at.desc())
            .all()
        )


class SQLAlchemyExecutionAuditRepository(ExecutionAuditRepository):
    def __init__(self, session: Session):
        self.session = session

    def record(self, entry: ExecutionAudit) -> ExecutionAudit:
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_for_plan(self, plan_id: str) -> List[ExecutionAudit]:
        return (
            self.session.query(ExecutionAudit)
            .filter_by(plan_id=plan_id)
            .order_by(ExecutionAudit.timestamp.desc())
            .all()
        )

    def list_recent(self, limit: int = 100) -> List[ExecutionAudit]:
        return (
            self.session.query(ExecutionAudit)
            .order_by(ExecutionAudit.timestamp.desc())
            .limit(limit)
            .all()
        )


class SQLAlchemyExecutionUnitOfWork(ExecutionUnitOfWork):
    def __init__(self, session: Session):
        self.session = session
        self._plans = SQLAlchemyExecutionPlanRepository(session)
        self._steps = SQLAlchemyExecutionStepRepository(session)
        self._history = SQLAlchemyExecutionHistoryRepository(session)
        self._audit = SQLAlchemyExecutionAuditRepository(session)

    def __enter__(self) -> "SQLAlchemyExecutionUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def plans(self) -> ExecutionPlanRepository:
        return self._plans

    def steps(self) -> ExecutionStepRepository:
        return self._steps

    def history(self) -> ExecutionHistoryRepository:
        return self._history

    def audit(self) -> ExecutionAuditRepository:
        return self._audit

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


@contextmanager
def sqlalchemy_execution_uow(session: Session):
    uow = SQLAlchemyExecutionUnitOfWork(session)
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
