import pytest
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from commerceos.platform.database.connection import get_session, reset_engine, create_all
from commerceos.ingestion import (
    SyncEngine,
    CanonicalEntity,
    Mapper,
    sqlalchemy_ingestion_uow,
    SyncCheckpoint,
    RawPayload,
    SyncProvenance,
)
from commerceos.ingestion.models import SyncRun
from commerceos.commerce.models import Order
from commerceos.connectors.core import (
    MarketplaceConnector,
    ConnectorAuth,
    ConnectorResult,
    ConnectorHealth,
    SyncMode,
)


DATABASE_URL = "sqlite:///:memory:"


class FakeAuth(ConnectorAuth):
    def get_credentials(self):
        return {}

    def refresh(self):
        return ConnectorResult.ok()

    @property
    def is_authenticated(self):
        return True


class FakeMapper(Mapper):
    def map(self, raw_payload):
        return [
            CanonicalEntity(
                entity_type="order",
                external_entity_id=str(raw_payload["id"]),
                model_class=Order,
                data={
                    "marketplace_order_id": str(raw_payload["id"]),
                    "status": raw_payload.get("status", "pending"),
                    "payment_status": "pending",
                    "currency": "IDR",
                    "subtotal": Decimal("100000"),
                    "shipping_cost": Decimal("10000"),
                    "discount": Decimal("0"),
                    "tax": Decimal("0"),
                    "total_amount": Decimal("110000"),
                    "platform_fee": Decimal("0"),
                    "commission": Decimal("0"),
                    "shipping_subsidy": Decimal("0"),
                    "ordered_at": datetime.now(timezone.utc),
                    "organization_id": str(uuid.uuid4()),
                    "business_id": str(uuid.uuid4()),
                    "store_id": str(uuid.uuid4()),
                },
            )
        ]


class FakeConnector(MarketplaceConnector):
    def __init__(self, payloads=None, version="1.0.0"):
        self._payloads = payloads or []
        self._version = version
        self._auth = FakeAuth()
        self.fetch_calls = []

    @property
    def marketplace_code(self):
        return "fake"

    @property
    def name(self):
        return "Fake Marketplace"

    @property
    def version(self):
        return self._version

    @property
    def auth(self):
        return self._auth

    def health(self):
        return ConnectorHealth(authenticated=True, status="healthy")

    def fetch_orders(self, sync_mode=SyncMode.INCREMENTAL, cursor=None, **kwargs):
        self.fetch_calls.append({"sync_mode": sync_mode, "cursor": cursor})
        return ConnectorResult.ok(
            data=self._payloads,
            metadata={"cursor": "next-cursor-123"},
        )

    def fetch_products(self, sync_mode=SyncMode.INCREMENTAL, cursor=None, **kwargs):
        return ConnectorResult.ok(data=[])

    def fetch_inventory(self, sync_mode=SyncMode.INCREMENTAL, cursor=None, **kwargs):
        return ConnectorResult.ok(data=[])

    def fetch_payments(self, sync_mode=SyncMode.INCREMENTAL, cursor=None, **kwargs):
        return ConnectorResult.ok(data=[])

    def fetch_ads(self, sync_mode=SyncMode.INCREMENTAL, cursor=None, **kwargs):
        return ConnectorResult.ok(data=[])


@pytest.fixture
def session():
    reset_engine()
    create_all(DATABASE_URL)
    sess = get_session(DATABASE_URL)
    try:
        yield sess
    finally:
        sess.close()
        reset_engine()


@pytest.fixture
def engine(session):
    engine = SyncEngine(uow=sqlalchemy_ingestion_uow(session).__enter__())
    engine.register_mapper("order", FakeMapper())
    return engine


def test_sync_creates_sync_run_and_checkpoint(session):
    connector = FakeConnector(payloads=[{"id": "order-1", "status": "completed"}])
    engine = SyncEngine(uow=sqlalchemy_ingestion_uow(session).__enter__())
    engine.register_mapper("orders", FakeMapper())

    result = engine.sync(connector, entity_type="orders", store_id="store-1")

    assert result.success is True
    assert result.metadata["records_received"] == 1
    assert result.metadata["records_persisted"] == 1
    assert result.metadata["cursor"] == "next-cursor-123"

    with session:
        sync_runs = session.query(SyncRun).all()
        assert len(sync_runs) == 1
        assert sync_runs[0].status == "completed"

        checkpoints = session.query(SyncCheckpoint).all()
        assert len(checkpoints) == 1
        assert checkpoints[0].cursor == "next-cursor-123"


def test_sync_is_idempotent(session):
    connector = FakeConnector(payloads=[{"id": "order-1", "status": "completed"}])
    engine = SyncEngine(uow=sqlalchemy_ingestion_uow(session).__enter__())
    engine.register_mapper("orders", FakeMapper())

    engine.sync(connector, entity_type="orders", store_id="store-1")
    engine.sync(connector, entity_type="orders", store_id="store-1")

    with session:
        raw_count = session.query(RawPayload).count()
        order_count = session.query(Order).count()
        assert raw_count == 1
        assert order_count == 1


def test_sync_resumes_from_checkpoint(session):
    connector = FakeConnector(payloads=[{"id": "order-1", "status": "completed"}])
    engine = SyncEngine(uow=sqlalchemy_ingestion_uow(session).__enter__())
    engine.register_mapper("orders", FakeMapper())

    engine.sync(connector, entity_type="orders", store_id="store-1")
    assert connector.fetch_calls[-1]["cursor"] is None

    engine.sync(connector, entity_type="orders", store_id="store-1")
    assert connector.fetch_calls[-1]["cursor"] == "next-cursor-123"


def test_failed_sync_does_not_update_checkpoint(session):
    connector = FakeConnector(payloads=[])

    def failing_fetch(*args, **kwargs):
        return ConnectorResult.failed("boom", error_code="E001")

    connector.fetch_orders = failing_fetch

    engine = SyncEngine(uow=sqlalchemy_ingestion_uow(session).__enter__())
    engine.register_mapper("orders", FakeMapper())

    result = engine.sync(connector, entity_type="orders", store_id="store-1")

    assert result.success is False

    with session:
        checkpoints = session.query(SyncCheckpoint).all()
        assert len(checkpoints) == 0


def test_provenance_recorded(session):
    connector = FakeConnector(payloads=[{"id": "order-1", "status": "completed"}])
    engine = SyncEngine(uow=sqlalchemy_ingestion_uow(session).__enter__())
    engine.register_mapper("orders", FakeMapper())

    engine.sync(connector, entity_type="orders", store_id="store-1")

    with session:
        provenance = session.query(SyncProvenance).all()
        assert len(provenance) == 1
        assert provenance[0].marketplace_code == "fake"
        assert provenance[0].external_entity_id == "order-1"
        assert provenance[0].raw_payload_id is not None


def test_duplicate_raw_payloads_are_deduplicated(session):
    connector = FakeConnector(payloads=[{"id": "order-1", "status": "completed"}])
    engine = SyncEngine(uow=sqlalchemy_ingestion_uow(session).__enter__())
    engine.register_mapper("orders", FakeMapper())

    engine.sync(connector, entity_type="orders", store_id="store-1")
    engine.sync(connector, entity_type="orders", store_id="store-1")

    with session:
        assert session.query(RawPayload).count() == 1
        assert session.query(SyncRun).count() == 2
