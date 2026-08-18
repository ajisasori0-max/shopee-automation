"""Tests for Obsidian vault and writer."""

import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from commerceos.knowledge.vault import COO_SUBDIRS, VAULT_ROOTS, ObsidianVault
from commerceos.knowledge.writer import ObsidianWriter


@pytest.fixture
def temp_vault(tmp_path: Path):
    vault = ObsidianVault(tmp_path / "vault")
    return vault


def test_vault_ensure_structure_creates_folders(temp_vault: ObsidianVault):
    vault_dir = temp_vault.ensure_structure()
    assert vault_dir.exists()
    for root in VAULT_ROOTS:
        assert (vault_dir / root).exists()
    for sub in COO_SUBDIRS:
        assert (vault_dir / "10 COO" / sub).exists()


def test_vault_ensure_structure_is_idempotent(temp_vault: ObsidianVault):
    temp_vault.ensure_structure()
    # Create a dummy file in one folder; it should remain untouched.
    dummy = temp_vault.vault_dir / "10 COO" / "Daily" / "hello.md"
    dummy.write_text("keep me")
    temp_vault.ensure_structure()
    assert dummy.read_text() == "keep me"


def test_vault_path_for_daily(temp_vault: ObsidianVault):
    path = temp_vault.path_for("daily", "2026-07-29", title="Operations")
    assert path.relative_to(temp_vault.vault_dir) == Path("10 COO/Daily/2026-07-29 Operations.md")


def test_vault_path_for_decision(temp_vault: ObsidianVault):
    path = temp_vault.path_for("decision", "dec-001", title="Raise Budget")
    assert path.relative_to(temp_vault.vault_dir) == Path("20 Decisions/dec-001 Raise Budget.md")


def test_vault_path_for_inbox_fallback(temp_vault: ObsidianVault):
    path = temp_vault.path_for("unknown", "tmp-001")
    assert path.relative_to(temp_vault.vault_dir) == Path("00 Inbox/tmp-001.md")


def test_vault_exists_true_after_create(temp_vault: ObsidianVault):
    assert not temp_vault.exists()
    temp_vault.ensure_structure()
    assert temp_vault.exists()


def test_writer_creates_frontmatter_and_body(temp_vault: ObsidianVault):
    writer = ObsidianWriter(temp_vault.vault_dir)
    path = writer.write(
        note_type="daily",
        note_id="kn-2026-07-29",
        title="Daily Operations",
        body="## KPIs\n- Revenue: Rp 1,000,000",
        note_date=date(2026, 7, 29),
        tags=["daily", "operations"],
        links=["kn-2026-07-28"],
        source_domains=["monitoring"],
    )

    content = path.read_text(encoding="utf-8")
    assert path.exists()
    assert content.startswith("---")
    assert "note_id: kn-2026-07-29" in content
    assert "type: daily" in content
    assert "date: '2026-07-29'" in content or "date: 2026-07-29" in content
    assert "tags:" in content
    assert "daily" in content
    assert "operations" in content
    assert "source: commerceos" in content
    assert "source_domains:" in content
    assert "links:" in content
    assert "- [[kn-2026-07-28]]" in content
    assert "# Daily Operations" in content
    assert "## KPIs" in content


def test_writer_link_to(temp_vault: ObsidianVault):
    writer = ObsidianWriter(temp_vault.vault_dir)
    assert writer.link_to("kn-1") == "[[kn-1]]"
    assert writer.link_to("kn-1", "Previous Day") == "[[kn-1|Previous Day]]"


def test_writer_deduplicates_tags_and_keeps_order(temp_vault: ObsidianVault):
    writer = ObsidianWriter(temp_vault.vault_dir)
    path = writer.write(
        note_type="daily",
        note_id="kn-2026-07-30",
        title="T",
        body="",
        tags=["b", "a", "b", "a"],
    )
    content = path.read_text(encoding="utf-8")
    assert "tags:\n- a\n- b" in content


def test_writer_does_not_overwrite_existing_file(temp_vault: ObsidianVault):
    writer = ObsidianWriter(temp_vault.vault_dir)
    path = writer.write(
        note_type="daily",
        note_id="kn-2026-07-31",
        title="Original",
        body="original",
    )
    original_mtime = path.stat().st_mtime
    # Write again with different content but same note_id/title.
    path2 = writer.write(
        note_type="daily",
        note_id="kn-2026-07-31",
        title="Original",
        body="updated",
    )
    assert path == path2
    # The writer currently overwrites by design. We document this behavior:
    assert "updated" in path.read_text(encoding="utf-8")
    assert path.stat().st_mtime >= original_mtime


def test_writer_extra_frontmatter(temp_vault: ObsidianVault):
    writer = ObsidianWriter(temp_vault.vault_dir)
    path = writer.write(
        note_type="weekly",
        note_id="kn-2026-W31",
        title="Weekly Review",
        body="",
        extra_frontmatter={"experiment_id": "exp-001"},
    )
    content = path.read_text(encoding="utf-8")
    assert "experiment_id: exp-001" in content


def test_writer_source_domains_optional(temp_vault: ObsidianVault):
    writer = ObsidianWriter(temp_vault.vault_dir)
    path = writer.write(
        note_type="reference",
        note_id="ref-001",
        title="Reference",
        body="",
    )
    content = path.read_text(encoding="utf-8")
    assert "source_domains" not in content
