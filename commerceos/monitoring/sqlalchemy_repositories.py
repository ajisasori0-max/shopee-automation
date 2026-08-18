"""SQLAlchemy implementations of Monitoring repositories."""
from commerceos.shared.value_objects.primitives import utc_now

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from commerceos.monitoring.models import Alert, HealthCheck, HealthSnapshot
from commerceos.monitoring.repositories import (
    AlertRepository,
    HealthCheckRepository,
    HealthSnapshotRepository,
    MonitoringUnitOfWork,
)


class SQLAlchemyHealthCheckRepository(HealthCheckRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, check: HealthCheck) -> HealthCheck:
        self.session.add(check)
        self.session.flush()
        return check

    def save_many(self, checks: List[HealthCheck]) -> List[HealthCheck]:
        for check in checks:
            self.session.add(check)
        self.session.flush()
        return checks

    def list(
        self,
        component: Optional[str] = None,
        component_instance: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[HealthCheck]:
        query = self.session.query(HealthCheck).order_by(HealthCheck.checked_at.desc())
        if component:
            query = query.filter_by(component=component)
        if component_instance:
            query = query.filter_by(component_instance=component_instance)
        if since:
            query = query.filter(HealthCheck.checked_at >= since)
        return query.limit(limit).all()

    def latest_by_component(
        self,
        component: Optional[str] = None,
        component_instance: Optional[str] = None,
    ) -> List[HealthCheck]:
        query = self.session.query(HealthCheck)
        if component:
            query = query.filter_by(component=component)
        if component_instance:
            query = query.filter_by(component_instance=component_instance)
        # Latest per component/component_instance
        subquery = (
            query.with_entities(
                HealthCheck.component,
                HealthCheck.component_instance,
                func.max(HealthCheck.checked_at).label("max_checked_at"),
            )
            .group_by(HealthCheck.component, HealthCheck.component_instance)
            .subquery()
        )
        return (
            self.session.query(HealthCheck)
            .join(
                subquery,
                (
                    (HealthCheck.component == subquery.c.component)
                    & ((HealthCheck.component_instance == subquery.c.component_instance)
                        | (HealthCheck.component_instance.is_(None) & subquery.c.component_instance.is_(None)))
                    & (HealthCheck.checked_at == subquery.c.max_checked_at)
                ),
            )
            .order_by(HealthCheck.component, HealthCheck.component_instance)
            .all()
        )


class SQLAlchemyAlertRepository(AlertRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_open(
        self,
        category: Optional[str] = None,
        component: Optional[str] = None,
        component_instance: Optional[str] = None,
    ) -> List[Alert]:
        query = self.session.query(Alert).filter_by(status="open")
        if category:
            query = query.filter_by(category=category)
        if component:
            query = query.filter_by(component=component)
        if component_instance:
            query = query.filter_by(component_instance=component_instance)
        return query.order_by(Alert.severity.desc(), Alert.first_seen.desc()).all()

    def find_matching(
        self,
        category: str,
        component: str,
        component_instance: Optional[str] = None,
    ) -> Optional[Alert]:
        query = self.session.query(Alert).filter_by(
            status="open",
            category=category,
            component=component,
        )
        if component_instance:
            query = query.filter_by(component_instance=component_instance)
        else:
            query = query.filter(Alert.component_instance.is_(None))
        return query.first()

    def save(self, alert: Alert) -> Alert:
        self.session.add(alert)
        self.session.flush()
        return alert

    def resolve(self, alert_id: str) -> Optional[Alert]:
        alert = self.session.query(Alert).filter_by(id=alert_id).first()
        if alert is None:
            return None
        alert.status = "resolved"
        alert.resolved_at = utc_now()
        self.session.flush()
        return alert

    def list_recent(self, limit: int = 50, status: Optional[str] = None) -> List[Alert]:
        query = self.session.query(Alert).order_by(Alert.last_seen.desc())
        if status:
            query = query.filter_by(status=status)
        return query.limit(limit).all()


class SQLAlchemyHealthSnapshotRepository(HealthSnapshotRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, snapshot: HealthSnapshot) -> HealthSnapshot:
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def latest(self) -> Optional[HealthSnapshot]:
        return (
            self.session.query(HealthSnapshot)
            .order_by(HealthSnapshot.generated_at.desc())
            .first()
        )

    def list(self, limit: int = 50) -> List[HealthSnapshot]:
        return (
            self.session.query(HealthSnapshot)
            .order_by(HealthSnapshot.generated_at.desc())
            .limit(limit)
            .all()
        )


class SQLAlchemyMonitoringUnitOfWork(MonitoringUnitOfWork):
    def __init__(self, session: Session):
        self.session = session
        self._health_checks = SQLAlchemyHealthCheckRepository(session)
        self._alerts = SQLAlchemyAlertRepository(session)
        self._snapshots = SQLAlchemyHealthSnapshotRepository(session)

    def __enter__(self) -> "SQLAlchemyMonitoringUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def health_checks(self) -> HealthCheckRepository:
        return self._health_checks

    def alerts(self) -> AlertRepository:
        return self._alerts

    def snapshots(self) -> HealthSnapshotRepository:
        return self._snapshots

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


@contextmanager
def sqlalchemy_monitoring_uow(session: Session):
    uow = SQLAlchemyMonitoringUnitOfWork(session)
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
