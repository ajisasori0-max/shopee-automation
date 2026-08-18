"""Knowledge repository interfaces.

Only metadata about Obsidian notes is stored. The Markdown file is the source of
truth.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List, Optional

from commerceos.knowledge.models import KnowledgeNote


class KnowledgeNoteRepository(ABC):
    """Persist and retrieve note metadata."""

    @abstractmethod
    def save(self, note: KnowledgeNote) -> KnowledgeNote:
        raise NotImplementedError

    @abstractmethod
    def save_many(self, notes: List[KnowledgeNote]) -> List[KnowledgeNote]:
        raise NotImplementedError

    @abstractmethod
    def get_by_note_id(self, note_id: str) -> Optional[KnowledgeNote]:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        note_type: Optional[str] = None,
        since: Optional[date] = None,
        until: Optional[date] = None,
        archived: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        source_domain: Optional[str] = None,
        limit: int = 100,
    ) -> List[KnowledgeNote]:
        raise NotImplementedError

    @abstractmethod
    def latest_by_type(
        self,
        note_type: str,
        limit: int = 1,
    ) -> List[KnowledgeNote]:
        raise NotImplementedError

    @abstractmethod
    def archive(self, note_id: str) -> Optional[KnowledgeNote]:
        """Mark a note as archived. Does not delete the file."""
        raise NotImplementedError


class KnowledgeUnitOfWork(ABC):
    """Boundary for atomic knowledge operations."""

    @abstractmethod
    def __enter__(self) -> "KnowledgeUnitOfWork":
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError

    @abstractmethod
    def notes(self) -> KnowledgeNoteRepository:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
