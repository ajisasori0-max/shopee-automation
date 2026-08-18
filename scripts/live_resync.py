"""Live full sync: pull all Shopee entities into commerceos.db.

By default this re-creates the database from scratch (useful for E1.3 validation).
Set FULL_RESYNC=0 to keep existing data and sync incrementally.

Credentials are read from token_manager APPS config (not .env sandbox creds).
"""
from commerceos.shared.value_objects.primitives import utc_now
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from token_manager import TokenManager, APPS
from commerceos.connectors.shopee import (
    ShopeeApiClient, ShopeeConnector,
    ShopeeOrderMapper, ShopeePaymentMapper, ShopeeTenantContext,
)
from commerceos.connectors.shopee.mappers import (
    ShopeeProductMapper, ShopeeInventoryMapper, ShopeeCampaignMapper,
    ShopeeAdsPerformanceMapper,
)
from commerceos.ingestion import SyncEngine, sqlalchemy_ingestion_uow
from commerceos.monitoring.job_log import log_job_execution
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.config.settings import get_settings

_settings = get_settings()
DB_URL = _settings.database_url
# For SQLite paths, derive the filesystem path so FULL_RESYNC can wipe the file.
DB_PATH = Path(DB_URL.replace("sqlite:///", "")) if DB_URL.startswith("sqlite:///") else None
STORE_ID = "store-ppm-001"


def _ensure_schema():
    """Run Alembic migrations to create all tables (including monitoring/decisions/events)."""
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        cwd=Path(__file__).parent.parent,
    )


def _make_client(app_name: str, tm: TokenManager) -> ShopeeApiClient:
    access_token = tm.get_valid_token(app_name)
    config = tm._config(app_name)
    return ShopeeApiClient(
        partner_id=config["partner_id"],
        partner_key=config["partner_key"],
        shop_id=config["shop_id"],
        access_token=access_token,
        sandbox=False,
    )


def main():
    full_resync = os.environ.get("FULL_RESYNC", "1") != "0"
    if full_resync and DB_PATH is not None and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Wiped existing database: {DB_PATH}")
    elif full_resync and DB_PATH is None:
        print("WARNING: FULL_RESYNC requested but target is not a SQLite file; skipping wipe.")

    _ensure_schema()

    start_time = utc_now()
    tm = TokenManager(".")
    # Force refresh access tokens before starting the sync. Shopee only allows
    # one active refresh token at a time, so this MUST go through
    # token_manager.py and never any other script.
    print("Refreshing access tokens via token_manager...")
    for app_name in APPS:
        token = tm.get_access_token(app_name, force_refresh=True)
        if not token:
            print(f"FATAL: {app_name}: could not refresh access token")
            sys.exit(1)

    health = tm.check_health(auto_refresh=False)
    print("Token health:", json.dumps({k: v["status"] for k, v in health.items()}, indent=2))
    if health["production"]["needs_reauth"] or health["ads"]["needs_reauth"]:
        print("FATAL: one or more tokens need reauth")
        sys.exit(1)

    prod_client = _make_client("production", tm)
    ads_client = _make_client("ads", tm)
    # Use the internal store alias for all canonical persistence. The injected
    # API clients already carry the real Shopee shop_id for API calls.
    internal_store_id = STORE_ID

    tenant = ShopeeTenantContext(
        organization_id="org-ppm-001", business_id="biz-ppm-001",
        store_id=internal_store_id, currency="IDR",
    )

    prod_connector = ShopeeConnector(store_id=internal_store_id, tenant=tenant, api_client=prod_client)
    ads_connector = ShopeeConnector(store_id=internal_store_id, tenant=tenant, api_client=ads_client)

    reset_engine()
    create_all(DB_URL)
    sess = get_session(DB_URL)

    results = {}
    with sqlalchemy_ingestion_uow(sess) as uow:
        engine = SyncEngine(uow=uow)
        engine.register_mapper("orders", ShopeeOrderMapper(tenant))
        engine.register_mapper("payments", ShopeePaymentMapper(tenant))
        engine.register_mapper("products", ShopeeProductMapper(tenant))
        engine.register_mapper("inventory", ShopeeInventoryMapper(tenant, uow.provenance(), store_id=internal_store_id))
        engine.register_mapper("campaigns", ShopeeCampaignMapper(tenant))
        engine.register_mapper("ad_performances", ShopeeAdsPerformanceMapper(tenant, uow.provenance(), store_id=internal_store_id))

        for entity in ["orders", "payments", "products", "inventory"]:
            connector = prod_connector
            try:
                r = engine.sync(connector, entity_type=entity, store_id=internal_store_id)
                results[entity] = _summarize(r)
                print(f"{entity}: {results[entity]}")
            except Exception as e:
                results[entity] = {"success": False, "error": str(e)[:200]}
                print(f"{entity}: FAILED {e}")

        for entity in ["campaigns", "ad_performances"]:
            connector = ads_connector
            try:
                r = engine.sync(connector, entity_type=entity, store_id=internal_store_id)
                results[entity] = _summarize(r)
                print(f"{entity}: {results[entity]}")
            except Exception as e:
                results[entity] = {"success": False, "error": str(e)[:200]}
                print(f"{entity}: FAILED {e}")

    sess.close()
    reset_engine()

    print("\n=== SYNC RESULTS ===")
    for entity, result in results.items():
        print(f"{entity}: {result}")

    # Log job execution for scheduler health monitoring
    end_time = utc_now()
    all_success = all(r.get("success", False) for r in results.values())
    log_session = get_session(DB_URL)
    log_job_execution(
        log_session,
        job_name="shopee-sync",
        status="completed" if all_success else "failed",
        started_at=start_time,
        finished_at=end_time,
        metadata={"results": results},
    )
    log_session.close()


def _summarize(r):
    out = {"success": r.success}
    for key in ("records_received", "records_persisted", "records_failed"):
        if key in r.metadata:
            out[key] = r.metadata[key]
    if not r.success:
        out["errors"] = r.errors or r.metadata.get("errors")
    return out


if __name__ == "__main__":
    main()
