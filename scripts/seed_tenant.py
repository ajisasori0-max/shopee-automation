#!/usr/bin/env python3
"""Seed the CommerceOS tenant (Organization, Business, Store) for dashboard use.

Idempotent: safe to run multiple times. Uses fixed UUIDs so the dashboard can
reference a known store_id.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from commerceos.commerce.models import Business, Marketplace, Organization, Store
from commerceos.platform.database.connection import create_all, get_session, reset_engine

DATABASE_URL = "sqlite:///./commerceos.db"

ORG_ID = "org-ppm-001"
BIZ_ID = "biz-ppm-001"
STORE_ID = "store-ppm-001"
MARKETPLACE_ID = "mkt-shopee-001"


def seed():
    reset_engine()
    create_all(DATABASE_URL)
    session = get_session(DATABASE_URL)

    with session:
        # Organization
        org = session.query(Organization).filter_by(id=ORG_ID).first()
        if not org:
            org = Organization(id=ORG_ID, name="Payung Murah Jakarta", slug="ppm", timezone="Asia/Jakarta")
            session.add(org)
            session.flush()

        # Business
        biz = session.query(Business).filter_by(id=BIZ_ID).first()
        if not biz:
            biz = Business(
                id=BIZ_ID,
                organization_id=ORG_ID,
                name="Payung Murah Jakarta",
                default_currency="IDR",
            )
            session.add(biz)
            session.flush()

        # Marketplace
        mkt = session.query(Marketplace).filter_by(code="shopee").first()
        if not mkt:
            mkt = Marketplace(id=MARKETPLACE_ID, code="shopee", name="Shopee")
            session.add(mkt)
            session.flush()

        # Store
        store = session.query(Store).filter_by(id=STORE_ID).first()
        if not store:
            store = Store(
                id=STORE_ID,
                business_id=BIZ_ID,
                marketplace_id=mkt.id,
                marketplace_store_id="1147948100",
                name="Payung Murah Jakarta",
                organization_id=ORG_ID,
                store_id=STORE_ID,
            )
            session.add(store)
            session.flush()

        session.commit()

    print("✅ Seeded CommerceOS tenant:")
    print(f"   Organization: {ORG_ID}")
    print(f"   Business:     {BIZ_ID}")
    print(f"   Marketplace:  {MARKETPLACE_ID}")
    print(f"   Store:        {STORE_ID} (Shopee shop 1147948100)")
    print()
    print("Use this store_id in dashboard queries or set COMMERCEOS_STORE_ID=store-ppm-001")


if __name__ == "__main__":
    seed()
