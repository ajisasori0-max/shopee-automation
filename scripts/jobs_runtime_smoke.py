"""End-to-end smoke test for the automation runtime."""

import os
import sys
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.jobs.factory import register_default_jobs
from commerceos.jobs.health import JobHealthReporter
from commerceos.jobs.runner import JobRunner
from commerceos.platform.database.connection import create_all, get_session, reset_engine


def main():
    db_path = "test_jobs_runtime.db"
    reset_engine()
    if os.path.exists(db_path):
        os.remove(db_path)

    db_url = f"sqlite:///{db_path}"
    create_all(db_url)
    session = get_session(db_url)

    try:
        settings = get_settings()
        registry = register_default_jobs(session=session, settings=settings)
        runner = JobRunner(session=session, registry=registry)
        reporter = JobHealthReporter(session=session, registry=registry)

        # Run all registered jobs. Some may fail due to empty data; that is OK for smoke test.
        results = runner.run_many(registry.names())
        for r in results:
            print(f"- {r['name']}: {r['status']}")

        summary = reporter.summary()
        print(f"Health summary: {summary}")

        # Verify records are persisted.
        assert all(r["execution_id"] for r in results), "All jobs should have execution IDs"
        assert summary["total_executions"] >= len(registry.names()), "Executions should be logged"
        print("✅ Automation runtime smoke test passed.")
    finally:
        session.close()
        reset_engine()
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    main()
