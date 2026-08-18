"""Unit tests for Shopee ads mappers."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from commerceos.commerce.models import Ad, AdPerformance, Campaign
from commerceos.connectors.shopee.mappers import (
    ShopeeAdsPerformanceMapper,
    ShopeeCampaignMapper,
    ShopeeTenantContext,
)
from tests.fixtures.shopee_ads_responses import (
    ads_daily_performance_response,
    campaign_setting_info_response,
)


@pytest.fixture
def tenant():
    return ShopeeTenantContext(
        organization_id="org-1",
        business_id="biz-1",
        store_id="store-1",
        currency="IDR",
    )


class FakeProvenanceRepo:
    def __init__(self, entries=None):
        self.entries = entries or []

    def get_by_external(self, marketplace_code, store_id, external_entity_id):
        return [
            FakeProvenanceEntry(e)
            for e in self.entries
            if e["external_entity_id"] == external_entity_id
            and e["marketplace_code"] == marketplace_code
            and e["store_id"] == store_id
        ]


class FakeProvenanceEntry:
    def __init__(self, data):
        self.canonical_entity_id = data["canonical_entity_id"]
        self.external_entity_id = data["external_entity_id"]
        self.marketplace_code = data["marketplace_code"]
        self.store_id = data["store_id"]


def test_campaign_mapper_creates_campaign_and_ads(tenant):
    mapper = ShopeeCampaignMapper(tenant)
    raw = campaign_setting_info_response("camp-123")["response"]["campaign_list"][0]

    entities = mapper.map(raw)

    campaigns = [e for e in entities if e.entity_type == "campaign"]
    ads = [e for e in entities if e.entity_type == "ad"]

    assert len(campaigns) == 1
    assert len(ads) == 1

    camp = campaigns[0]
    assert camp.model_class == Campaign
    assert camp.data["marketplace_campaign_id"] == "camp-123"
    assert camp.data["name"] == "Campaign camp-123"
    assert camp.data["status"] == "ONGOING"
    assert camp.data["budget"] == Decimal("150000")

    ad = ads[0]
    assert ad.model_class == Ad
    assert ad.data["marketplace_ad_id"] == "ad-camp-123-1"
    assert ad.data["name"] == "Ad camp-123-1"
    assert ad.parent_external_id == "camp-123"
    assert ad.parent_field == "campaign_id"


def test_campaign_mapper_requires_campaign_id(tenant):
    mapper = ShopeeCampaignMapper(tenant)
    with pytest.raises(ValueError, match="campaign_id"):
        mapper.map({})


def test_ads_performance_mapper_creates_ad_performance(tenant):
    provenance = FakeProvenanceRepo(entries=[
        {
            "external_entity_id": "camp-123",
            "canonical_entity_id": "canonical-camp-uuid",
            "marketplace_code": "shopee",
            "store_id": "store-1",
        },
        {
            "external_entity_id": "ad-camp-123-1",
            "canonical_entity_id": "canonical-ad-uuid",
            "marketplace_code": "shopee",
            "store_id": "store-1",
        },
    ])
    mapper = ShopeeAdsPerformanceMapper(tenant, provenance, store_id="store-1")
    raw = ads_daily_performance_response("camp-123", "ad-camp-123-1")["response"][0]

    entities = mapper.map(raw)

    assert len(entities) == 1
    perf = entities[0]
    assert perf.model_class == AdPerformance
    assert perf.data["campaign_id"] == "canonical-camp-uuid"
    assert perf.data["ad_id"] == "canonical-ad-uuid"
    assert perf.data["impressions"] == 12500
    assert perf.data["clicks"] == 340
    assert perf.data["conversions"] == 12
    assert perf.data["spend"] == Decimal("150000")
    assert perf.data["revenue"] == Decimal("480000")
    assert perf.data["roas"] == Decimal("3.2000")
    assert perf.data["date"] == datetime(2026, 7, 17, tzinfo=timezone.utc)


def test_ads_performance_mapper_requires_campaign_and_ad(tenant):
    provenance = FakeProvenanceRepo()
    mapper = ShopeeAdsPerformanceMapper(tenant, provenance)
    with pytest.raises(ValueError, match="campaign_id or ad_id"):
        mapper.map({})


def test_ads_performance_mapper_fails_when_parent_not_synced(tenant):
    provenance = FakeProvenanceRepo()
    mapper = ShopeeAdsPerformanceMapper(tenant, provenance)
    raw = ads_daily_performance_response("camp-123", "ad-camp-123-1")["response"][0]

    with pytest.raises(ValueError, match="No canonical campaign found"):
        mapper.map(raw)
