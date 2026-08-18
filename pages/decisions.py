"""Decisions page for the Web COO Dashboard."""
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.coo.web_service import WebCOODashboardService
from commerceos.platform.database.connection import get_session

st.set_page_config(page_title="Decisions — CommerceOS", page_icon="⚖️", layout="wide")

SETTINGS = get_settings()
STORE_ID = st.secrets.get("COMMERCEOS_STORE_ID", "store-ppm-001")


@st.cache_resource(show_spinner=False)
def _get_session():
    return get_session(SETTINGS.database_url)


st.title("⚖️ Decisions")
st.caption("Review, approve, and track business decisions.")

session = _get_session()
service = WebCOODashboardService(session, store_id=STORE_ID)

status_filter = st.sidebar.selectbox("Status", ["open", "all", "approved", "rejected", "executed"], index=0)
category_filter = st.sidebar.text_input("Category filter")

data = service.get_decisions(status=status_filter, category=category_filter or None)

if data.get("errors"):
    with st.expander("Warnings"):
        for error in data["errors"]:
            st.caption(f"⚠️ {error}")

summary = data.get("summary", {})
cols = st.columns(4)
with cols[0]:
    st.metric("Overall Severity", summary.get("overall_severity", "info").upper())
with cols[1]:
    counts = summary.get("counts_by_status", {})
    st.metric("Proposed", counts.get("proposed", 0))
with cols[2]:
    st.metric("Approved", counts.get("approved", 0))
with cols[3]:
    st.metric("Executed", counts.get("executed", 0))

st.divider()

decisions = data.get("decisions", [])
if not decisions:
    st.info("No decisions match the selected filters.")
else:
    for decision in decisions:
        severity = decision.get("severity", "info")
        with st.container():
            st.markdown(f"**{decision.get('title', 'Decision')}**")
            st.caption(f"{decision.get('category', '—')} | Severity: {severity.upper()} | Status: {decision.get('status', '—')}")
            st.markdown(decision.get("description", "—")[:200])
            col1, col2, col3 = st.columns([1, 1, 3])
            with col1:
                if st.button("✅ Approve", key=f"approve_{decision['id']}", width='stretch'):
                    result = service.approve_decision(decision["id"])
                    if result["success"]:
                        st.success("Approved")
                        st.rerun()
                    else:
                        st.error(result["error"])
            with col2:
                if st.button("❌ Reject", key=f"reject_{decision['id']}", width='stretch'):
                    result = service.reject_decision(decision["id"])
                    if result["success"]:
                        st.success("Rejected")
                        st.rerun()
                    else:
                        st.error(result["error"])
            with col3:
                if st.button("🔍 View Details", key=f"detail_{decision['id']}", width='stretch'):
                    st.session_state["selected_decision_id"] = decision["id"]
                    st.rerun()
            st.divider()

if st.session_state.get("selected_decision_id"):
    decision_id = st.session_state["selected_decision_id"]
    detail = service.get_decision(decision_id)
    if detail:
        st.subheader("Decision Details")
        st.json(detail)
    if st.button("Close Details"):
        del st.session_state["selected_decision_id"]
        st.rerun()

st.divider()
st.caption("CommerceOS Web COO Dashboard | Decisions")
