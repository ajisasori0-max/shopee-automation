"""Sync Engine: the orchestrator between Marketplace Connectors and the Ingestion context.

The Sync Engine is responsible for:
- Starting a SyncRun
- Reading the last checkpoint for a connector/store/entity scope
- Invoking the connector's fetch method
- Persisting raw payloads via the Ingestion context
- Mapping raw payloads to canonical entities via connector-provided mappers
- Upserting canonical entities
- Recording provenance
- Saving the next checkpoint
- Marking the SyncRun as completed or failed

It does NOT compute KPIs, apply business rules, generate Commerce State, or
execute automations. It only retrieves, translates, and persists.
"""
from commerceos.shared.value_objects.primitives import utc_now

from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple
import hashlib
import json
import uuid

from sqlalchemy import and_, Date, DateTime, func, or_, tuple_

from commerceos.connectors.core.interfaces import MarketplaceConnector, ConnectorResult, SyncMode
from commerceos.connectors.core.mapper import CanonicalEntity, Mapper
from commerceos.ingestion.models import SyncRun, RawPayload, SyncProvenance, SyncCheckpoint
from commerceos.ingestion.repositories import IngestionUnitOfWork


# Natural key columns per canonical model class. Used to resolve existing rows
# during incremental sync so session.merge updates instead of inserting duplicates.
NATURAL_KEYS: Dict[str, List[str]] = {
    "Order": ["organization_id", "business_id", "store_id", "marketplace_order_id"],
    "Variant": ["organization_id", "business_id", "store_id", "sku"],
    "Campaign": ["organization_id", "business_id", "store_id", "marketplace_campaign_id"],
    "AdPerformance": ["ad_id", "date"],
    "Product": ["organization_id", "business_id", "store_id", "sku"],
    "Inventory": ["organization_id", "business_id", "store_id", "variant_id"],
}


def _model_name(model_class: type) -> str:
    return model_class.__name__


def _natural_key_tuple(model_class: type, data: Dict[str, Any]) -> Optional[Tuple[str, ...]]:
    """Return a hashable natural-key tuple for a model class and data, or None."""
    key_cols = NATURAL_KEYS.get(_model_name(model_class))
    if not key_cols:
        return None
    try:
        return tuple(_normalize_natural_key_value(data.get(col)) for col in key_cols)
    except Exception:
        return None


def _normalize_natural_key_value(value: Any) -> Any:
    """Normalize a natural-key value to a deterministic, hashable value.

    SQLAlchemy DateTime columns round-trip as ``datetime`` objects, while the
    incoming data may contain naive or timezone-aware datetimes. Canonical
    natural-key upsert must compare the same logical value regardless of
    representation. Naive datetimes are assumed to be UTC.

    DateTime natural keys are normalized to ``datetime.date`` so that database
    lookups can use ``func.date(col) == value`` and string comparisons do not
    mismatch against stored timestamps such as ``2026-08-11 00:00:00.000000``.
    """
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.date()
    if isinstance(value, date):
        return value
    return str(value)


class CanonicalEntity:
    """Lightweight container for a canonical entity before persistence."""

    def __init__(
        self,
        entity_type: str,
        external_entity_id: str,
        model_class: type,
        data: Dict[str, Any],
        children: Optional[List["CanonicalEntity"]] = None,
        parent_external_id: Optional[str] = None,
        parent_field: Optional[str] = None,
    ):
        self.entity_type = entity_type
        self.external_entity_id = external_entity_id
        self.model_class = model_class
        self.data = data
        self.children = children or []
        self.parent_external_id = parent_external_id
        self.parent_field = parent_field


class Mapper(ABC):
    """Abstract mapper from raw marketplace payload to canonical entity/entities."""

    @abstractmethod
    def map(self, raw_payload: Dict[str, Any]) -> List[CanonicalEntity]:
        """Map a raw payload to one or more canonical entities."""
        raise NotImplementedError


