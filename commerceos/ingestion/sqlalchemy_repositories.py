"""SQLAlchemy implementations of Ingestion repositories."""

from contextlib import contextmanager
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from commerceos.ingestion.models import SyncRun, RawPayload, SyncProvenance, SyncCheckpoint
from commerceos.ingestion.repositories import (
    SyncRunRepository,
    RawPayloadRepository,
    SyncProvenanceRepository,
    SyncCheckpointRepository,
    IngestionUnitOfWork,
)


class SQLAlchemySyncRunRepository(SyncRunRepository):
    def __init__(self, session: Session):
        self.session = session

    def create(self, sync_run: SyncRun) -> SyncRun:
        self.session.add(sync_run)
        self.session.flush()
        return sync_run

    def update(self, sync_run: SyncRun) -> SyncRun:
        self.session.merge(sync_run)
        self.session.flush()
        return sync_run

    def get(self, sync_run_id: str) -> Optional[SyncRun]:
        return self.session.query(SyncRun).filter_by(id=sync_run_id).first()

    def list(
        self,
        connector_code: Optional[str] = None,
        store_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[SyncRun]:
        query = self.session.query(SyncRun).order_by(SyncRun.created_at.desc())
        if connector_code:
            query = query.filter_by(connector_code=connector_code)
        if store_id:
            query = query.filter_by(store_id=store_id)
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        return query.limit(limit).all()


class SQLAlchemyRawPayloadRepository(RawPayloadRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, payload: RawPayload) -> RawPayload:
        self.session.add(payload)
        self.session.flush()
        return payload

    def save_many(self, payloads: List[RawPayload]) -> List[RawPayload]:
        for payload in payloads:
            self.session.add(payload)
        self.session.flush()
        return payloads

    def get(self, raw_payload_id: str) -> Optional[RawPayload]:
        return self.session.query(RawPayload).filter_by(id=raw_payload_id).first()

    def find_by_external_id(
        self,
        marketplace_code: str,
        store_id: str,
        entity_type: str,
        external_entity_id: str,
    ) -> List[RawPayload]:
        return (
            self.session.query(RawPayload)
            .filter_by(
                marketplace_code=marketplace_code,
                store_id=store_id,
                entity_type=entity_type,
                external_entity_id=external_entity_id,
            )
            .order_by(RawPayload.fetched_at.desc())
            .all()
        )

    def exists_by_hash(
        self,
        marketplace_code: str,
        store_id: str,
        entity_type: str,
        external_entity_id: str,
        payload_hash: str,
    ) -> bool:
        return (
            self.session.query(RawPayload)
            .filter_by(
                marketplace_code=marketplace_code,
                store_id=store_id,
                entity_type=entity_type,
                external_entity_id=external_entity_id,
                payload_hash=payload_hash,
            )
            .first()
            is not None
        )


class SQLAlchemySyncProvenanceRepository(SyncProvenanceRepository):
    def __init__(self, session: Session):
        self.session = session

    def record(self, provenance: SyncProvenance) -> SyncProvenance:
        existing = self.get_by_canonical(
            provenance.canonical_entity_type, provenance.canonical_entity_id
        )
        if existing is not None:
            # Update the existing provenance with latest sync run / timestamp.
            existing.raw_payload_id = provenance.raw_payload_id
            existing.sync_run_id = provenance.sync_run_id
            existing.synced_at = provenance.synced_at
            existing.connector_version = provenance.connector_version
            self.session.merge(existing)
            self.session.flush()
            return existing
        self.session.merge(provenance)
        self.session.flush()
        return provenance

    def record_many(self, provenance_entries: List[SyncProvenance]) -> List[SyncProvenance]:
        results = []
        for entry in provenance_entries:
            results.append(self.record(entry))
        self.session.flush()
        return results

    def get_by_canonical(
        self, canonical_entity_type: str, canonical_entity_id: str
    ) -> Optional[SyncProvenance]:
        return (
            self.session.query(SyncProvenance)
            .filter_by(
                canonical_entity_type=canonical_entity_type,
                canonical_entity_id=canonical_entity_id,
            )
            .first()
        )

    def get_by_external(
        self,
        marketplace_code: str,
        store_id: str,
        external_entity_id: str,
    ) -> List[SyncProvenance]:
        return (
            self.session.query(SyncProvenance)
            .filter_by(
                marketplace_code=marketplace_code,
                store_id=store_id,
                external_entity_id=external_entity_id,
            )
            .all()
        )


class SQLAlchemySyncCheckpointRepository(SyncCheckpointRepository):
    def __init__(self, session: Session):
        self.session = session

    def get(
        self,
        connector_code: str,
        store_id: str,
        entity_type: str,
        sync_mode: str,
    ) -> Optional[SyncCheckpoint]:
        return (
            self.session.query(SyncCheckpoint)
            .filter_by(
                connector_code=connector_code,
                store_id=store_id,
                entity_type=entity_type,
                sync_mode=sync_mode,
            )
            .first()
        )

    def save(self, checkpoint: SyncCheckpoint) -> SyncCheckpoint:
        # Explicit upsert by natural identity (connector_code, store_id, entity_type, sync_mode).
        existing = (
            self.session.query(SyncCheckpoint)
            .filter_by(
                connector_code=checkpoint.connector_code,
                store_id=checkpoint.store_id,
                entity_type=checkpoint.entity_type,
                sync_mode=checkpoint.sync_mode,
            )
            .first()
        )

        if existing is not None:
            existing.cursor = checkpoint.cursor
            existing.last_successful_sync_at = checkpoint.last_successful_sync_at
            existing.connector_version = checkpoint.connector_version
            existing.extra_metadata = checkpoint.extra_metadata
            existing.updated_at = checkpoint.updated_at
            self.session.flush()
            return existing

        self.session.add(checkpoint)
        self.session.flush()
        return checkpoint

    def list(
        self, connector_code: Optional[str] = None, store_id: Optional[str] = None
    ) -> List[SyncCheckpoint]:
        query = self.session.query(SyncCheckpoint)
        if connector_code:
            query = query.filter_by(connector_code=connector_code)
        if store_id:
            query = query.filter_by(store_id=store_id)
        return query.all()


class SQLAlchemyIngestionUnitOfWork(IngestionUnitOfWork):
    """SQLAlchemy-backed unit of work for the Ingestion context."""

    def __init__(self, session: Session):
        self.session = session
        self._sync_runs = SQLAlchemySyncRunRepository(session)
        self._raw_payloads = SQLAlchemyRawPayloadRepository(session)
        self._provenance = SQLAlchemySyncProvenanceRepository(session)
        self._checkpoints = SQLAlchemySyncCheckpointRepository(session)

    def __enter__(self) -> "SQLAlchemyIngestionUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def sync_runs(self) -> SyncRunRepository:
        return self._sync_runs

    def raw_payloads(self) -> RawPayloadRepository:
        return self._raw_payloads

    def provenance(self) -> SyncProvenanceRepository:
        return self._provenance

    def checkpoints(self) -> SyncCheckpointRepository:
        return self._checkpoints

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()


@contextmanager
def sqlalchemy_ingestion_uow(session: Session):
    uow = SQLAlchemyIngestionUnitOfWork(session)
    try:
        yield uow
        uow.commit()
    except Exception:
        uow.rollback()
        raise
