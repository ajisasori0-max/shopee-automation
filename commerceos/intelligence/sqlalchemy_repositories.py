"""SQLAlchemy implementations of Intelligence repositories."""

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from commerceos.intelligence.models import Insight, TrendSnapshot
from commerceos.intelligence.repositories import (
    InsightRepository,
    IntelligenceUnitOfWork,
    TrendSnapshotRepository,
)


class SQLAlchemyInsightRepository(InsightRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, insight: Insight) -> Insight:
        self.session.add(insight)
        self.session.flush()
        return insight

    def save_many(self, insights: List[Insight]) -> List[Insight]:
        for insight in insights:
            self.session.add(insight)
        self.session.flush()
        return insights

    def list(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Insight]:
        query = self.session.query(Insight).order_by(Insight.created_at.desc())
        if category:
            query = query.filter_by(category=category)
        if severity:
            query = query.filter_by(severity=severity)
        if since:
            query = query.filter(Insight.created_at >= since)
        return query.limit(limit).all()

    def latest_by_category(self, limit: int = 100) -> List[Insight]:
        subquery = (
            self.session.query(
                Insight.category,
                func.max(Insight.created_at).label("max_created_at"),
            )
            .group_by(Insight.category)
            .subquery()
        )
        return (
            self.session.query(Insight)
            .join(
                subquery,
                (Insight.category == subquery.c.category)
                & (Insight.created_at == subquery.c.max_created_at),
            )
            .order_by(Insight.category)
            .limit(limit)
            .all()
        )

    def acknowledge(self, insight_id: str) -> Optional[Insight]:
        insight = self.session.query(Insight).filter_by(id=insight_id).first()
        if insight is None:
            return None
        insight.acknowledged = True
        self.session.flush()
        return insight


class SQLAlchemyTrendSnapshotRepository(TrendSnapshotRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, snapshot: TrendSnapshot) -> TrendSnapshot:
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def save_many(self, snapshots: List[TrendSnapshot]) -> List[TrendSnapshot]:
        for snapshot in snapshots:
            self.session.add(snapshot)
        self.session.flush()
        return snapshots

    def list(
        self,
        metric: Optional[str] = None,
        period: Optional[str] = None,
        limit: int = 100,
    ) -> List[TrendSnapshot]:
        query = self.session.query(TrendSnapshot).order_by(TrendSnapshot.generated_at.desc())
        if metric:
            query = query.filter_by(metric=metric)
        if period:
            query = query.filter_by(period=period)
        return query.limit(limit).all()

    def latest(self, metric: str, period: str) -> Optional[TrendSnapshot]:
        return (
            self.session.query(TrendSnapshot)
            .filter_by(metric=metric, period=period)
            .order_by(TrendSnapshot.generated_at.desc())
            .first()
        )


class SQLAlchemyIntelligenceUnitOfWork(IntelligenceUnitOfWork):
    def __init__(self, session: Session):
        self.session = session
        self._insights = SQLAlchemyInsightRepository(session)
        self._trends = SQLAlchemyTrendSnapshotRepository(session)

    def __enter__(self) -> "SQLAlchemyIntelligenceUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def insights(self) -> InsightRepository:
        return self._insights

    def trends(self) -> TrendSnapshotRepository:
        return self._trends

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


@contextmanager
def sqlalchemy_intelligence_uow(session: Session):
    uow = SQLAlchemyIntelligenceUnitOfWork(session)
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
