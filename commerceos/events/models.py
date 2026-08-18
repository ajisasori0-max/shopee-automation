"""Event Bus database models.

SQLite-compatible, PostgreSQL-ready.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import String, Text, DateTime, JSON, Integer, Boolean, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from commerceos.events.constants import EventStatus, WorkflowJobStatus, Priority
from commerceos.platform.database.models import Base, TimestampMixin, new_uuid


class Event(Base, TimestampMixin):
    """A domain event published by a bounded context."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True, default=EventStatus.CREATED.value)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    dead_letter: Mapped[Optional["DeadLetterEvent"]] = relationship(
        "DeadLetterEvent", back_populates="event", uselist=False, cascade="all, delete-orphan"
    )
    workflow_jobs: Mapped[List["WorkflowJob"]] = relationship(
        "WorkflowJob", back_populates="trigger_event", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_events_type_status", "event_type", "status"),
        Index("ix_events_aggregate", "aggregate_type", "aggregate_id"),
        Index("ix_events_status_created", "status", "created_at"),
    )


class EventSubscription(Base, TimestampMixin):
    """Registered handler subscription for an event type."""

    __tablename__ = "event_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    handler_name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_event_subscriptions_type_handler", "event_type", "handler_name", unique=True),
    )


class WorkflowJob(Base, TimestampMixin):
    """A multi-step workflow job triggered by an event or scheduled."""

    __tablename__ = "workflow_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workflow_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True, default=WorkflowJobStatus.QUEUED.value)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=Priority.NORMAL.value)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    trigger_event_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("events.id"), nullable=True
    )
    metadata_: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    trigger_event: Mapped[Optional["Event"]] = relationship("Event", back_populates="workflow_jobs")
    history: Mapped[List["WorkflowHistory"]] = relationship(
        "WorkflowHistory", back_populates="job", cascade="all, delete-orphan"
    )
    locks: Mapped[List["DistributedLock"]] = relationship(
        "DistributedLock", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_workflow_jobs_status_scheduled", "status", "scheduled_at"),
        Index("ix_workflow_jobs_name_status", "workflow_name", "status"),
    )


class WorkflowHistory(Base, TimestampMixin):
    """Status change history for workflow jobs."""

    __tablename__ = "workflow_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_jobs.id"), nullable=False, index=True
    )
    old_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    job: Mapped["WorkflowJob"] = relationship("WorkflowJob", back_populates="history")


class DeadLetterEvent(Base, TimestampMixin):
    """Failed event that exceeded retry limit."""

    __tablename__ = "dead_letter_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("events.id"), nullable=False, index=True, unique=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    failed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    retry_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    event: Mapped["Event"] = relationship("Event", back_populates="dead_letter")

    __table_args__ = (
        Index("ix_dead_letter_events_failed_at", "failed_at"),
    )


class DistributedLock(Base, TimestampMixin):
    """Distributed lock for sync jobs, execution jobs, and workflows."""

    __tablename__ = "distributed_locks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    lock_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, unique=True)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now() + timedelta(minutes=5)
    )
    job_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("workflow_jobs.id"), nullable=True, index=True
    )

    job: Mapped[Optional["WorkflowJob"]] = relationship("WorkflowJob", back_populates="locks")

    __table_args__ = (
        Index("ix_distributed_locks_expires_at", "expires_at"),
    )
