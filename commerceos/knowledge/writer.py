"""Markdown writer for the Obsidian knowledge vault.

Produces deterministic frontmatter + body notes. The Markdown file is the source
of truth; the writer only records metadata via a KnowledgeNoteRepository callback
provided by the caller.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from commerceos.knowledge.vault import ObsidianVault


class ObsidianWriter:
    """Write Obsidian Markdown notes with YAML frontmatter and wiki-links."""

    def __init__(self, vault_dir: Path):
        self.vault = ObsidianVault(vault_dir)
        self.vault.ensure_structure()

    def write(
        self,
        note_type: str,
        note_id: str,
        title: str,
        body: str,
        note_date: Optional[date] = None,
        tags: Optional[List[str]] = None,
        links: Optional[List[str]] = None,
        source_domains: Optional[List[str]] = None,
        extra_frontmatter: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Write a note to the vault and return its path.

        Does not duplicate body content into the database. The caller is
        responsible for persisting the metadata index.
        """
        note_date = note_date or date.today()
        generated_at = utc_now().isoformat()
        tags = sorted(set(tags or []))
        links = list(links or [])
        source_domains = sorted(set(source_domains or []))

        frontmatter = {
            "note_id": note_id,
            "type": note_type,
            "date": note_date.isoformat(),
            "generated_at": generated_at,
            "tags": tags,
            "source": "commerceos",
            "links": links,
        }
        if source_domains:
            frontmatter["source_domains"] = source_domains
        if extra_frontmatter:
            frontmatter.update(extra_frontmatter)

        # Reorder for readability and deterministic output.
        ordered = self._order_frontmatter(frontmatter)

        content_lines = [
            "---",
            yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True).strip(),
            "---",
            "",
            f"# {title}",
            "",
        ]

        if body:
            content_lines.append(body.strip())
            content_lines.append("")

        if links:
            content_lines.append("## Related")
            content_lines.append("")
            for link in links:
                content_lines.append(f"- [[{link}]]")
            content_lines.append("")

        content = "\n".join(content_lines)
        path = self.vault.path_for(note_type, note_id, title)
        path.write_text(content, encoding="utf-8")
        return path

    def _order_frontmatter(self, frontmatter: Dict[str, Any]) -> Dict[str, Any]:
        ordered: Dict[str, Any] = {}
        top_keys = ["note_id", "type", "date", "generated_at", "title", "tags", "source", "source_domains", "links"]
        for key in top_keys:
            if key in frontmatter:
                ordered[key] = frontmatter[key]
        for key, value in frontmatter.items():
            if key not in ordered:
                ordered[key] = value
        return ordered

    def link_to(self, note_id: str, title: Optional[str] = None) -> str:
        """Return a wiki-link pointing to another note."""
        if title:
            return f"[[{note_id}|{title}]]"
        return f"[[{note_id}]]"
