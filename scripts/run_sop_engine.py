#!/usr/bin/env python3
"""Command-line and scheduled entry point for the SOP Engine.

Intended to be run as a scheduled job or manually during operational cycles.
Idempotent: re-running the same engine session produces deterministic outputs; the
knowledge layer records each run, but duplicate recommendations are avoided by the
Decision Engine downstream if it enforces deduplication.
"""

import os
import sys

# Make the script runnable from any CWD when the package is next to it.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from commerceos.sop.engine import run_sop_engine
from commerceos.platform.database.connection import get_session, create_all
from commerceos.config.settings import get_settings


def main():
    parser = argparse.ArgumentParser(description="Run SOP engine for a store")
    parser.add_argument("--store-id", default="store-ppm-001", help="Store identifier")
    parser.add_argument("--no-persist", action="store_true", help="Do not persist decisions")
    parser.add_argument("--no-events", action="store_true", help="Do not publish events")
    parser.add_argument("--no-knowledge", action="store_true", help="Do not record knowledge note")
    parser.add_argument("--init-db", action="store_true", help="Create tables before running")
    args = parser.parse_args()

    settings = get_settings()
    if args.init_db:
        create_all(settings.database_url)

    session = get_session(settings.database_url)
    try:
        result = run_sop_engine(
            session,
            store_id=args.store_id,
            persist_decisions=not args.no_persist,
            publish_events=not args.no_events,
            record_knowledge=not args.no_knowledge,
        )
        print(f"SOP run complete: {result['applicable']}/{result['sop_count']} applicable")
        for rec in result["recommendations"]:
            print(f"- {rec['title']}: {rec['recommended_action']}")
        if result.get("decision_ids"):
            print(f"Persisted decision IDs: {result['decision_ids']}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
