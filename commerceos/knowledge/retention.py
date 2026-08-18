"""Knowledge retention policy.

Archive notes after successful higher-level summarization. Files are moved to
`90 Archive/` but remain recoverable. Metadata records are marked with
`archived_at` but not deleted.
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from commerceos.knowledge.repositories import KnowledgeNoteRepository


class RetentionPolicy:
    """Move notes to archive after successful higher-level summary."""

    def __init__(
        self,
        repository: KnowledgeNoteRepository,
        vault_dir: Path,
    ):
        self.repository = repository
        self.vault_dir = vault_dir

    def archive_daily_notes(self, before: Optional[date] = None) -> List[str]:
        """Archive daily notes older than the cut-off date.

        Default cut-off is the Monday of the previous completed week, i.e. archive
        dailies that have already been summarized into a weekly note.
        """
        before = before or self._default_daily_cutoff()
        notes = self.repository.list(
            note_type="daily",
            until=before,
            archived=False,
            limit=1000,
        )
        return self._archive_notes([n for n in notes if n.note_date < before])

    def archive_weekly_notes(self, before: Optional[date] = None) -> List[str]:
        """Archive weekly notes older than the cut-off month."""
        before = before or self._default_weekly_cutoff()
        notes = self.repository.list(
            note_type="weekly",
            until=before,
            archived=False,
            limit=1000,
        )
        return self._archive_notes([n for n in notes if n.note_date < before])

    def archive_monthly_notes(self, before: Optional[date] = None) -> List[str]:
        """Archive monthly notes older than the cut-off year."""
        before = before or self._default_monthly_cutoff()
        notes = self.repository.list(
            note_type="monthly",
            until=before,
            archived=False,
            limit=1000,
        )
        return self._archive_notes([n for n in notes if n.note_date < before])

    def _archive_notes(self, notes) -> List[str]:
        archived_ids: List[str] = []
        archive_root = self.vault_dir / "90 Archive"
        archive_root.mkdir(parents=True, exist_ok=True)

        for note in notes:
            archived = self.repository.archive(note.note_id)
            if archived is None:
                continue
            archived_ids.append(archived.note_id)

            source = self.vault_dir / note.path
            if source.exists():
                target_dir = archive_root / note.note_type
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / source.name
                counter = 1
                while target.exists():
                    target = target_dir / f"{source.stem}_{counter}{source.suffix}"
                    counter += 1
                source.rename(target)

        return archived_ids

    def _default_daily_cutoff(self) -> date:
        today = date.today()
        # Last Monday that completed a full week.
        return today - timedelta(days=today.weekday() + 7)

    def _default_weekly_cutoff(self) -> date:
        today = date.today()
        # First day of the previous month.
        if today.month == 1:
            return date(today.year - 1, 12, 1)
        return date(today.year, today.month - 1, 1)

    def _default_monthly_cutoff(self) -> date:
        today = date.today()
        return date(today.year - 1, 1, 1)
