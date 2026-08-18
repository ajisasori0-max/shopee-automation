"""Decision Intelligence bounded context: insights, trends, snapshots.

This module defines the database models used by the Intelligence Layer. They are
intended to be storage-agnostic SQLAlchemy models; PostgreSQL-specific features
are avoided so tests can run against SQLite.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, DateTime, JSON, Numeric, Index, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from commerceos.platform.database.models import Base, TimestampMixin, new_uuid


class Insight(Base, TimestampMixin):
    """One deterministic business intelligence insight."""

    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now() + __import__("datetime").timedelta(days=1)
    )
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_insights_category_created", "category", "created_at"),
    )


class TrendSnapshot(Base, TimestampMixin):
    """Materialized trend data point for a metric and period."""

    __tablename__ = "trend_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    metric: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    baseline: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    delta: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    metadata_: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_trend_snapshots_metric_period", "metric", "period"),
    )
