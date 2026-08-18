"""SOP Engine repository interfaces."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from commerceos.sop.models import SOPDefinitionRecord, SOPExecutionRecord


class SOPDefinitionRepository(ABC):
    @abstractmethod
    def save(self, record: SOPDefinitionRecord) -> SOPDefinitionRecord:
        raise NotImplementedError

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[SOPDefinitionRecord]:
        raise NotImplementedError

    @abstractmethod
    def list(self, enabled_only: bool = True, category: Optional[str] = None) -> List[SOPDefinitionRecord]:
        raise NotImplementedError


class SOPExecutionRepository(ABC):
    @abstractmethod
    def save(self, record: SOPExecutionRecord) -> SOPExecutionRecord:
        raise NotImplementedError

    @abstractmethod
    def get(self, execution_id: str) -> Optional[SOPExecutionRecord]:
        raise NotImplementedError

    @abstractmethod
    def list(self, store_id: Optional[str] = None, sop_code: Optional[str] = None, limit: int = 100) -> List[SOPExecutionRecord]:
        raise NotImplementedError

    @abstractmethod
    def latest(self, store_id: str, sop_code: str) -> Optional[SOPExecutionRecord]:
        raise NotImplementedError


class SOPUnitOfWork(ABC):
    @abstractmethod
    def definitions(self) -> SOPDefinitionRepository:
        raise NotImplementedError

    @abstractmethod
    def executions(self) -> SOPExecutionRepository:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