class SyncEngine:
    """Deterministic, idempotent, restart-safe sync engine."""

    def __init__(
        self,
        uow: IngestionUnitOfWork,
        mapper_registry: Optional[Dict[str, Mapper]] = None,
    ):
        self.uow = uow
        self.mapper_registry = mapper_registry or {}

    def register_mapper(self, entity_type: str, mapper: Mapper) -> None:
        self.mapper_registry[entity_type] = mapper

    def sync(
        self,
        connector: MarketplaceConnector,
        entity_type: str,
        store_id: str,
        sync_mode: SyncMode = SyncMode.INCREMENTAL,
        fetch_fn: Optional[Callable[..., ConnectorResult]] = None,
        request_id: Optional[str] = None,
    ) -> ConnectorResult:
        """Run a sync for a connector, entity type, and store.

        Returns a ConnectorResult describing the outcome. On failure, the sync
        run is recorded with status 'failed' and the checkpoint is NOT updated,
        so the next sync can resume from the last known good position.
        """
        connector_code = connector.marketplace_code
        connector_version = connector.version
        request_id = request_id or str(uuid.uuid4())

        # Start sync run
        sync_run = SyncRun(
            request_id=request_id,
            connector_code=connector_code,
            store_id=store_id,
            entity_type=entity_type,
            sync_mode=sync_mode.value,
            connector_version=connector_version,
            status="running",
        )

        with self.uow:
            self.uow.sync_runs().create(sync_run)

        try:
            # Read checkpoint
            with self.uow:
                checkpoint = self.uow.checkpoints().get(
                    connector_code=connector_code,
                    store_id=store_id,
                    entity_type=entity_type,
                    sync_mode=sync_mode.value,
                )
            cursor = checkpoint.cursor if checkpoint else None

            # Fetch from connector
            fetch_fn = fetch_fn or self._default_fetch_fn(connector, entity_type)
            result = fetch_fn(sync_mode=sync_mode, cursor=cursor)

            if not result.success:
                return self._fail_sync_run(sync_run, result)

            raw_payloads = result.data or []
            next_cursor = result.metadata.get("cursor")
            source_timestamp = result.metadata.get("source_timestamp")
            fetched_at = utc_now()

            # Persist raw payloads and map to canonical entities
            persisted_raw, canonical_entries, errors = self._persist_and_map(
                sync_run=sync_run,
                connector=connector,
                store_id=store_id,
                entity_type=entity_type,
                raw_payloads=raw_payloads,
                fetched_at=fetched_at,
            )

            if errors:
                return self._fail_sync_run(
                    sync_run,
                    ConnectorResult.failed(
                        f"Mapping failed for {len(errors)} records",
                        metadata={"errors": errors},
                    ),
                )

            # Upsert canonical entities and record provenance
            provenance_entries = self._upsert_canonical(
                sync_run=sync_run,
                connector=connector,
                store_id=store_id,
                entity_type=entity_type,
                canonical_entries=canonical_entries,
                raw_payloads=persisted_raw,
            )

            # Update checkpoint on success
            with self.uow:
                new_checkpoint = SyncCheckpoint(
                    connector_code=connector_code,
                    store_id=store_id,
                    entity_type=entity_type,
                    sync_mode=sync_mode.value,
                    cursor=next_cursor,
                    last_successful_sync_at=fetched_at,
                    connector_version=connector_version,
                    extra_metadata={"source_timestamp": source_timestamp, "request_id": request_id},
                )
                self.uow.checkpoints().save(new_checkpoint)

            # Mark sync run complete
            return self._complete_sync_run(
                sync_run=sync_run,
                records_received=len(raw_payloads),
                records_persisted=len(persisted_raw),
                records_failed=0,
                metadata={
                    "cursor": next_cursor,
                    "source_timestamp": source_timestamp,
                    "provenance_recorded": len(provenance_entries),
                },
            )

        except Exception as exc:
            return self._fail_sync_run(
                sync_run,
                ConnectorResult.from_exception(exc),
            )

    def _default_fetch_fn(
        self, connector: MarketplaceConnector, entity_type: str
    ) -> Callable[..., ConnectorResult]:
        fetch_methods = {
            "orders": "fetch_orders",
            "products": "fetch_products",
            "inventory": "fetch_inventory",
            "payments": "fetch_payments",
            "campaigns": "fetch_campaigns",
            "ad_performances": "fetch_ad_performances",
            "ads": "fetch_ads",
        }
        method_name = fetch_methods.get(entity_type)
        if method_name is None:
            raise ValueError(f"No fetch method for entity type: {entity_type}")
        return getattr(connector, method_name)

    def _persist_and_map(
        self,
        sync_run: SyncRun,
        connector: MarketplaceConnector,
        store_id: str,
        entity_type: str,
        raw_payloads: List[Dict[str, Any]],
        fetched_at: datetime,
    ) -> Tuple[List[RawPayload], List[CanonicalEntity], List[Dict[str, Any]]]:
        """Persist raw payloads and map them to canonical entities.

        Returns (persisted_raw, canonical_entries, errors).
        """
        mapper = self.mapper_registry.get(entity_type)
        if mapper is None and raw_payloads:
            return [], [], [{"message": f"No mapper registered for entity type: {entity_type}"}]

        persisted: List[RawPayload] = []
        canonical_entries: List[CanonicalEntity] = []
        errors: List[Dict[str, Any]] = []
        marketplace_code = connector.marketplace_code
        connector_version = connector.version

        with self.uow:
            for raw_data in raw_payloads:
                external_entity_id = str(
                    raw_data.get("id")
                    or raw_data.get("item_id")
                    or raw_data.get("model_id")
                    or raw_data.get("campaign_id")
                    or raw_data.get("ad_id")
                    or raw_data.get("order_sn")
                    or raw_data.get("payment_id")
                    or uuid.uuid4()
                )
                payload_json = json.dumps(raw_data, sort_keys=True, default=str)
                payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

                # Deduplication: skip identical payloads
                if self.uow.raw_payloads().exists_by_hash(
                    marketplace_code=marketplace_code,
                    store_id=store_id,
                    entity_type=entity_type,
                    external_entity_id=external_entity_id,
                    payload_hash=payload_hash,
                ):
                    continue

                raw_payload = RawPayload(
                    id=str(uuid.uuid4()),
                    sync_run_id=sync_run.id,
                    marketplace_code=marketplace_code,
                    store_id=store_id,
                    entity_type=entity_type,
                    external_entity_id=external_entity_id,
                    payload_hash=payload_hash,
                    payload=raw_data,
                    fetched_at=fetched_at,
                    connector_version=connector_version,
                )
                self.uow.raw_payloads().save(raw_payload)
                persisted.append(raw_payload)

                try:
                    canonical_entries.extend(mapper.map(raw_data))
                except Exception as exc:
                    errors.append({
                        "external_entity_id": external_entity_id,
                        "message": str(exc),
                    })

        return persisted, canonical_entries, errors

    def _upsert_canonical(
        self,
        sync_run: SyncRun,
        connector: MarketplaceConnector,
        store_id: str,
        entity_type: str,
        canonical_entries: List[CanonicalEntity],
        raw_payloads: List[RawPayload],
    ) -> List[SyncProvenance]:
        """Upsert canonical entities and record provenance.

        The canonical commerce domain is updated here, but only as a translation
        of raw payloads. The Ingestion context owns the sync lifecycle.

        Parent entities are persisted first so children can reference their
        generated canonical IDs. Provenance for children falls back to the parent
        raw payload when the child has no raw payload of its own.

        Natural-key upsert: before merging, load existing rows by their unique
        business keys and reuse their primary-key IDs so session.merge updates
        instead of inserting duplicates.
        """
        external_to_raw = {rp.external_entity_id: rp for rp in raw_payloads}
        provenance_entries: List[SyncProvenance] = []

        with self.uow:
            session = getattr(self.uow, "session", None)
            if session is None:
                raise RuntimeError("UoW does not expose a session; cannot persist canonical entities")

            # Pre-resolve existing canonical IDs by natural key for all entries.
            existing_ids = self._resolve_existing_ids(session, canonical_entries)

            # Track parent canonical IDs for child foreign key resolution.
            parent_ids: Dict[str, str] = {}
            parent_entries = [e for e in canonical_entries if e.parent_external_id is None]
            child_entries = [e for e in canonical_entries if e.parent_external_id is not None]

            # Persist parents first.
            for entry in parent_entries:
                data = dict(entry.data)
                nat_key = _natural_key_tuple(entry.model_class, data)
                existing_id = existing_ids.get(nat_key) if nat_key else None
                if existing_id:
                    data["id"] = existing_id
                model = entry.model_class(**data)
                merged = session.merge(model)
                session.flush()
                parent_ids[entry.external_entity_id] = str(merged.id)

                raw_payload = external_to_raw.get(entry.external_entity_id)
                if raw_payload is not None:
                    provenance = SyncProvenance(
                        canonical_entity_type=entry.entity_type,
                        canonical_entity_id=str(merged.id),
                        raw_payload_id=raw_payload.id,
                        marketplace_code=connector.marketplace_code,
                        store_id=store_id,
                        external_entity_id=entry.external_entity_id,
                        sync_run_id=sync_run.id,
                        synced_at=utc_now(),
                        connector_version=connector.version,
                    )
                    self.uow.provenance().record(provenance)
                    provenance_entries.append(provenance)

            # Persist children with resolved parent IDs.
            for entry in child_entries:
                data = dict(entry.data)
                if entry.parent_external_id and entry.parent_field:
                    parent_id = parent_ids.get(entry.parent_external_id)
                    if parent_id is None:
                        # Parent not in this sync run; resolve from existing provenance.
                        existing = self.uow.provenance().get_by_external(
                            marketplace_code=connector.marketplace_code,
                            store_id=store_id,
                            external_entity_id=entry.parent_external_id,
                        )
                        if existing:
                            parent_id = existing[0].canonical_entity_id
                    if parent_id:
                        data[entry.parent_field] = parent_id

                nat_key = _natural_key_tuple(entry.model_class, data)
                existing_id = existing_ids.get(nat_key) if nat_key else None
                if existing_id:
                    data["id"] = existing_id
                model = entry.model_class(**data)
                merged = session.merge(model)
                session.flush()

                raw_payload = external_to_raw.get(entry.external_entity_id) or (
                    external_to_raw.get(entry.parent_external_id) if entry.parent_external_id else None
                )
                if raw_payload is not None:
                    provenance = SyncProvenance(
                        canonical_entity_type=entry.entity_type,
                        canonical_entity_id=str(merged.id),
                        raw_payload_id=raw_payload.id,
                        marketplace_code=connector.marketplace_code,
                        store_id=store_id,
                        external_entity_id=entry.external_entity_id,
                        sync_run_id=sync_run.id,
                        synced_at=utc_now(),
                        connector_version=connector.version,
                    )
                    self.uow.provenance().record(provenance)
                    provenance_entries.append(provenance)

        return provenance_entries

    def _resolve_existing_ids(
        self,
        session,
        canonical_entries: List[CanonicalEntity],
    ) -> Dict[Tuple[Any, ...], str]:
        """Query existing canonical rows by natural keys and return id mapping.

        Natural keys may contain DateTime columns; values are normalized to
        ``datetime.date`` so comparisons are date- rather than timestamp-based.
        """
        result: Dict[Tuple[Any, ...], str] = {}
        if not canonical_entries:
            return result

        # Group entries by model class and natural-key columns.
        by_class: Dict[type, Dict[Tuple[str, ...], List[Tuple[Any, ...]]]] = {}
        for entry in canonical_entries:
            key_cols = NATURAL_KEYS.get(_model_name(entry.model_class))
            if not key_cols:
                continue
            nat_key = _natural_key_tuple(entry.model_class, entry.data)
            if nat_key is None:
                continue
            by_class.setdefault(entry.model_class, {}).setdefault(tuple(key_cols), []).append(nat_key)

        for model_class, key_cols_to_keys in by_class.items():
            key_cols = next(iter(key_cols_to_keys.keys()))
            keys = set(key_cols_to_keys[key_cols])
            # Query only for keys that have no empty/None components.
            valid_keys = [k for k in keys if None not in k and "" not in k]
            if not valid_keys:
                continue
            col_objects = [getattr(model_class, col) for col in key_cols]

            def _col_eq(col_obj: Any, value: Any) -> Any:
                if isinstance(col_obj.type, (Date, DateTime)) and isinstance(value, (date, datetime)):
                    return func.date(col_obj) == value
                return col_obj == value

            filters = [
                and_(*[_col_eq(col, val) for col, val in zip(col_objects, key_vals)])
                for key_vals in valid_keys
            ]
            existing = (
                session.query(*col_objects, model_class.id)
                .filter(or_(*filters))
                .all()
            )
            for row in existing:
                nat_key = tuple(_normalize_natural_key_value(row[i]) for i in range(len(key_cols)))
                result[nat_key] = str(row[-1])

        return result

    def _complete_sync_run(
        self,
        sync_run: SyncRun,
        records_received: int,
        records_persisted: int,
        records_failed: int,
        metadata: Dict[str, Any],
    ) -> ConnectorResult:
        sync_run.status = "completed"
        sync_run.completed_at = utc_now()
        sync_run.records_received = records_received
        sync_run.records_persisted = records_persisted
        sync_run.records_failed = records_failed
        sync_run.extra_metadata = metadata

        with self.uow:
            self.uow.sync_runs().update(sync_run)

        return ConnectorResult.ok(
            data={"sync_run_id": sync_run.id},
            metadata={
                "connector_code": sync_run.connector_code,
                "store_id": sync_run.store_id,
                "entity_type": sync_run.entity_type,
                "sync_mode": sync_run.sync_mode,
                "records_received": records_received,
                "records_persisted": records_persisted,
                "records_failed": records_failed,
                **metadata,
            },
        )

    def _fail_sync_run(
        self,
        sync_run: SyncRun,
        result: ConnectorResult,
    ) -> ConnectorResult:
        sync_run.status = "failed"
        sync_run.completed_at = utc_now()
        sync_run.errors = result.errors
        sync_run.extra_metadata = result.metadata

        with self.uow:
            self.uow.sync_runs().update(sync_run)

        return ConnectorResult.failed(
            message=f"Sync failed for {sync_run.connector_code}/{sync_run.entity_type}",
            metadata={
                "sync_run_id": sync_run.id,
                "connector_code": sync_run.connector_code,
                "store_id": sync_run.store_id,
                "entity_type": sync_run.entity_type,
                **result.to_dict(),
            },
        )

    @property
    def uow(self) -> IngestionUnitOfWork:
        return self._uow

    @uow.setter
    def uow(self, value: IngestionUnitOfWork) -> None:
        self._uow = value
