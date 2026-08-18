"""Raw payload audit utilities for the ingestion bounded context.

These helpers let you inspect what was fetched, detect gaps, and verify
provenance without writing ad-hoc SQL.
"""
from __future__ import annotations


from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.ingestion.models import RawPayload, SyncProvenance, SyncRun


def raw_payload_summary(session: Session, sync_run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return a summary of raw payloads, optionally filtered by sync run."""
    query = session.query(RawPayload)
    if sync_run_id:
        query = query.filter_by(sync_run_id=sync_run_id)
    payloads = query.order_by(RawPayload.fetched_at.desc()).all()

    return [
        {
            "id": p.id,
            "sync_run_id": p.sync_run_id,
            "marketplace_code": p.marketplace_code,
            "store_id": p.store_id,
            "entity_type": p.entity_type,
            "external_entity_id": p.external_entity_id,
            "payload_hash": p.payload_hash,
            "fetched_at": p.fetched_at.isoformat() if p.fetched_at else None,
            "connector_version": p.connector_version,
        }
        for p in payloads
    ]


def provenance_report(session: Session, canonical_entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return provenance entries, optionally filtered by canonical entity type."""
    query = session.query(SyncProvenance)
    if canonical_entity_type:
        query = query.filter_by(canonical_entity_type=canonical_entity_type)
    entries = query.order_by(SyncProvenance.synced_at.desc()).all()

    return [
        {
            "canonical_entity_type": e.canonical_entity_type,
            "canonical_entity_id": e.canonical_entity_id,
            "raw_payload_id": e.raw_payload_id,
            "marketplace_code": e.marketplace_code,
            "store_id": e.store_id,
            "external_entity_id": e.external_entity_id,
            "sync_run_id": e.sync_run_id,
            "synced_at": e.synced_at.isoformat() if e.synced_at else None,
        }
        for e in entries
    ]


def sync_run_report(session: Session, limit: int = 50) -> List[Dict[str, Any]]:
    """Return recent sync runs with error details."""
    runs = session.query(SyncRun).order_by(SyncRun.created_at.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "connector_code": r.connector_code,
            "store_id": r.store_id,
            "entity_type": r.entity_type,
            "sync_mode": r.sync_mode,
            "status": r.status,
            "records_received": r.records_received,
            "records_persisted": r.records_persisted,
            "records_failed": r.records_failed,
            "errors": r.errors,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


def find_missing_provenance(session: Session) -> List[Dict[str, Any]]:
    """Find canonical entities that have no provenance record.

    This indicates data that was written outside the ingestion pipeline or
    that a provenance write failed silently.
    """
    # Compare counts across tables
    from commerceos.commerce.models import Order, OrderItem, Payment, Campaign, Ad, AdPerformance

    checks = [
        ("order", Order),
        ("order_item", OrderItem),
        ("payment", Payment),
        ("campaign", Campaign),
        ("ad", Ad),
        ("ad_performance", AdPerformance),
    ]

    missing: List[Dict[str, Any]] = []
    for entity_type, model in checks:
        total = session.query(model).count()
        provenance_count = (
            session.query(SyncProvenance)
            .filter_by(canonical_entity_type=entity_type)
            .count()
        )
        if total > provenance_count:
            missing.append(
                {
                    "entity_type": entity_type,
                    "canonical_count": total,
                    "provenance_count": provenance_count,
                    "missing": total - provenance_count,
                }
            )
    return missing


def payload_diff(
    session: Session,
    marketplace_code: str,
    store_id: str,
    entity_type: str,
    external_entity_id: str,
) -> List[Dict[str, Any]]:
    """Return all raw payload versions for a given external entity.

    Useful for debugging: you can see exactly what Shopee returned each time
    the entity was synced, and compare payload hashes to detect changes.
    """
    payloads = (
        session.query(RawPayload)
        .filter_by(
            marketplace_code=marketplace_code,
            store_id=store_id,
            entity_type=entity_type,
            external_entity_id=external_entity_id,
        )
        .order_by(RawPayload.fetched_at.asc())
        .all()
    )

    return [
        {
            "id": p.id,
            "payload_hash": p.payload_hash,
            "fetched_at": p.fetched_at.isoformat() if p.fetched_at else None,
            "payload": p.payload,
        }
        for p in payloads
    ]
