"""Operations page for the Web COO Dashboard."""
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.coo.web_service import WebCOODashboardService
from commerceos.platform.database.connection import get_session

st.set_page_config(page_title="Operations — CommerceOS", page_icon="🖥️", layout="wide")

SETTINGS = get_settings()
STORE_ID = st.secrets.get("COMMERCEOS_STORE_ID", "store-ppm-001")


@st.cache_resource(show_spinner=False)
def _get_session():
    return get_session(SETTINGS.database_url)


st.title("🖥️ Operations")
st.caption("Sync freshness, job health, data quality, and system status.")

session = _get_session()
service = WebCOODashboardService(session, store_id=STORE_ID)
data = service.get_operations()

if data.get("errors"):
    with st.expander("Warnings"):
        for error in data["errors"]:
            st.caption(f"⚠️ {error}")

snapshot = data.get("snapshot", {})
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Overall Status", snapshot.get("overall_status", "unknown").upper())
with col2:
    score = snapshot.get("data_quality_score")
    st.metric("Data Quality", f"{score:.0%}" if score is not None else "—")
with col3:
    score = snapshot.get("freshness_score")
    st.metric("Freshness", f"{score:.0%}" if score is not None else "—")
with col4:
    score = snapshot.get("availability_score")
    st.metric("Availability", f"{score:.0%}" if score is not None else "—")

st.divider()

tab_sync, tab_jobs, tab_health, tab_alerts, tab_dead = st.tabs(["Sync", "Jobs", "System Health", "Alerts", "Dead Letters"])

with tab_sync:
    col_sync1, col_sync2 = st.columns([1, 3])
    with col_sync1:
        if st.button("🔄 Sync Now", help="Run incremental sync + KPI refresh in the background"):
            with st.spinner("Starting sync..."):
                env = os.environ.copy()
                env["PYTHONPATH"] = str(BASE_DIR)
                env["FULL_RESYNC"] = "0"
                env["DATABASE_URL"] = SETTINGS.database_url
                result = subprocess.run(
                    [sys.executable, str(BASE_DIR / "scripts" / "sync_then_refresh.py")],
                    cwd=str(BASE_DIR),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=1800,
                )
                if result.returncode == 0:
                    st.success("Sync completed successfully")
                    st.rerun()
                else:
                    st.error("Sync failed — check logs")
                    with st.expander("Error output"):
                        st.text(result.stderr[-2000:])

    freshness = data.get("sync", {}).get("freshness", {})
    if freshness:
        df = pd.DataFrame(
            [
                {"entity": k, "hours_since": v["hours_since_sync"], "fresh": v["is_fresh"], "last_sync": v["last_sync"][:19]}
                for k, v in freshness.items()
            ]
        )
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("No sync checkpoints recorded.")

    sync_runs = data.get("sync", {}).get("sync_health", [])
    if sync_runs:
        st.subheader("Recent Sync Runs")
        df = pd.DataFrame(sync_runs[:20])
        display = [c for c in ["connector_code", "entity_type", "sync_mode", "status", "records_received", "records_persisted", "records_failed", "completed_at"] if c in df.columns]
        st.dataframe(df[display], width='stretch', hide_index=True)

    dq = data.get("data_quality", {})
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Missing Provenance**")
        missing = dq.get("missing_provenance", [])
        if missing:
            st.dataframe(pd.DataFrame(missing), width='stretch', hide_index=True)
        else:
            st.success("All records have provenance")
    with col2:
        st.markdown("**Recent Failures**")
        failures = dq.get("recent_failures", [])
        if failures:
            st.dataframe(pd.DataFrame(failures), width='stretch', hide_index=True)
        else:
            st.success("No recent sync failures")

with tab_jobs:
    jobs = data.get("jobs", {})
    summary = jobs.get("summary", {})
    st.metric("Executions (24h)", summary.get("total_executions", 0))
    st.metric("Failed", summary.get("failed_executions", 0))
    latest = jobs.get("latest", [])
    if latest:
        st.dataframe(pd.DataFrame(latest), width='stretch', hide_index=True)
    else:
        st.info("No job execution history.")

with tab_health:
    health = data.get("system_health", {})
    components = health.get("components", [])
    if components:
        df = pd.DataFrame(components)
        display = [c for c in ["component", "component_instance", "check_type", "status", "severity", "message", "checked_at"] if c in df.columns]
        st.dataframe(df[display], width='stretch', hide_index=True)
    else:
        st.info("No health checks recorded.")

with tab_alerts:
    alerts = data.get("open_alerts", [])
    if alerts:
        st.dataframe(pd.DataFrame(alerts), width='stretch', hide_index=True)
    else:
        st.success("No open alerts.")

with tab_dead:
    dead = data.get("dead_letters", [])
    if dead:
        st.warning(f"{len(dead)} dead letter(s)")
        st.dataframe(pd.DataFrame(dead), width='stretch', hide_index=True)
    else:
        st.success("No dead letters.")

st.divider()
st.caption("CommerceOS Web COO Dashboard | Operations")
