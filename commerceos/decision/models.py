"""Decision Engine database models.

SQLite-compatible PostgreSQL-ready models. No business logic beyond lifecycle
fields. TimestampMixin supplies created_at and updated_at; do not declare them.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import String, Text, DateTime, JSON, Boolean, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from commerceos.platform.database.models import Base, TimestampMixin, new_uuid


class Decision(Base, TimestampMixin):
    """A proposed business decision awaiting approval."""

    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True, default="proposed")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    expected_impact: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now() + timedelta(days=7)
    )
    metadata_: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    evidence: Mapped[List["DecisionEvidence"]] = relationship(
        "DecisionEvidence", back_populates="decision", cascade="all, delete-orphan"
    )
    history: Mapped[List["DecisionHistory"]] = relationship(
        "DecisionHistory", back_populates="decision", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_decisions_category_status", "category", "status"),
        Index("ix_decisions_severity_created", "severity", "created_at"),
    )


class DecisionEvidence(Base, TimestampMixin):
    """Evidence linking a decision to source insights, KPIs, alerts, or rules."""

    __tablename__ = "decision_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    decision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("decisions.id"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    decision: Mapped["Decision"] = relationship("Decision", back_populates="evidence")


class DecisionHistory(Base, TimestampMixin):
    """Audit trail of decision status changes."""

    __tablename__ = "decision_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    decision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("decisions.id"), nullable=False, index=True
    )
    old_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    changed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    decision: Mapped["Decision"] = relationship("Decision", back_populates="history")
