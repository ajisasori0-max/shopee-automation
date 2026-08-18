"""Tests for Knowledge layer models and repositories."""

import os
from datetime import date, datetime, timezone

import pytest

from commerceos.knowledge.models import KnowledgeNote
from commerceos.knowledge.repositories import KnowledgeNoteRepository
from commerceos.knowledge.sqlalchemy_repositories import (
    SQLAlchemyKnowledgeUnitOfWork,
    sqlalchemy_knowledge_uow,
)
from commerceos.platform.database.connection import create_all, get_session, reset_engine


@pytest.fixture
def knowledge_uow():
    db_url = "sqlite:///test_knowledge_unit.db"
    reset_engine()
    if os.path.exists("test_knowledge_unit.db"):
        os.remove("test_knowledge_unit.db")
    create_all(db_url)
    session = get_session(db_url)
    uow = SQLAlchemyKnowledgeUnitOfWork(session)
    try:
        yield uow
    finally:
        session.close()
        reset_engine()
        if os.path.exists("test_knowledge_unit.db"):
            os.remove("test_knowledge_unit.db")


def _make_note(note_id: str, note_type: str, note_date: date, tags=None, source_domains=None) -> KnowledgeNote:
    return KnowledgeNote(
        note_id=note_id,
        note_type=note_type,
        note_date=note_date,
        title=f"{note_type.title()} {note_id}",
        path=f"10 COO/{note_type.title()}/{note_id}.md",
        tags=tags or ["daily", "business"],
        links=[],
        source_domains=source_domains or ["intelligence", "monitoring"],
    )


def test_knowledge_note_defaults_and_dict(knowledge_uow):
    note = _make_note("kn-2026-07-29", "daily", date(2026, 7, 29))
    with knowledge_uow:
        saved = knowledge_uow.notes().save(note)
    assert saved.id is not None
    assert saved.is_archived() is False
    d = saved.to_dict()
    assert d["note_id"] == "kn-2026-07-29"
    assert d["note_type"] == "daily"
    assert d["archived_at"] is None


def test_get_by_note_id(knowledge_uow):
    note = _make_note("kn-2026-07-29", "daily", date(2026, 7, 29))
    with knowledge_uow:
        knowledge_uow.notes().save(note)
    found = knowledge_uow.notes().get_by_note_id("kn-2026-07-29")
    assert found is not None
    assert found.title == "Daily kn-2026-07-29"


def test_list_by_type_and_date_range(knowledge_uow):
    with knowledge_uow:
        knowledge_uow.notes().save_many([
            _make_note("kn-2026-07-28", "daily", date(2026, 7, 28)),
            _make_note("kn-2026-07-29", "daily", date(2026, 7, 29)),
            _make_note("kn-2026-W30", "weekly", date(2026, 7, 27)),
        ])
    dailies = knowledge_uow.notes().list(note_type="daily", limit=10)
    assert len(dailies) == 2
    assert dailies[0].note_date == date(2026, 7, 29)

    weeklies = knowledge_uow.notes().list(
        since=date(2026, 7, 1), until=date(2026, 7, 31), limit=10
    )
    assert len(weeklies) == 3


def test_list_by_tag_and_source_domain(knowledge_uow):
    with knowledge_uow:
        knowledge_uow.notes().save_many([
            _make_note("kn-1", "daily", date(2026, 7, 29), tags=["revenue"], source_domains=["intelligence"]),
            _make_note("kn-2", "daily", date(2026, 7, 29), tags=["inventory"], source_domains=["monitoring"]),
        ])
    revenue = knowledge_uow.notes().list(tags=["revenue"], limit=10)
    assert len(revenue) == 1
    assert revenue[0].note_id == "kn-1"

    monitoring = knowledge_uow.notes().list(source_domain="monitoring", limit=10)
    assert len(monitoring) == 1
    assert monitoring[0].note_id == "kn-2"


def test_archive_preserves_record(knowledge_uow):
    note = _make_note("kn-2026-07-29", "daily", date(2026, 7, 29))
    with knowledge_uow:
        knowledge_uow.notes().save(note)
    archived = knowledge_uow.notes().archive("kn-2026-07-29")
    assert archived is not None
    assert archived.is_archived() is True

    active = knowledge_uow.notes().list(archived=False, limit=10)
    assert len(active) == 0

    all_notes = knowledge_uow.notes().list(archived=True, limit=10)
    assert len(all_notes) == 1


def test_latest_by_type(knowledge_uow):
    with knowledge_uow:
        knowledge_uow.notes().save_many([
            _make_note("kn-2026-07-28", "daily", date(2026, 7, 28)),
            _make_note("kn-2026-07-29", "daily", date(2026, 7, 29)),
            _make_note("kn-2026-07-27", "daily", date(2026, 7, 27)),
        ])
    latest = knowledge_uow.notes().latest_by_type("daily", limit=1)
    assert len(latest) == 1
    assert latest[0].note_date == date(2026, 7, 29)

    top_2 = knowledge_uow.notes().latest_by_type("daily", limit=2)
    assert len(top_2) == 2
    assert [n.note_date for n in top_2] == [date(2026, 7, 29), date(2026, 7, 28)]


def test_context_manager_commit(knowledge_uow):
    note = _make_note("kn-cm-1", "daily", date(2026, 7, 29))
    with sqlalchemy_knowledge_uow(knowledge_uow.session):
        knowledge_uow.notes().save(note)
    found = knowledge_uow.notes().get_by_note_id("kn-cm-1")
    assert found is not None


def test_context_manager_rollback(knowledge_uow):
    note = _make_note("kn-cm-2", "daily", date(2026, 7, 29))
    try:
        with sqlalchemy_knowledge_uow(knowledge_uow.session):
            knowledge_uow.notes().save(note)
            raise ValueError("intentional failure")
    except ValueError:
        pass
    found = knowledge_uow.notes().get_by_note_id("kn-cm-2")
    assert found is None
