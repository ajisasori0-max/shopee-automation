"""WP4.5 — Closed Operational Loop Foundation models.

Extends Decision and Execution models with outcome tracking without changing their
schemas. Outcomes are stored as DecisionOutcome records that reference a Decision
and an optional ExecutionPlan. This keeps the loop explicit: Decision → Action →
Outcome → Memory.
"""
from __future__ import annotations
from commerceos.shared.value_objects.primitives import utc_now


from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from commerceos.platform.database.models import Base, TimestampMixin, new_uuid


class DecisionOutcome(Base, TimestampMixin):
    """Tracked outcome for a decision + execution pair."""

    __tablename__ = "decision_outcomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    decision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("decisions.id"), nullable=False, index=True
    )
    execution_plan_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("execution_plans.id"), nullable=True, index=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    expected_outcome: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    actual_outcome: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    success: Mapped[Optional[bool]] = mapped_column(nullable=True)
    impact_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    lessons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    follow_up_decision_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recorded_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_decision_outcomes_decision_recorded", "decision_id", "recorded_at"),
    )
