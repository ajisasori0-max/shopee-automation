"""SQLAlchemy-backed SOP repositories."""

from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from commerceos.sop.models import SOPDefinitionRecord, SOPExecutionRecord
from commerceos.sop.repositories import SOPDefinitionRepository, SOPExecutionRepository, SOPUnitOfWork


class SQLAlchemySOPDefinitionRepository(SOPDefinitionRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, record: SOPDefinitionRecord) -> SOPDefinitionRecord:
        self.session.add(record)
        self.session.flush()
        return record

    def get_by_code(self, code: str) -> Optional[SOPDefinitionRecord]:
        return self.session.query(SOPDefinitionRecord).filter_by(code=code).first()

    def list(self, enabled_only: bool = True, category: Optional[str] = None) -> List[SOPDefinitionRecord]:
        query = self.session.query(SOPDefinitionRecord)
        if enabled_only:
            query = query.filter_by(enabled=True)
        if category:
            query = query.filter_by(category=category)
        return query.order_by(SOPDefinitionRecord.code).all()


class SQLAlchemySOPExecutionRepository(SOPExecutionRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, record: SOPExecutionRecord) -> SOPExecutionRecord:
        self.session.add(record)
        self.session.flush()
        return record

    def get(self, execution_id: str) -> Optional[SOPExecutionRecord]:
        return self.session.query(SOPExecutionRecord).filter_by(execution_id=execution_id).first()

    def list(
        self,
        store_id: Optional[str] = None,
        sop_code: Optional[str] = None,
        limit: int = 100,
    ) -> List[SOPExecutionRecord]:
        query = self.session.query(SOPExecutionRecord).order_by(desc(SOPExecutionRecord.executed_at))
        if store_id:
            query = query.filter_by(store_id=store_id)
        if sop_code:
            query = query.filter_by(sop_code=sop_code)
        return query.limit(limit).all()

    def latest(self, store_id: str, sop_code: str) -> Optional[SOPExecutionRecord]:
        return (
            self.session.query(SOPExecutionRecord)
            .filter_by(store_id=store_id, sop_code=sop_code)
            .order_by(desc(SOPExecutionRecord.executed_at))
            .first()
        )


class SQLAlchemySOPUnitOfWork(SOPUnitOfWork):
    def __init__(self, session: Session):
        self._session = session
        self._definitions = SQLAlchemySOPDefinitionRepository(session)
        self._executions = SQLAlchemySOPExecutionRepository(session)

    def definitions(self) -> SOPDefinitionRepository:
        return self._definitions

    def executions(self) -> SOPExecutionRepository:
        return self._executions

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
