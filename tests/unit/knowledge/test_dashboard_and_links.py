"""Tests for KnowledgeDashboard retrieval APIs and wiki-link helpers."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from commerceos.knowledge.dashboard import KnowledgeDashboard
from commerceos.knowledge.links import LinkBuilder, WikiLink
from commerceos.knowledge.models import KnowledgeNote


def _note(note_id: str, note_type: str, note_date: date, **kwargs) -> KnowledgeNote:
    defaults = {
        "title": note_id,
        "path": f"{note_type}/{note_id}.md",
        "tags": [],
        "links": [],
        "source_domains": [],
    }
    defaults.update(kwargs)
    return KnowledgeNote(
        note_id=note_id,
        note_type=note_type,
        note_date=note_date,
        **defaults,
    )


@pytest.fixture
def mock_repository():
    repo = MagicMock()
    notes: List[KnowledgeNote] = []

    def _list(*args, **kwargs):
        archived = kwargs.get("archived")
        ntype = kwargs.get("note_type")
        since = kwargs.get("since")
        until = kwargs.get("until")
        tags = set(kwargs.get("tags") or [])
        result = []
        for n in notes:
            if archived is True and n.archived_at is None:
                continue
            if archived is False and n.archived_at is not None:
                continue
            if ntype and n.note_type != ntype:
                continue
            if since and n.note_date < since:
                continue
            if until and n.note_date > until:
                continue
            if tags and not tags.intersection(set(n.tags)):
                continue
            result.append(n)
        return result

    def _save(note):
        notes.append(note)
        return note

    def _get(note_id):
        for n in notes:
            if n.note_id == note_id:
                return n
        return None

    def _latest(note_type, limit=1):
        filtered = [n for n in notes if n.note_type == note_type and n.archived_at is None]
        return sorted(filtered, key=lambda n: n.note_date, reverse=True)[:limit]

    repo.list.side_effect = _list
    repo.save.side_effect = _save
    repo.get_by_note_id.side_effect = _get
    repo.latest_by_type.side_effect = _latest
    return repo


def test_dashboard_get_recent_memory(mock_repository):
    dash = KnowledgeDashboard(mock_repository)
    today = date.today()
    mock_repository.save(_note("n1", "daily", today, tags=["business"]))
    mock_repository.save(_note("n2", "daily", today - timedelta(days=10), tags=["business"]))
    result = dash.get_recent_memory(days=7, note_type="daily")
    assert len(result) == 1
    assert result[0]["note_id"] == "n1"


def test_dashboard_business_timeline(mock_repository):
    dash = KnowledgeDashboard(mock_repository)
    today = date.today()
    mock_repository.save(_note("n1", "daily", today - timedelta(days=1), tags=["revenue"]))
    mock_repository.save(_note("n2", "daily", today, tags=["inventory"]))
    result = dash.get_business_timeline(today - timedelta(days=2), today, categories=["revenue"])
    assert len(result) == 1
    assert result[0]["note_id"] == "n1"


def test_dashboard_find_related_decisions(mock_repository):
    dash = KnowledgeDashboard(mock_repository)
    today = date.today()
    mock_repository.save(_note("n1", "daily", today, links=["decision:d1"]))
    mock_repository.save(_note("n2", "daily", today, links=["decision:d2"]))
    result = dash.find_related_decisions("d1", days=30)
    assert len(result) == 1
    assert result[0]["note_id"] == "n1"


def test_dashboard_find_related_events(mock_repository):
    dash = KnowledgeDashboard(mock_repository)
    today = date.today()
    mock_repository.save(_note("n1", "daily", today, tags=["workflow.completed"], title="Sync completed"))
    mock_repository.save(_note("n2", "daily", today, tags=["other"]))
    result = dash.find_related_events(event_type="workflow.completed", days=30)
    assert len(result) == 1


def test_dashboard_find_project_history(mock_repository):
    dash = KnowledgeDashboard(mock_repository)
    today = date.today()
    mock_repository.save(_note("n1", "project", today, tags=["commerceos"]))
    mock_repository.save(_note("n2", "daily", today, tags=["commerceos"]))
    mock_repository.save(_note("n3", "daily", today, tags=["other"]))
    result = dash.find_project_history("CommerceOS", limit=10)
    assert len(result) == 2


def test_dashboard_search_memory(mock_repository):
    dash = KnowledgeDashboard(mock_repository)
    today = date.today()
    mock_repository.save(_note("n1", "daily", today, title="Revenue Drop Analysis", tags=["revenue"]))
    result = dash.search_memory("Revenue Drop", days=30)
    assert len(result) == 1
    assert result[0]["note_id"] == "n1"


def test_dashboard_read_note(tmp_path: Path, mock_repository):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "daily").mkdir()
    note = _note("n1", "daily", date.today(), path="daily/n1.md")
    (vault / note.path).write_text("# Note\ncontent")
    mock_repository.save(note)

    dash = KnowledgeDashboard(mock_repository, vault_dir=vault)
    data = dash.read_note("n1")
    assert data is not None
    assert "content" in data
    assert "# Note" in data["content"]


def test_dashboard_read_note_missing_file(mock_repository):
    dash = KnowledgeDashboard(mock_repository, vault_dir=Path("/nonexistent"))
    note = _note("n1", "daily", date.today(), path="daily/n1.md")
    mock_repository.save(note)
    assert dash.read_note("n1") is None


def test_wiki_link_basic():
    assert WikiLink.to("abc") == "[[abc]]"
    assert WikiLink.to("abc", "Title") == "[[abc|Title]]"


def test_wiki_link_namespace():
    assert WikiLink.from_namespace("decision", "d1") == "[[decision:d1]]"


def test_wiki_link_parse():
    assert WikiLink.parse("[[abc]]") == ("abc", None)
    assert WikiLink.parse("[[abc|Title]]") == ("abc", "Title")


def test_link_builder_deduplicates_and_excludes_self():
    builder = LinkBuilder("source")
    links = builder.add("a").add("b", "B").add("a").add("source").build()
    assert links == ["[[a]]", "[[b|B]]"]


def test_link_builder_note_ids():
    builder = LinkBuilder("source")
    builder.add("a", "A").add_namespace("decision", "d1")
    assert builder.build_note_ids() == ["a", "decision:d1"]
