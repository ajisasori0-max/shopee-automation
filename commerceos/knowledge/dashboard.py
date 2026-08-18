"""Deterministic knowledge retrieval APIs for the COO layer.

All methods return metadata first. Full content is loaded lazily from the
Markdown file only when the caller explicitly requests it. No embeddings, no
semantic search, no vector database.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from commerceos.knowledge.models import KnowledgeNote
from commerceos.knowledge.repositories import KnowledgeNoteRepository


class KnowledgeDashboard:
    """Read-only API for retrieving knowledge note metadata and content."""

    def __init__(
        self,
        repository: KnowledgeNoteRepository,
        vault_dir: Optional[Path] = None,
    ):
        self.repository = repository
        self.vault_dir = vault_dir

    def get_recent_memory(
        self,
        days: int = 7,
        note_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent active note metadata, ordered by date descending."""
        since = date.today() - timedelta(days=days)
        notes = self.repository.list(
            note_type=note_type,
            since=since,
            archived=False,
            limit=100,
        )
        return [self._to_dict(n) for n in sorted(notes, key=lambda n: n.note_date, reverse=True)]

    def get_business_timeline(
        self,
        start: date,
        end: date,
        categories: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return daily note metadata within a date range, useful for timeline views."""
        notes = self.repository.list(
            note_type="daily",
            since=start,
            until=end,
            archived=False,
            limit=500,
        )
        if categories:
            notes = [n for n in notes if any(t in categories for t in n.tags)]
        return [self._to_dict(n) for n in sorted(notes, key=lambda n: n.note_date, reverse=True)]

    def find_related_decisions(
        self,
        decision_id: str,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return notes that link to the given decision or vice versa."""
        target = f"decision:{decision_id}"
        target_simple = decision_id
        since = date.today() - timedelta(days=days)
        notes = self.repository.list(since=since, archived=False, limit=500)
        related = []
        for n in notes:
            links = {link.lower() for link in n.links}
            if target.lower() in links or target_simple.lower() in links:
                related.append(self._to_dict(n))
        return related

    def find_related_events(
        self,
        event_type: Optional[str] = None,
        aggregate_id: Optional[str] = None,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return notes tagged with or linking to an event type/aggregate."""
        since = date.today() - timedelta(days=days)
        notes = self.repository.list(since=since, archived=False, limit=500)
        related = []
        terms = [t for t in (event_type, aggregate_id) if t]
        for n in notes:
            text = " ".join([str(t) for t in n.tags + n.links + [n.title, n.note_id]]).lower()
            if any(t.lower() in text for t in terms):
                related.append(self._to_dict(n))
        return related

    def find_project_history(
        self,
        project: str = "CommerceOS",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return notes tagged with the project name."""
        project_lower = project.lower()
        notes = self.repository.list(archived=False, limit=1000)
        matched = [
            n
            for n in notes
            if project_lower in [t.lower() for t in n.tags]
            or n.note_type == "project"
        ]
        matched = sorted(matched, key=lambda n: n.note_date, reverse=True)
        return [self._to_dict(n) for n in matched[:limit]]

    def search_memory(
        self,
        query: str,
        note_type: Optional[str] = None,
        days: int = 90,
    ) -> List[Dict[str, Any]]:
        """Deterministic search: title, tags, note_id, path. Does not scan file content."""
        since = date.today() - timedelta(days=days)
        notes = self.repository.list(
            note_type=note_type,
            since=since,
            archived=False,
            limit=500,
        )
        query_lower = query.lower()
        results = []
        for n in notes:
            searchable = " ".join([
                n.note_id,
                n.title,
                n.note_type,
                " ".join(n.tags),
                " ".join(n.source_domains),
                n.path,
            ]).lower()
            if query_lower in searchable:
                results.append(self._to_dict(n))
        return results

    def read_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Load full Markdown content for a note. Returns None if file missing."""
        note = self.repository.get_by_note_id(note_id)
        if note is None or self.vault_dir is None:
            return None
        path = self.vault_dir / note.path
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        data = self._to_dict(note)
        data["content"] = content
        return data

    def _to_dict(self, note: KnowledgeNote) -> Dict[str, Any]:
        return note.to_dict()

    def latest_summary(self, note_type: str = "weekly") -> Optional[Dict[str, Any]]:
        """Return the latest active note of a given type."""
        notes = self.repository.latest_by_type(note_type, limit=1)
        if not notes:
            return None
        return self._to_dict(notes[0])

    def recent_decisions(self, days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent decision/project notes."""
        since = date.today() - timedelta(days=days)
        notes = self.repository.list(
            note_type="decision",
            since=since,
            archived=False,
            limit=limit,
        )
        return [self._to_dict(n) for n in sorted(notes, key=lambda n: n.note_date, reverse=True)]

    def recent_lessons(self, days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent notes tagged with lessons."""
        since = date.today() - timedelta(days=days)
        notes = self.repository.list(
            since=since,
            archived=False,
            tags=["lesson"],
            limit=limit,
        )
        return [self._to_dict(n) for n in sorted(notes, key=lambda n: n.note_date, reverse=True)]

    def memory_timeline(self, days: int = 30) -> List[Dict[str, Any]]:
        """Return a flat timeline of recent active notes across all types."""
        since = date.today() - timedelta(days=days)
        notes = self.repository.list(since=since, archived=False, limit=500)
        return [self._to_dict(n) for n in sorted(notes, key=lambda n: n.note_date, reverse=True)]
