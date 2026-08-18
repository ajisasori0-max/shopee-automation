"""Execution Engine database models.

SQLite-compatible, PostgreSQL-ready. ExecutionPlan is immutable once created.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import String, Text, DateTime, JSON, Integer, Boolean, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from commerceos.platform.database.models import Base, TimestampMixin, new_uuid


class ExecutionPlan(Base, TimestampMixin):
    """Immutable execution plan created from an approved decision."""

    __tablename__ = "execution_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    decision_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("decisions.id"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True, default="planned")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now() + timedelta(days=1)
    )
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    metadata_: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    steps: Mapped[List["ExecutionStep"]] = relationship(
        "ExecutionStep", back_populates="plan", cascade="all, delete-orphan", order_by="ExecutionStep.step_number"
    )
    history: Mapped[List["ExecutionHistory"]] = relationship(
        "ExecutionHistory", back_populates="plan", cascade="all, delete-orphan"
    )
    audit: Mapped[List["ExecutionAudit"]] = relationship(
        "ExecutionAudit", back_populates="plan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_execution_plans_decision_status", "decision_id", "status"),
        Index("ix_execution_plans_status_created", "status", "created_at"),
    )


class ExecutionStep(Base, TimestampMixin):
    """One step inside an execution plan."""

    __tablename__ = "execution_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("execution_plans.id"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rollback_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    plan: Mapped["ExecutionPlan"] = relationship("ExecutionPlan", back_populates="steps")

    __table_args__ = (
        Index("ix_execution_steps_plan_id", "plan_id"),
        Index("ix_execution_steps_plan_id_step_number", "plan_id", "step_number"),
    )


class ExecutionHistory(Base, TimestampMixin):
    """Status change audit for execution plans."""

    __tablename__ = "execution_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("execution_plans.id"), nullable=False
    )
    old_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    changed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    plan: Mapped["ExecutionPlan"] = relationship("ExecutionPlan", back_populates="history")

    __table_args__ = (
        Index("ix_execution_history_plan_id", "plan_id"),
    )


class ExecutionAudit(Base, TimestampMixin):
    """Fine-grained execution event log."""

    __tablename__ = "execution_audit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("execution_plans.id"), nullable=False
    )
    event: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    actor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    plan: Mapped["ExecutionPlan"] = relationship("ExecutionPlan", back_populates="audit")

    __table_args__ = (
        Index("ix_execution_audit_plan_id", "plan_id"),
    )
