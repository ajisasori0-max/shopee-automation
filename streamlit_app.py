import streamlit as st
from datetime import datetime, timedelta, timezone
import os
import threading
import time
import logging

# Minimal landing page that immediately redirects to the Command Center.
# This preserves the existing URL entrypoint while making Mission Control the
# default homepage.

st.set_page_config(
    page_title="CommerceOS",
    page_icon="🦊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Background sync scheduler (Render / single-service deployment)
# ---------------------------------------------------------------------------

def _background_sync_loop(interval_seconds: int = 14400) -> None:
    """Run the CommerceOS sync pipeline periodically in a daemon thread.

    This keeps a single-service Render deployment fresh without needing a
    separate cron job or persistent disk sharing. It is intentionally
    best-effort: failures are logged, not surfaced in the UI.
    """
    logger = logging.getLogger("commerceos.background_sync")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)

    # Delay first run so the Streamlit server can finish starting.
    time.sleep(30)

    while True:
        try:
            # Run in a subprocess so PYTHONPATH/env are isolated and clean.
            import subprocess
            import sys

            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
            env["FULL_RESYNC"] = "0"

            result = subprocess.run(
                [sys.executable, "scripts/sync_then_refresh.py"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env,
                capture_output=True,
                text=True,
                timeout=1800,
            )
            if result.returncode == 0:
                logger.info("Background sync completed successfully")
            else:
                logger.error("Background sync failed: %s", result.stderr[-1000:])
        except Exception as e:
            logger.exception("Background sync error: %s", e)

        time.sleep(interval_seconds)


def _start_background_sync() -> None:
    """Start the daemon sync thread exactly once per Streamlit process."""
    if os.environ.get("COMMERCEOS_BACKGROUND_SYNC", "1") != "0":
        thread = threading.Thread(target=_background_sync_loop, daemon=True)
        thread.start()


_start_background_sync()

st.switch_page("pages/mission_control.py")
