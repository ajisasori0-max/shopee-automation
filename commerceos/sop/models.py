"""Operational SOP Engine models.

Lightweight persistence for SOP definitions and executions. The SOP definitions
themselves are code-first in `commerceos.sop.engine`, but executions are recorded
for auditability.
"""

from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, JSON, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column

from commerceos.platform.database.models import Base, TimestampMixin, new_uuid


class SOPDefinitionRecord(Base, TimestampMixin):
    """Persistent record of a SOP definition for audit and version tracking."""

    __tablename__ = "sop_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
    steps: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (
        Index("ix_sop_definitions_enabled", "enabled", "category"),
    )


class SOPExecutionRecord(Base, TimestampMixin):
    """Recorded execution of a SOP."""

    __tablename__ = "sop_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sop_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    execution_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True, unique=True)
    applies: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    branches: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    outputs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    errors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: utc_now())
    source_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    __table_args__ = (
        Index("ix_sop_executions_store_executed", "store_id", "executed_at"),
    )
