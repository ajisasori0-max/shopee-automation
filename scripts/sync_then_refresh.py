#!/usr/bin/env python3
"""Run incremental Shopee sync and immediately refresh KPIs/CommerceState.

This is the scheduled entrypoint for the CommerceOS ingestion pipeline.
- Uses the project's virtualenv Python implicitly (must be invoked via .venv/bin/python3).
- Forces FULL_RESYNC=0 so the SQLite database is never wiped.
- Only refreshes KPIs if the sync exits successfully.
- Logs both steps to the standard job execution log.
"""
import os
import subprocess
import sys
from pathlib import Path

from commerceos.config.settings import get_settings


_settings = get_settings()
BASE_DIR = Path(__file__).parent.parent
VENV_PYTHON = BASE_DIR / ".venv" / "bin" / "python3"
REQUIRED_ENV = {
    "PYTHONPATH": str(BASE_DIR),
    "FULL_RESYNC": "0",
    "DATABASE_URL": _settings.database_url,
}


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(REQUIRED_ENV)
    return env


def _run(script: str) -> int:
    cmd = [str(VENV_PYTHON), str(BASE_DIR / "scripts" / script)]
    result = subprocess.run(cmd, cwd=BASE_DIR, env=_env())
    return result.returncode


def main() -> int:
    sync_rc = _run("live_resync.py")
    if sync_rc != 0:
        print("Sync failed; skipping KPI refresh.", file=sys.stderr)
        return sync_rc

    kpi_rc = _run("refresh_kpis.py")
    if kpi_rc != 0:
        print("KPI refresh failed.", file=sys.stderr)
        return kpi_rc

    print("Sync + KPI refresh completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
