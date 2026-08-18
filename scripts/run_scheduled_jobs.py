"""Run the scheduled CommerceOS operational jobs.

Designed to be invoked from cron. Example crontab entries:

# 08:00 daily — morning brief, health check, index refresh
0 8 * * * cd /path/to/repo && /path/to/venv/bin/python scripts/run_scheduled_jobs.py

# 20:00 daily — evening review
0 20 * * * cd /path/to/repo && /path/to/venv/bin/python scripts/send_evening_review.py

# Every 4 hours — health check
0 */4 * * * cd /path/to/repo && /path/to/venv/bin/python scripts/run_scheduled_jobs.py --only system_health_check

# Monday 08:30 — weekly review + retention
30 8 * * 1 cd /path/to/repo && /path/to/venv/bin/python scripts/run_scheduled_jobs.py --only weekly_business_review,knowledge_retention

# First day of month 08:00 — monthly executive review
0 8 1 * * cd /path/to/repo && /path/to/venv/bin/python scripts/run_scheduled_jobs.py --only monthly_executive_review
"""
from __future__ import annotations
from commerceos.shared.value_objects.primitives import utc_now


import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.jobs.factory import register_default_jobs
from commerceos.jobs.runner import JobRunner
from commerceos.platform.database.connection import get_session


def main():
    parser = argparse.ArgumentParser(description="Run scheduled CommerceOS jobs")
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="Comma-separated job names to run (default: all registered jobs)",
    )
    parser.add_argument(
        "--send-morning-brief",
        action="store_true",
        help="Also send the morning Telegram brief after jobs run",
    )
    parser.add_argument(
        "--send-evening-review",
        action="store_true",
        help="Also send the evening Telegram review after jobs run",
    )
    args = parser.parse_args()

    settings = get_settings()
    session = get_session(settings.database_url)
    try:
        registry = register_default_jobs(session=session, settings=settings)
        runner = JobRunner(session=session, registry=registry)

        names = [n.strip() for n in args.only.split(",") if n.strip()] or registry.names()
        results = runner.run_many(names)

        failed = [r for r in results if r["status"] != "completed"]
        print(f"Run finished at {utc_now().isoformat()}: {len(results)} job(s), {len(failed)} failed")
        for r in results:
            print(f"- {r['name']}: {r['status']}")
        if failed:
            for r in failed:
                print(f"  FAILED: {r.get('error')}")
            return 1

        if args.send_morning_brief:
            from scripts.send_morning_brief import main as send_morning
            send_morning()
        if args.send_evening_review:
            from scripts.send_evening_review import main as send_evening
            send_evening()
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
