"""WP3.2 — Organizational Memory Foundation.

Extends the knowledge layer with richer classification, lifecycle automation, and
project notes. No semantic search or graph storage.
"""
from __future__ import annotations
from commerceos.shared.value_objects.primitives import utc_now


from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from commerceos.knowledge.links import LinkBuilder, WikiLink
from commerceos.knowledge.models import KnowledgeNote
from commerceos.knowledge.retention import RetentionPolicy
from commerceos.knowledge.vault import ObsidianVault
from commerceos.knowledge.writer import ObsidianWriter


class OrganizationalMemory:
    """Richer memory classification and lifecycle operations for WP3.2."""

    def __init__(
        self,
        repository,
        vault_dir: Optional[Path] = None,
        writer: Optional[ObsidianWriter] = None,
    ):
        from commerceos.config.settings import get_settings

        settings = get_settings()
        self.vault_dir = vault_dir or settings.obsidian_vault_path
        self.repository = repository
        self.writer = writer or ObsidianWriter(self.vault_dir)
        self.retention = RetentionPolicy(repository, self.vault_dir)

    def create_lesson(
        self,
        title: str,
        text: str,
        related_note_ids: Optional[List[str]] = None,
        project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a standalone lesson note."""
        note_id = f"lesson-{utc_now().strftime('%Y%m%d-%H%M%S')}"
        links = LinkBuilder(note_id)
        for rid in related_note_ids or []:
            links.add(rid)
        tags = ["lesson"]
        if project:
            tags.append(project.lower().replace(" ", "-"))

        path = self.writer.write(
            note_type="reference",
            note_id=note_id,
            title=title,
            body=f"## Lesson\n\n{text}",
            tags=tags,
            links=links.build_note_ids(),
            source_domains=["knowledge"],
        )
        return {"note_id": note_id, "path": str(path)}

    def create_experiment(
        self,
        title: str,
        hypothesis: str,
        expected_outcome: str,
        project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an experiment tracking note."""
        note_id = f"experiment-{utc_now().strftime('%Y%m%d-%H%M%S')}"
        tags = ["experiment"]
        if project:
            tags.append(project.lower().replace(" ", "-"))

        body = (
            f"## Hypothesis\n\n{hypothesis}\n\n"
            f"## Expected Outcome\n\n{expected_outcome}\n\n"
            "## Actual Outcome\n\nNot recorded yet.\n\n"
            "## Decision\n\nNo decision linked yet.\n"
        )
        path = self.writer.write(
            note_type="experiment",
            note_id=note_id,
            title=title,
            body=body,
            tags=tags,
            source_domains=["knowledge"],
        )
        return {"note_id": note_id, "path": str(path)}

    def create_sop(
        self,
        title: str,
        steps: List[str],
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a standard operating procedure note."""
        note_id = f"sop-{utc_now().strftime('%Y%m%d-%H%M%S')}"
        tags = ["sop"]
        if category:
            tags.append(category.lower().replace(" ", "-"))

        body_lines = ["## Steps", ""]
        for i, step in enumerate(steps, 1):
            body_lines.append(f"{i}. {step}")
        body_lines.append("")

        path = self.writer.write(
            note_type="sop",
            note_id=note_id,
            title=title,
            body="\n".join(body_lines),
            tags=tags,
            source_domains=["knowledge"],
        )
        return {"note_id": note_id, "path": str(path)}

    def create_project_note(
        self,
        name: str,
        status: str,
        milestones: List[str],
    ) -> Dict[str, Any]:
        """Create a project summary note."""
        note_id = f"project-{name.lower().replace(' ', '-')}"
        body_lines = [
            f"## Status\n\n{status}\n",
            "## Milestones",
            "",
        ]
        for milestone in milestones:
            body_lines.append(f"- {milestone}")
        body_lines.append("")

        path = self.writer.write(
            note_type="project",
            note_id=note_id,
            title=name,
            body="\n".join(body_lines),
            tags=["project", name.lower().replace(" ", "-")],
            source_domains=["knowledge"],
        )
        return {"note_id": note_id, "path": str(path)}

    def run_lifecycle(self) -> Dict[str, List[str]]:
        """Run the full archive lifecycle."""
        return {
            "daily": self.retention.archive_daily_notes(),
            "weekly": self.retention.archive_weekly_notes(),
            "monthly": self.retention.archive_monthly_notes(),
        }
