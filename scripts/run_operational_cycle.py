"""Run one end-to-end operational cycle: health → brief → OAT → closed loop.

This script demonstrates the Epic 4 operational loop. It does not execute any
marketplace mutations; it only records observations, briefs, and verification.
"""
from __future__ import annotations
from commerceos.shared.value_objects.primitives import utc_now


import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.jobs.factory import register_default_jobs
from commerceos.jobs.runner import JobRunner
from commerceos.platform.database.connection import get_session
from scripts.oat_verification import OATVerification


def main():
    settings = get_settings()
    session = get_session(settings.database_url)
    try:
        registry = register_default_jobs(session=session, settings=settings)
        runner = JobRunner(session=session, registry=registry)

        print(f"Operational cycle started at {utc_now().isoformat()}")
        results = runner.run_many([
            "system_health_check",
            "daily_coo_brief",
            "knowledge_index_refresh",
        ])
        for r in results:
            print(f"- {r['name']}: {r['status']}")

        verifier = OATVerification(session)
        report = verifier.run_all()
        verifier.print_report(report)

        if report["overall"] != "PASS":
            print("Operational cycle completed with OAT failures.")
            return 1

        print("✅ Operational cycle passed.")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
