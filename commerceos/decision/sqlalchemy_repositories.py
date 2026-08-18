"""SQLAlchemy implementations of Decision Engine repositories."""

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from commerceos.decision.models import Decision, DecisionEvidence, DecisionHistory
from commerceos.decision.repositories import (
    DecisionEvidenceRepository,
    DecisionHistoryRepository,
    DecisionRepository,
    DecisionUnitOfWork,
)


class SQLAlchemyDecisionRepository(DecisionRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, decision: Decision) -> Decision:
        self.session.add(decision)
        self.session.flush()
        return decision

    def save_many(self, decisions: List[Decision]) -> List[Decision]:
        for decision in decisions:
            self.session.add(decision)
        self.session.flush()
        return decisions

    def get(self, decision_id: str) -> Optional[Decision]:
        return self.session.query(Decision).filter_by(id=decision_id).first()

    def list(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Decision]:
        query = self.session.query(Decision).order_by(Decision.created_at.desc())
        if status:
            query = query.filter_by(status=status)
        if category:
            query = query.filter_by(category=category)
        if severity:
            query = query.filter_by(severity=severity)
        return query.limit(limit).all()

    def get_open(self, category: Optional[str] = None, limit: int = 100) -> List[Decision]:
        query = self.session.query(Decision).filter_by(status="proposed")
        if category:
            query = query.filter_by(category=category)
        return query.order_by(Decision.created_at.desc()).limit(limit).all()

    def get_history(self, decision_id: str) -> List[DecisionHistory]:
        return (
            self.session.query(DecisionHistory)
            .filter_by(decision_id=decision_id)
            .order_by(DecisionHistory.changed_at.desc())
            .all()
        )


class SQLAlchemyDecisionEvidenceRepository(DecisionEvidenceRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, evidence: DecisionEvidence) -> DecisionEvidence:
        self.session.add(evidence)
        self.session.flush()
        return evidence

    def save_many(self, evidence: List[DecisionEvidence]) -> List[DecisionEvidence]:
        for item in evidence:
            self.session.add(item)
        self.session.flush()
        return evidence

    def list_for_decision(self, decision_id: str) -> List[DecisionEvidence]:
        return self.session.query(DecisionEvidence).filter_by(decision_id=decision_id).all()


class SQLAlchemyDecisionHistoryRepository(DecisionHistoryRepository):
    def __init__(self, session: Session):
        self.session = session

    def record(self, entry: DecisionHistory) -> DecisionHistory:
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_for_decision(self, decision_id: str) -> List[DecisionHistory]:
        return (
            self.session.query(DecisionHistory)
            .filter_by(decision_id=decision_id)
            .order_by(DecisionHistory.changed_at.desc())
            .all()
        )


class SQLAlchemyDecisionUnitOfWork(DecisionUnitOfWork):
    def __init__(self, session: Session):
        self.session = session
        self._decisions = SQLAlchemyDecisionRepository(session)
        self._evidence = SQLAlchemyDecisionEvidenceRepository(session)
        self._history = SQLAlchemyDecisionHistoryRepository(session)

    def __enter__(self) -> "SQLAlchemyDecisionUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def decisions(self) -> DecisionRepository:
        return self._decisions

    def evidence(self) -> DecisionEvidenceRepository:
        return self._evidence

    def history(self) -> DecisionHistoryRepository:
        return self._history

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


@contextmanager
def sqlalchemy_decision_uow(session: Session):
    uow = SQLAlchemyDecisionUnitOfWork(session)
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
