"""Deterministic wiki-link helpers for the knowledge layer.

This module provides stable link conventions without building graph intelligence
or embedding-based retrieval. All link formats are human- and Obsidian-readable.
"""

from typing import List, Optional


# Link namespaces used in frontmatter `links` and inline wiki-links.
NAMESPACE_DAILY = "daily"
NAMESPACE_WEEKLY = "weekly"
NAMESPACE_MONTHLY = "monthly"
NAMESPACE_YEARLY = "yearly"
NAMESPACE_DECISION = "decision"
NAMESPACE_EXECUTION = "execution"
NAMESPACE_ALERT = "alert"
NAMESPACE_EVENT = "event"
NAMESPACE_PROJECT = "project"
NAMESPACE_SOP = "sop"
NAMESPACE_EXPERIMENT = "experiment"


class WikiLink:
    """Formatter for deterministic Obsidian wiki-links."""

    @staticmethod
    def to(note_id: str, title: Optional[str] = None) -> str:
        if title:
            return f"[[{note_id}|{title}]]"
        return f"[[{note_id}]]"

    @staticmethod
    def from_namespace(namespace: str, identifier: str, title: Optional[str] = None) -> str:
        """Return a link in a stable namespace format, e.g. `[[decision:dec-001]]`."""
        note_id = f"{namespace}:{identifier}"
        return WikiLink.to(note_id, title)

    @staticmethod
    def parse(link: str) -> tuple[str, Optional[str]]:
        """Parse a wiki-link into (note_id, optional_title)."""
        inner = link.strip("[]")
        if "|" in inner:
            note_id, title = inner.split("|", 1)
            return note_id, title
        return inner, None

    @staticmethod
    def extract_note_ids(links: List[str]) -> List[str]:
        return [WikiLink.parse(link)[0] for link in links]


class LinkBuilder:
    """Build related link lists for notes."""

    def __init__(self, source_note_id: str):
        self.source_note_id = source_note_id
        self.links: List[str] = []

    def add(self, note_id: str, title: Optional[str] = None) -> "LinkBuilder":
        if note_id and note_id != self.source_note_id:
            self.links.append(WikiLink.to(note_id, title))
        return self

    def add_namespace(self, namespace: str, identifier: str, title: Optional[str] = None) -> "LinkBuilder":
        note_id = f"{namespace}:{identifier}"
        return self.add(note_id, title)

    def build(self) -> List[str]:
        # Return unique links preserving order.
        seen = set()
        unique = []
        for link in self.links:
            note_id, _ = WikiLink.parse(link)
            if note_id not in seen:
                seen.add(note_id)
                unique.append(link)
        return unique

    def build_note_ids(self) -> List[str]:
        return WikiLink.extract_note_ids(self.build())
