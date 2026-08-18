"""Obsidian vault layout and index maintenance.

The vault structure is deterministic and idempotent. Existing files are never
deleted or overwritten by `ensure_structure`. The `index.md` file is rebuilt from
metadata records when explicitly requested by later phases.
"""

from pathlib import Path
from typing import List, Optional


VAULT_ROOTS = ["00 Inbox", "10 COO", "20 Decisions", "30 Projects", "40 SOP", "50 Reference", "90 Archive"]

COO_SUBDIRS = ["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"]


class ObsidianVault:
    """Manage the standard CommerceOS Obsidian vault layout."""

    def __init__(self, vault_dir: Path):
        self.vault_dir = vault_dir.expanduser().resolve()

    def ensure_structure(self) -> Path:
        """Create the standard folder structure if it does not exist."""
        for root in VAULT_ROOTS:
            (self.vault_dir / root).mkdir(parents=True, exist_ok=True)
        for sub in COO_SUBDIRS:
            (self.vault_dir / "10 COO" / sub).mkdir(parents=True, exist_ok=True)
        return self.vault_dir

    def path_for(self, note_type: str, note_id: str, title: Optional[str] = None) -> Path:
        """Return the canonical path for a note type.

        Daily notes:    10 COO/Daily/YYYY-MM-DD.md
        Weekly notes:   10 COO/Weekly/YYYY-Wnn.md
        Monthly notes:  10 COO/Monthly/YYYY-MM.md
        Quarterly notes:10 COO/Quarterly/YYYY-Qn.md
        Yearly notes:   10 COO/Yearly/YYYY.md
        Decisions:      20 Decisions/{note_id}.md
        Projects:       30 Projects/{note_id}.md
        SOP:            40 SOP/{note_id}.md
        Reference:      50 Reference/{note_id}.md
        Inbox/fallback: 00 Inbox/{note_id}.md
        """
        folder = self._folder_for_type(note_type)
        filename = self._filename_for(note_type, note_id, title)
        path = self.vault_dir / folder / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _folder_for_type(self, note_type: str) -> str:
        mapping = {
            "daily": "10 COO/Daily",
            "weekly": "10 COO/Weekly",
            "monthly": "10 COO/Monthly",
            "quarterly": "10 COO/Quarterly",
            "yearly": "10 COO/Yearly",
            "decision": "20 Decisions",
            "project": "30 Projects",
            "sop": "40 SOP",
            "reference": "50 Reference",
        }
        return mapping.get(note_type.lower(), "00 Inbox")

    def _filename_for(self, note_type: str, note_id: str, title: Optional[str] = None) -> str:
        if title:
            safe_title = title.replace("/", "-")
            return f"{note_id} {safe_title}.md"
        return f"{note_id}.md"

    def index_path(self) -> Path:
        return self.vault_dir / "index.md"

    def archive_path(self) -> Path:
        return self.vault_dir / "90 Archive"

    def exists(self) -> bool:
        """Return True if the vault directory and all root folders exist."""
        if not self.vault_dir.exists():
            return False
        return all((self.vault_dir / root).exists() for root in VAULT_ROOTS)
