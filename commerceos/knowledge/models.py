"""Knowledge layer database models.

SQLite-compatible PostgreSQL-ready models. The Markdown file in Obsidian remains
the source of truth; these tables store navigation metadata only.
"""

from datetime import date, datetime, timezone
from typing import Optional, List

from sqlalchemy import String, Text, Date, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from commerceos.platform.database.models import Base, TimestampMixin, new_uuid


class KnowledgeNote(Base, TimestampMixin):
    """Index record for one Obsidian note written by the knowledge layer."""

    __tablename__ = "knowledge_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    note_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    note_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    note_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    tags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    links: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    source_domains: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    __table_args__ = (
        Index("ix_knowledge_notes_type_date", "note_type", "note_date"),
        Index("ix_knowledge_notes_archived", "archived_at", "note_type"),
    )

    def is_archived(self) -> bool:
        return self.archived_at is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "note_id": self.note_id,
            "note_type": self.note_type,
            "note_date": self.note_date.isoformat() if self.note_date else None,
            "title": self.title,
            "path": self.path,
            "tags": list(self.tags or []),
            "links": list(self.links or []),
            "source_domains": list(self.source_domains or []),
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
