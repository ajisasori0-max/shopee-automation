"""Idempotency tests for canonical AdPerformance persistence through SyncEngine."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from commerceos.commerce.models import Ad, AdPerformance, Campaign
from commerceos.connectors.core import (
    ConnectorAuth,
    ConnectorHealth,
    ConnectorResult,
    MarketplaceConnector,
    SyncMode,
)
from commerceos.connectors.core.mapper import CanonicalEntity, Mapper
from commerceos.ingestion import SyncEngine, sqlalchemy_ingestion_uow
from commerceos.ingestion.models import SyncRun
from commerceos.platform.database.connection import create_all, get_session, reset_engine

DATABASE_URL = "sqlite:///:memory:"


class FakeAuth(ConnectorAuth):
    def get_credentials(self):
        return {}

    def refresh(self):
        return ConnectorResult.ok()

    @property
    def is_authenticated(self):
        return True


class FakeConnector(MarketplaceConnector):
    """Connector that yields a deterministic daily ad performance payload."""

    def __init__(self, payloads=None, version="1.0.0"):
        self._payloads = payloads or []
        self._version = version
        self._auth = FakeAuth()

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
        return ConnectorResult.ok(data=[])

    def fetch_products(self, sync_mode=SyncMode.INCREMENTAL, cursor=None, **kwargs):
        return ConnectorResult.ok(data=[])

    def fetch_inventory(self, sync_mode=SyncMode.INCREMENTAL, cursor=None, **kwargs):
        return ConnectorResult.ok(data=[])

    def fetch_payments(self, sync_mode=SyncMode.INCREMENTAL, cursor=None, **kwargs):
        return ConnectorResult.ok(data=[])

    def fetch_ads(self, sync_mode=SyncMode.INCREMENTAL, cursor=None, **kwargs):
        return ConnectorResult.ok(data=[])

    def fetch_ad_performances(self, sync_mode=SyncMode.INCREMENTAL, cursor=None, **kwargs):
        return ConnectorResult.ok(
            data=self._payloads,
            metadata={"cursor": None, "source_timestamp": "2026-08-11T00:00:00+00:00"},
        )


class FakeAdPerformanceMapper(Mapper):
    """Mapper that mimics ShopeeAdsPerformanceMapper output using canonical IDs."""

    def __init__(self, ad_id: str, campaign_id: str):
        self.ad_id = ad_id
        self.campaign_id = campaign_id

    def map(self, raw_payload: dict):
        date_str = str(raw_payload.get("date", ""))
        perf_date = datetime.strptime(date_str, "%d-%m-%Y").replace(tzinfo=timezone.utc)
        return [
            CanonicalEntity(
                entity_type="ad_performance",
                external_entity_id=f"{self.ad_id}-{date_str}",
                model_class=AdPerformance,
                data={
                    "ad_id": self.ad_id,
                    "campaign_id": self.campaign_id,
                    "date": perf_date,
                    "impressions": int(raw_payload.get("impression", 0)),
                    "clicks": int(raw_payload.get("clicks", 0)),
                    "conversions": int(raw_payload.get("direct_order", 0)),
                    "spend": Decimal(str(raw_payload.get("expense", 0))),
                    "revenue": Decimal(str(raw_payload.get("direct_gmv", 0))),
                    "roas": Decimal(str(raw_payload.get("direct_roas", 0)))
                    if raw_payload.get("direct_roas") is not None
                    else None,
                    "currency": "IDR",
                    "marketplace_metadata": raw_payload,
                    "organization_id": "org-1",
                    "business_id": "biz-1",
                    "store_id": "store-1",
                },
            )
        ]


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
def seeded_session(session):
    """Seed an Ad + Campaign so the mapper can reference canonical IDs."""
    with session:
        campaign = Campaign(
            id="campaign-1",
            marketplace_campaign_id="shop-total",
            name="Shop Total",
            campaign_type=" CPC",
            status="ACTIVE",
            organization_id="org-1",
            business_id="biz-1",
            store_id="store-1",
        )
        ad = Ad(
            id="ad-1",
            campaign_id="campaign-1",
            marketplace_ad_id="shop-total",
            name="Shop Total Ad",
            ad_type=" CPC",
            status="ACTIVE",
            organization_id="org-1",
            business_id="biz-1",
            store_id="store-1",
        )
        session.add(campaign)
        session.add(ad)
        session.commit()
    return session


def _payload(date_str="11-08-2026", impressions=100, clicks=10, conversions=1, expense="50000", direct_gmv="100000", direct_roas="2.0"):
    return {
        "campaign_id": "shop-total",
        "ad_id": "shop-total",
        "date": date_str,
        "impression": impressions,
        "clicks": clicks,
        "direct_order": conversions,
        "expense": expense,
        "direct_gmv": direct_gmv,
        "direct_roas": direct_roas,
    }


def test_ad_performance_first_sync_inserts(seeded_session):
    connector = FakeConnector(payloads=[_payload()])
    mapper = FakeAdPerformanceMapper(ad_id="ad-1", campaign_id="campaign-1")
    with sqlalchemy_ingestion_uow(seeded_session) as uow:
        engine = SyncEngine(uow=uow)
        engine.register_mapper("ad_performances", mapper)
        result = engine.sync(connector, entity_type="ad_performances", store_id="store-1")

    assert result.success is True
    with seeded_session:
        assert seeded_session.query(AdPerformance).count() == 1
        perf = seeded_session.query(AdPerformance).one()
        assert perf.spend == Decimal("50000")
        assert perf.revenue == Decimal("100000")


def test_ad_performance_second_sync_does_not_fail(seeded_session):
    payload = _payload()
    connector = FakeConnector(payloads=[payload])
    mapper = FakeAdPerformanceMapper(ad_id="ad-1", campaign_id="campaign-1")
    with sqlalchemy_ingestion_uow(seeded_session) as uow:
        engine = SyncEngine(uow=uow)
        engine.register_mapper("ad_performances", mapper)
        engine.sync(connector, entity_type="ad_performances", store_id="store-1")
        # Same payload again; should not raise or fail.
        result2 = engine.sync(connector, entity_type="ad_performances", store_id="store-1")

    assert result2.success is True
    with seeded_session:
        assert seeded_session.query(AdPerformance).count() == 1


def test_ad_performance_second_sync_updates_values(seeded_session):
    payload1 = _payload(direct_gmv="100000", direct_roas="2.0")
    payload2 = _payload(direct_gmv="200000", direct_roas="4.0")
    connector1 = FakeConnector(payloads=[payload1])
    connector2 = FakeConnector(payloads=[payload2])
    mapper = FakeAdPerformanceMapper(ad_id="ad-1", campaign_id="campaign-1")
    with sqlalchemy_ingestion_uow(seeded_session) as uow:
        engine = SyncEngine(uow=uow)
        engine.register_mapper("ad_performances", mapper)
        engine.sync(connector1, entity_type="ad_performances", store_id="store-1")
        result2 = engine.sync(connector2, entity_type="ad_performances", store_id="store-1")
    assert result2.success is True
    with seeded_session:
        perf = seeded_session.query(AdPerformance).one()
        assert perf.revenue == Decimal("200000")
        assert perf.roas == Decimal("4.0")


def test_ad_performance_no_duplicate_canonical_rows(seeded_session):
    payload = _payload()
    connector = FakeConnector(payloads=[payload])
    mapper = FakeAdPerformanceMapper(ad_id="ad-1", campaign_id="campaign-1")
    with sqlalchemy_ingestion_uow(seeded_session) as uow:
        engine = SyncEngine(uow=uow)
        engine.register_mapper("ad_performances", mapper)
        engine.sync(connector, entity_type="ad_performances", store_id="store-1")
        engine.sync(connector, entity_type="ad_performances", store_id="store-1")
        engine.sync(connector, entity_type="ad_performances", store_id="store-1")

    with seeded_session:
        assert seeded_session.query(AdPerformance).count() == 1
        assert seeded_session.query(SyncRun).filter(SyncRun.status == "completed").count() == 3
