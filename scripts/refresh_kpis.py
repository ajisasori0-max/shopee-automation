"""Refresh KPIs and Commerce State for a store."""


import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure workspace is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from commerceos.config.settings import get_settings
from commerceos.dashboard.query_service import DashboardQueryService
from commerceos.monitoring.job_log import log_job_execution
from commerceos.platform.database.connection import get_session
from commerceos.shared.value_objects.primitives import utc_now


_settings = get_settings()
DB_URL = _settings.database_url


def refresh(store_id: str, organization_id: str, business_id: str) -> None:
    start_time = utc_now()
    settings = get_settings()
    with DashboardQueryService(database_url=settings.database_url) as qs:
        result = qs.refresh(store_id, organization_id, business_id)

    # Log job execution for scheduler health monitoring
    end_time = utc_now()
    log_session = get_session(DB_URL)
    log_job_execution(
        log_session,
        job_name="kpi-refresh",
        status="completed",
        started_at=start_time,
        finished_at=end_time,
        metadata={"result": result},
    )
    log_session.close()

    print(f"KPI refresh complete: {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh materialized KPIs")
    parser.add_argument("--store-id", default="store-ppm-001")
    parser.add_argument("--organization-id", default="org-ppm-001")
    parser.add_argument("--business-id", default="biz-ppm-001")
    args = parser.parse_args()
    refresh(args.store_id, args.organization_id, args.business_id)
