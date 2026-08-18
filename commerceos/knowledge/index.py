"""Automatic index generation for the Obsidian knowledge vault.

Builds a deterministic `index.md` from `KnowledgeNote` metadata records. The
Markdown file is the source of truth; this module regenerates the index when
called by a reporter or scheduler.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from commerceos.knowledge.repositories import KnowledgeNoteRepository


class KnowledgeIndex:
    """Generate the vault index.md from note metadata."""

    def __init__(self, vault_dir: Path, repository: Optional[KnowledgeNoteRepository] = None):
        self.vault_dir = vault_dir
        self.repository = repository

    def generate(self, notes: Optional[List[Dict[str, Any]]] = None) -> Path:
        """Generate or regenerate `index.md`.

        If `notes` is provided, use it. Otherwise, query the repository. If no
        repository is available, generate an empty index skeleton.
        """
        if notes is None and self.repository is not None:
            notes = [n.to_dict() for n in self.repository.list(archived=False, limit=1000)]
        notes = notes or []

        categorized = self._categorize(notes)
        lines = [
            "# CommerceOS Knowledge Index",
            "",
            f"Generated: {utc_now().isoformat()}",
            f"Total notes: {len(notes)}",
            "",
            "## Business",
            "",
        ]
        lines.extend(self._category_lines(categorized.get("business", [])))

        lines.extend(["", "## Projects", ""])
        lines.extend(self._category_lines(categorized.get("projects", [])))

        lines.extend(["", "## Decisions", ""])
        lines.extend(self._category_lines(categorized.get("decisions", [])))

        lines.extend(["", "## Lessons Learned", ""])
        lines.extend(self._category_lines(categorized.get("lessons", [])))

        lines.extend(["", "## Experiments", ""])
        lines.extend(self._category_lines(categorized.get("experiments", [])))

        lines.extend(["", "## SOPs", ""])
        lines.extend(self._category_lines(categorized.get("sops", [])))

        lines.extend(["", "## Reference", ""])
        lines.extend(self._category_lines(categorized.get("reference", [])))

        lines.extend(["", "## All Notes", ""])
        for note in sorted(notes, key=lambda n: n.get("note_date", ""), reverse=True):
            path = note.get("path", "")
            title = note.get("title", note.get("note_id", "unknown"))
            note_type = note.get("note_type", "unknown")
            tags = note.get("tags", [])
            tag_str = f" ({', '.join(tags)})" if tags else ""
            lines.append(f"- [[{path}|{title}]] — `{note_type}`{tag_str}")

        index_path = self.vault_dir / "index.md"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("\n".join(lines), encoding="utf-8")
        return index_path

    def _categorize(self, notes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        categories: Dict[str, List[Dict[str, Any]]] = {
            "business": [],
            "projects": [],
            "decisions": [],
            "lessons": [],
            "experiments": [],
            "sops": [],
            "reference": [],
        }
        seen = set()
        for note in notes:
            note_id = note.get("note_id")
            if note_id in seen:
                continue
            seen.add(note_id)
            tags = {t.lower() for t in note.get("tags", [])}
            ntype = note.get("note_type", "").lower()

            if ntype == "decision":
                categories["decisions"].append(note)
            elif ntype == "experiment":
                categories["experiments"].append(note)
            elif ntype == "sop":
                categories["sops"].append(note)
            elif ntype == "reference":
                categories["reference"].append(note)
            elif ntype == "project":
                categories["projects"].append(note)
            elif "lesson" in tags or "lessons" in tags:
                categories["lessons"].append(note)
            else:
                categories["business"].append(note)
        return categories

    def _category_lines(self, notes: List[Dict[str, Any]]) -> List[str]:
        if not notes:
            return ["No entries yet.", ""]
        lines = []
        for note in sorted(notes, key=lambda n: n.get("note_date", ""), reverse=True):
            path = note.get("path", "")
            title = note.get("title", note.get("note_id", "unknown"))
            lines.append(f"- [[{path}|{title}]]")
        lines.append("")
        return lines
