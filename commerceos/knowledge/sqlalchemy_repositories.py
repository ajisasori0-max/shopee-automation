"""SQLAlchemy implementations of Knowledge repositories."""
from commerceos.shared.value_objects.primitives import utc_now

from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from commerceos.knowledge.models import KnowledgeNote
from commerceos.knowledge.repositories import (
    KnowledgeNoteRepository,
    KnowledgeUnitOfWork,
)


class SQLAlchemyKnowledgeNoteRepository(KnowledgeNoteRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, note: KnowledgeNote) -> KnowledgeNote:
        self.session.add(note)
        self.session.flush()
        return note

    def save_many(self, notes: List[KnowledgeNote]) -> List[KnowledgeNote]:
        for note in notes:
            self.session.add(note)
        self.session.flush()
        return notes

    def get_by_note_id(self, note_id: str) -> Optional[KnowledgeNote]:
        return self.session.query(KnowledgeNote).filter_by(note_id=note_id).first()

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
        query = self.session.query(KnowledgeNote).order_by(
            KnowledgeNote.note_date.desc(), KnowledgeNote.created_at.desc()
        )
        if note_type:
            query = query.filter_by(note_type=note_type)
        if since:
            query = query.filter(KnowledgeNote.note_date >= since)
        if until:
            query = query.filter(KnowledgeNote.note_date <= until)
        if archived is True:
            query = query.filter(KnowledgeNote.archived_at.is_not(None))
        elif archived is False:
            query = query.filter(KnowledgeNote.archived_at.is_(None))
        if tags:
            for tag in tags:
                query = query.filter(KnowledgeNote.tags.contains(tag))
        if source_domain:
            query = query.filter(KnowledgeNote.source_domains.contains(source_domain))
        return query.limit(limit).all()

    def latest_by_type(self, note_type: str, limit: int = 1) -> List[KnowledgeNote]:
        return (
            self.session.query(KnowledgeNote)
            .filter_by(note_type=note_type)
            .filter(KnowledgeNote.archived_at.is_(None))
            .order_by(KnowledgeNote.note_date.desc())
            .limit(limit)
            .all()
        )

    def archive(self, note_id: str) -> Optional[KnowledgeNote]:
        note = self.get_by_note_id(note_id)
        if note is None:
            return None
        note.archived_at = utc_now()
        self.session.flush()
        return note


class SQLAlchemyKnowledgeUnitOfWork(KnowledgeUnitOfWork):
    def __init__(self, session: Session):
        self.session = session
        self._notes = SQLAlchemyKnowledgeNoteRepository(session)

    def __enter__(self) -> "SQLAlchemyKnowledgeUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def notes(self) -> KnowledgeNoteRepository:
        return self._notes

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


@contextmanager
def sqlalchemy_knowledge_uow(session: Session):
    uow = SQLAlchemyKnowledgeUnitOfWork(session)
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
