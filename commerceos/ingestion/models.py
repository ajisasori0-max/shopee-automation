"""Ingestion bounded context: raw payload persistence, sync lifecycle, provenance.

The Ingestion context owns the raw data pipeline. It knows how to store raw
marketplace payloads, track sync runs, record provenance, and manage
sync checkpoints.

It does NOT compute KPIs, apply business rules, or generate Commerce State.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, Integer, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from commerceos.platform.database.models import Base, TimestampMixin, new_uuid


# Ensure SOP tables are registered in the shared Base metadata so that
# create_all() creates them without requiring a separate migration call.
try:
    from commerceos.sop import models as _sop_models  # noqa: F401
except Exception:
    pass


class SyncRun(Base, TimestampMixin):
    """One row per connector sync invocation."""

    __tablename__ = "sync_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    connector_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    cursor: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    connector_version: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_persisted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_sync_runs_store_started", "store_id", "started_at"),
    )


class RawPayload(Base, TimestampMixin):
    """Immutable raw marketplace payload for a single marketplace entity.

    The payload_hash allows deduplication: identical payloads from the same
    marketplace, store, entity type, and external id are not stored twice.
    """

    __tablename__ = "raw_payloads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sync_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    marketplace_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    connector_version: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "marketplace_code",
            "store_id",
            "entity_type",
            "external_entity_id",
            "payload_hash",
            name="uq_raw_payload_identity",
        ),
        Index("ix_raw_payloads_sync_run", "sync_run_id", "entity_type"),
    )


class SyncProvenance(Base, TimestampMixin):
    """Provenance link between a canonical record and the raw payload that produced it.

    There is one row per canonical record. It tells us exactly where the record
    came from: marketplace, store, external id, sync run, and connector version.
    """

    __tablename__ = "sync_provenance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    canonical_entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    canonical_entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    raw_payload_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    marketplace_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    external_entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sync_run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    connector_version: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "canonical_entity_type",
            "canonical_entity_id",
            name="uq_sync_provenance_canonical",
        ),
        Index(
            "ix_sync_provenance_lookup",
            "marketplace_code",
            "store_id",
            "external_entity_id",
        ),
    )


class SyncCheckpoint(Base, TimestampMixin):
    """Last successful synchronization position for a connector, store, and entity type.

    The Sync Engine resumes from this checkpoint rather than inferring state from
    SyncRun history. This keeps resume logic deterministic and simple.
    """

    __tablename__ = "sync_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    connector_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    store_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    cursor: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_successful_sync_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: utc_now()
    )
    connector_version: Mapped[str] = mapped_column(String(50), nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint(
            "connector_code",
            "store_id",
            "entity_type",
            "sync_mode",
            name="uq_sync_checkpoint_scope",
        ),
    )
