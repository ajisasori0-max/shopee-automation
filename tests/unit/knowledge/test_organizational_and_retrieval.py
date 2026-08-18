"""Tests for WP3.2 organizational memory and WP3.3 retrieval engine."""

from datetime import date, timedelta
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest

from commerceos.knowledge.dashboard import KnowledgeDashboard
from commerceos.knowledge.models import KnowledgeNote
from commerceos.knowledge.organizational_memory import OrganizationalMemory
from commerceos.knowledge.retrieval_engine import MemoryRetrievalEngine


@pytest.fixture
def repo_and_vault(tmp_path: Path):
    notes: List[KnowledgeNote] = []
    repo = MagicMock()

    def _list(*args, **kwargs):
        ntype = kwargs.get("note_type")
        since = kwargs.get("since")
        until = kwargs.get("until")
        archived = kwargs.get("archived")
        tags = set(kwargs.get("tags") or [])
        limit = kwargs.get("limit", 100)
        result = []
        for n in notes:
            if ntype and n.note_type != ntype:
                continue
            if since and n.note_date < since:
                continue
            if until and n.note_date > until:
                continue
            if archived is True and n.archived_at is None:
                continue
            if archived is False and n.archived_at is not None:
                continue
            if tags and not tags.intersection(set(n.tags)):
                continue
            result.append(n)
        return result[:limit]

    def _save(note):
        notes.append(note)
        return note

    repo.list.side_effect = _list
    repo.save.side_effect = _save

    return repo, tmp_path, notes


def test_create_lesson(repo_and_vault):
    repo, vault, _notes = repo_and_vault
    org = OrganizationalMemory(repo, vault_dir=vault)
    result = org.create_lesson("Slow sync lesson", "Check token health before debugging.")
    assert result["note_id"].startswith("lesson-")
    path = Path(result["path"])
    assert path.exists()
    assert "lesson" in path.read_text(encoding="utf-8")


def test_create_experiment(repo_and_vault):
    repo, vault, _notes = repo_and_vault
    org = OrganizationalMemory(repo, vault_dir=vault)
    result = org.create_experiment(
        "ROAS test",
        "Increasing budget improves ROAS",
        "ROAS remains stable or improves",
        project="CommerceOS",
    )
    assert result["note_id"].startswith("experiment-")
    path = Path(result["path"])
    assert "experiment" in path.read_text(encoding="utf-8")


def test_create_sop(repo_and_vault):
    repo, vault, _notes = repo_and_vault
    org = OrganizationalMemory(repo, vault_dir=vault)
    result = org.create_sop("Restart sync", ["Stop scheduler", "Refresh token", "Run live_resync"])
    path = Path(result["path"])
    content = path.read_text(encoding="utf-8")
    assert "sop" in content
    assert "Restart sync" in content


def test_create_project_note(repo_and_vault):
    repo, vault, _notes = repo_and_vault
    org = OrganizationalMemory(repo, vault_dir=vault)
    result = org.create_project_note("CommerceOS", "In progress", ["WP3.1 done", "WP3.2 in progress"])
    path = Path(result["path"])
    content = path.read_text(encoding="utf-8")
    assert "project" in content
    assert "WP3.1 done" in content


def test_retrieval_engine_decision_history():
    repo = MagicMock()
    notes = [
        KnowledgeNote(
            note_id="d1",
            note_type="decision",
            note_date=date.today(),
            title="Pricing decision",
            path="20 Decisions/d1.md",
            tags=["decision", "pricing"],
            links=[],
            source_domains=[],
        ),
        KnowledgeNote(
            note_id="d2",
            note_type="decision",
            note_date=date.today(),
            title="Budget decision",
            path="20 Decisions/d2.md",
            tags=["decision", "marketing"],
            links=[],
            source_domains=[],
        ),
    ]
    repo.list.return_value = notes

    dash = KnowledgeDashboard(repo)
    engine = MemoryRetrievalEngine(dash)
    history = engine.decision_history(query="pricing", days=30)
    assert len(history) == 1
    assert history[0]["note_id"] == "d1"


def test_retrieval_engine_what_happened_before():
    repo = MagicMock()
    event_date = date(2026, 7, 29)
    notes = [
        KnowledgeNote(
            note_id="kn-2026-07-28",
            note_type="daily",
            note_date=event_date - timedelta(days=1),
            title="Daily 28",
            path="10 COO/Daily/28.md",
            tags=["daily"],
            links=[],
            source_domains=[],
        ),
    ]
    repo.list.return_value = notes

    dash = KnowledgeDashboard(repo)
    engine = MemoryRetrievalEngine(dash)
    result = engine.what_happened_before(event_date, window_days=7)
    assert result["note_count"] == 1
    assert result["notes"][0]["note_id"] == "kn-2026-07-28"


def test_retrieval_engine_project_history():
    repo = MagicMock()
    notes = [
        KnowledgeNote(
            note_id="p1",
            note_type="project",
            note_date=date.today(),
            title="CommerceOS",
            path="30 Projects/CommerceOS.md",
            tags=["project", "commerceos"],
            links=[],
            source_domains=[],
        ),
    ]
    repo.list.return_value = notes

    dash = KnowledgeDashboard(repo)
    engine = MemoryRetrievalEngine(dash)
    result = engine.project_history("CommerceOS", days=30)
    assert result["project"] == "CommerceOS"
    assert result["note_count"] == 1


def test_retrieval_engine_timeline_around_metric():
    repo = MagicMock()
    notes = [
        KnowledgeNote(
            note_id="kn-2026-07-29",
            note_type="daily",
            note_date=date.today(),
            title="Revenue Drop",
            path="10 COO/Daily/29.md",
            tags=["revenue"],
            links=[],
            source_domains=[],
        ),
    ]
    repo.list.return_value = notes

    dash = KnowledgeDashboard(repo)
    engine = MemoryRetrievalEngine(dash)
    result = engine.timeline_around_metric("revenue", days=14)
    assert result["note_count"] == 1


def test_retrieval_engine_memory_timeline():
    repo = MagicMock()
    notes = [
        KnowledgeNote(
            note_id="kn-1",
            note_type="daily",
            note_date=date.today(),
            title="A",
            path="a.md",
            tags=[],
            links=[],
            source_domains=[],
        ),
    ]
    repo.list.return_value = notes

    dash = KnowledgeDashboard(repo)
    engine = MemoryRetrievalEngine(dash)
    result = engine.memory_timeline(days=30)
    assert len(result) == 1


def test_organizational_memory_run_lifecycle(repo_and_vault):
    repo, vault, notes = repo_and_vault
    cutoff = date(2026, 7, 20)
    old = KnowledgeNote(
        note_id="d1",
        note_type="daily",
        note_date=cutoff - timedelta(days=1),
        title="old",
        path="10 COO/Daily/old.md",
        tags=[],
        links=[],
        source_domains=[],
    )
    notes.append(old)
    path = vault / "10 COO" / "Daily" / "old.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("old")

    repo.archive.return_value = old
    org = OrganizationalMemory(repo, vault_dir=vault)
    result = org.run_lifecycle()
    assert "daily" in result
