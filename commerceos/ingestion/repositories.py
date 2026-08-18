"""Repository interfaces for the Ingestion bounded context.

These interfaces isolate the Sync Engine from SQLAlchemy. They can be replaced
with PostgreSQL, S3, Kafka, or any other durable store without changing the engine.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from commerceos.ingestion.models import SyncRun, RawPayload, SyncProvenance, SyncCheckpoint


class SyncRunRepository(ABC):
    """Store and retrieve sync run lifecycle records."""

    @abstractmethod
    def create(self, sync_run: SyncRun) -> SyncRun:
        """Persist a new sync run."""
        raise NotImplementedError

    @abstractmethod
    def update(self, sync_run: SyncRun) -> SyncRun:
        """Update an existing sync run."""
        raise NotImplementedError

    @abstractmethod
    def get(self, sync_run_id: str) -> Optional[SyncRun]:
        """Retrieve a sync run by id."""
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        connector_code: Optional[str] = None,
        store_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[SyncRun]:
        """List sync runs, optionally filtered."""
        raise NotImplementedError


class RawPayloadRepository(ABC):
    """Persist and retrieve immutable raw marketplace payloads."""

    @abstractmethod
    def save(self, payload: RawPayload) -> RawPayload:
        """Persist a raw payload. Idempotent by identity+hash."""
        raise NotImplementedError

    @abstractmethod
    def save_many(self, payloads: List[RawPayload]) -> List[RawPayload]:
        """Persist multiple raw payloads."""
        raise NotImplementedError

    @abstractmethod
    def get(self, raw_payload_id: str) -> Optional[RawPayload]:
        """Retrieve a raw payload by id."""
        raise NotImplementedError

    @abstractmethod
    def find_by_external_id(
        self,
        marketplace_code: str,
        store_id: str,
        entity_type: str,
        external_entity_id: str,
    ) -> List[RawPayload]:
        """Find raw payloads for a specific external entity."""
        raise NotImplementedError

    @abstractmethod
    def exists_by_hash(
        self,
        marketplace_code: str,
        store_id: str,
        entity_type: str,
        external_entity_id: str,
        payload_hash: str,
    ) -> bool:
        """Return True if an identical payload already exists."""
        raise NotImplementedError


class SyncProvenanceRepository(ABC):
    """Store and retrieve provenance links between raw and canonical records."""

    @abstractmethod
    def record(self, provenance: SyncProvenance) -> SyncProvenance:
        """Record or update provenance for a canonical entity."""
        raise NotImplementedError

    @abstractmethod
    def record_many(self, provenance_entries: List[SyncProvenance]) -> List[SyncProvenance]:
        """Record or update provenance for many canonical entities."""
        raise NotImplementedError

    @abstractmethod
    def get_by_canonical(
        self, canonical_entity_type: str, canonical_entity_id: str
    ) -> Optional[SyncProvenance]:
        """Get provenance for a canonical entity."""
        raise NotImplementedError

    @abstractmethod
    def get_by_external(
        self,
        marketplace_code: str,
        store_id: str,
        external_entity_id: str,
    ) -> List[SyncProvenance]:
        """Get provenance entries for an external entity."""
        raise NotImplementedError


class SyncCheckpointRepository(ABC):
    """Store and retrieve sync checkpoints for resume semantics."""

    @abstractmethod
    def get(
        self,
        connector_code: str,
        store_id: str,
        entity_type: str,
        sync_mode: str,
    ) -> Optional[SyncCheckpoint]:
        """Get the latest checkpoint for a scope."""
        raise NotImplementedError

    @abstractmethod
    def save(self, checkpoint: SyncCheckpoint) -> SyncCheckpoint:
        """Save or overwrite the checkpoint for a scope."""
        raise NotImplementedError

    @abstractmethod
    def list(self, connector_code: Optional[str] = None, store_id: Optional[str] = None) -> List[SyncCheckpoint]:
        """List checkpoints."""
        raise NotImplementedError


class IngestionUnitOfWork(ABC):
    """Boundary for atomic ingestion operations."""

    @abstractmethod
    def __enter__(self) -> "IngestionUnitOfWork":
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        raise NotImplementedError

    @abstractmethod
    def sync_runs(self) -> SyncRunRepository:
        raise NotImplementedError

    @abstractmethod
    def raw_payloads(self) -> RawPayloadRepository:
        raise NotImplementedError

    @abstractmethod
    def provenance(self) -> SyncProvenanceRepository:
        raise NotImplementedError

    @abstractmethod
    def checkpoints(self) -> SyncCheckpointRepository:
        raise NotImplementedError

    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def rollback(self) -> None:
        raise NotImplementedError
