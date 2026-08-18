"""Executions page for the Web COO Dashboard."""
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.coo.web_service import WebCOODashboardService
from commerceos.platform.database.connection import get_session

st.set_page_config(page_title="Executions — CommerceOS", page_icon="⚙️", layout="wide")

SETTINGS = get_settings()
STORE_ID = st.secrets.get("COMMERCEOS_STORE_ID", "store-ppm-001")


@st.cache_resource(show_spinner=False)
def _get_session():
    return get_session(SETTINGS.database_url)


st.title("⚙️ Executions")
st.caption("Recommendation → Approval → Execution. Track the lifecycle.")

session = _get_session()
service = WebCOODashboardService(session, store_id=STORE_ID)
data = service.get_executions()

if data.get("errors"):
    with st.expander("Warnings"):
        for error in data["errors"]:
            st.caption(f"⚠️ {error}")

summary = data.get("summary", {})
status_counts = summary.get("counts_by_status", {})
cols = st.columns(4)
with cols[0]:
    st.metric("Total Plans", summary.get("total", 0))
with cols[1]:
    st.metric("Planned", status_counts.get("planned", 0))
with cols[2]:
    st.metric("Running", status_counts.get("running", 0))
with cols[3]:
    st.metric("Completed", status_counts.get("completed", 0))

st.divider()

st.subheader("Running")
if data.get("running"):
    st.dataframe(pd.DataFrame(data["running"]), width='stretch', hide_index=True)
else:
    st.success("No running executions.")

st.divider()

st.subheader("Queue (Ready / Planned)")
if data.get("queue"):
    st.dataframe(pd.DataFrame(data["queue"]), width='stretch', hide_index=True)
else:
    st.info("Execution queue is empty.")

st.divider()

st.subheader("Recent (24h)")
if data.get("recent"):
    st.dataframe(pd.DataFrame(data["recent"]), width='stretch', hide_index=True)
else:
    st.info("No executions in the last 24 hours.")

if st.session_state.get("selected_plan_id"):
    plan_id = st.session_state["selected_plan_id"]
    detail = service.get_execution(plan_id)
    if detail:
        st.subheader("Execution Plan Details")
        st.json(detail)
    if st.button("Close Details"):
        del st.session_state["selected_plan_id"]
        st.rerun()

st.divider()
st.caption("CommerceOS Web COO Dashboard | Executions")
