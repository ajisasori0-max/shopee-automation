from commerceos.shared.value_objects.primitives import utc_now
import sys
sys.path.insert(0, "/Users/gerard/.openclaw/workspace/shopee-api-onboarding")

from commerceos.config.settings import get_settings
from commerceos.platform.database.connection import get_session
from commerceos.ingestion.models import SyncCheckpoint
from datetime import datetime, timezone

settings = get_settings()
session = get_session(settings.database_url)
now = utc_now()
print("now:", now)
for cp in session.query(SyncCheckpoint).filter_by(store_id="store-ppm-001").all():
    ts = cp.last_successful_sync_at
    print(cp.entity_type, ts, type(ts).__name__, ts.tzinfo if ts else None)
    if ts:
        try:
            diff = (now - ts).total_seconds() / 3600
            print("  hours_ago:", diff, "fresh:", diff < 24)
        except Exception as e:
            print("  ERROR:", e)
