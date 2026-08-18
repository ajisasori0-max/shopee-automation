"""Tests for retention policy and reporter integration."""

from datetime import date, timedelta
from pathlib import Path
from typing import List
from unittest.mock import MagicMock

import pytest

from commerceos.knowledge.models import KnowledgeNote
from commerceos.knowledge.retention import RetentionPolicy


@pytest.fixture
def retention_setup(tmp_path: Path):
    notes: List[KnowledgeNote] = []
    repo = MagicMock()

    def _list(*args, **kwargs):
        ntype = kwargs.get("note_type")
        until = kwargs.get("until")
        archived = kwargs.get("archived")
        result = []
        for n in notes:
            if ntype and n.note_type != ntype:
                continue
            if until and n.note_date >= until:
                continue
            if archived is True and n.archived_at is None:
                continue
            if archived is False and n.archived_at is not None:
                continue
            result.append(n)
        return result

    def _archive(note_id):
        for n in notes:
            if n.note_id == note_id and n.archived_at is None:
                n.archived_at = "2026-07-29T00:00:00+00:00"
                return n
        return None

    repo.list.side_effect = _list
    repo.archive.side_effect = _archive

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "daily").mkdir()
    (vault / "weekly").mkdir()
    (vault / "monthly").mkdir()

    return repo, vault, notes


def test_retention_archives_old_dailies(retention_setup):
    repo, vault, notes = retention_setup

    cutoff = date(2026, 7, 20)
    old = KnowledgeNote(
        note_id="d1",
        note_type="daily",
        note_date=cutoff - timedelta(days=1),
        title="old",
        path="daily/old.md",
        tags=[],
        links=[],
        source_domains=[],
    )
    new = KnowledgeNote(
        note_id="d2",
        note_type="daily",
        note_date=cutoff + timedelta(days=1),
        title="new",
        path="daily/new.md",
        tags=[],
        links=[],
        source_domains=[],
    )
    notes.extend([old, new])
    (vault / old.path).write_text("old")
    (vault / new.path).write_text("new")

    policy = RetentionPolicy(repo, vault)
    archived = policy.archive_daily_notes(before=cutoff)
    assert archived == ["d1"]
    assert (vault / "90 Archive" / "daily" / "old.md").exists()
    assert not (vault / old.path).exists()
    assert (vault / new.path).exists()


def test_retention_archives_old_weeklies(retention_setup):
    repo, vault, notes = retention_setup
    cutoff = date(2026, 7, 1)
    note = KnowledgeNote(
        note_id="w1",
        note_type="weekly",
        note_date=cutoff - timedelta(days=1),
        title="old week",
        path="weekly/old.md",
        tags=[],
        links=[],
        source_domains=[],
    )
    notes.append(note)
    (vault / note.path).write_text("old")

    policy = RetentionPolicy(repo, vault)
    archived = policy.archive_weekly_notes(before=cutoff)
    assert archived == ["w1"]
    assert (vault / "90 Archive" / "weekly" / "old.md").exists()


def test_retention_archives_old_monthlies(retention_setup):
    repo, vault, notes = retention_setup
    cutoff = date(2026, 1, 1)
    note = KnowledgeNote(
        note_id="m1",
        note_type="monthly",
        note_date=cutoff - timedelta(days=1),
        title="old month",
        path="monthly/old.md",
        tags=[],
        links=[],
        source_domains=[],
    )
    notes.append(note)
    (vault / note.path).write_text("old")

    policy = RetentionPolicy(repo, vault)
    archived = policy.archive_monthly_notes(before=cutoff)
    assert archived == ["m1"]
    assert (vault / "90 Archive" / "monthly" / "old.md").exists()


def test_retention_handles_duplicate_filenames(retention_setup):
    repo, vault, notes = retention_setup
    cutoff = date(2026, 7, 20)
    for i in range(2):
        note = KnowledgeNote(
            note_id=f"d{i}",
            note_type="daily",
            note_date=cutoff - timedelta(days=1),
            title="old",
            path=f"daily/old_{i}.md" if i else "daily/old.md",
            tags=[],
            links=[],
            source_domains=[],
        )
        notes.append(note)
    (vault / "daily" / "old.md").write_text("first")
    (vault / "daily" / "old_1.md").write_text("second")

    policy = RetentionPolicy(repo, vault)
    archived = policy.archive_daily_notes(before=cutoff)
    assert len(archived) == 2
    assert (vault / "90 Archive" / "daily" / "old.md").exists()
    assert (vault / "90 Archive" / "daily" / "old_1.md").exists()
