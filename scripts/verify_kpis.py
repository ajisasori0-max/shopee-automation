"""Verify materialized KPIs vs temporary fallback."""


import os
import sys
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from commerceos.config.settings import get_settings
from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.shared.value_objects.primitives import utc_now


def main():
    settings = get_settings()
    store_id = "store-ppm-001"
    end = utc_now()
    start = end - timedelta(days=30)

    with DashboardQueryService(database_url=settings.database_url) as qs:
        pl = qs.get_pl_summary(store_id, start, end)
        ads = qs.get_ad_performance_summary(store_id, start, end)
        daily = qs.get_daily_sales(store_id, start, end)
        state = qs.get_commerce_state(store_id)

        print("=== P&L Summary ===")
        for k, v in pl.items():
            print(f"  {k}: {v}")
        print("\n=== Ad Performance Summary ===")
        for k, v in ads.items():
            print(f"  {k}: {v}")
        print("\n=== Daily Sales ===")
        for row in daily:
            print(f"  {row}")
        print("\n=== Commerce State ===")
        print(f"  temporary: {state.get('temporary')}")
        print(f"  data_quality_score: {state.get('data_quality_score')}")
        print(f"  sources_fresh: {state.get('sources_fresh')}")
        print(f"  sources_stale: {state.get('sources_stale')}")
        print(f"  summary: {state.get('summary')}")


if __name__ == "__main__":
    main()
