"""SOP & Rules page for the Web COO Dashboard."""
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.coo.web_service import WebCOODashboardService
from commerceos.platform.database.connection import get_session

st.set_page_config(page_title="SOP & Rules — CommerceOS", page_icon="📜", layout="wide")

SETTINGS = get_settings()
STORE_ID = st.secrets.get("COMMERCEOS_STORE_ID", "store-ppm-001")


@st.cache_resource(show_spinner=False)
def _get_session():
    return get_session(SETTINGS.database_url)


st.title("📜 SOP & Rules")
st.caption("How CommerceOS handles recurring business situations.")

session = _get_session()
service = WebCOODashboardService(session, store_id=STORE_ID)
data = service.get_sop_rules()

if data.get("errors"):
    with st.expander("Warnings"):
        for error in data["errors"]:
            st.caption(f"⚠️ {error}")

st.subheader("Standard Operating Procedures")
for sop in data.get("sops", []):
    with st.expander(f"{sop.get('name')} ({sop.get('code')})", expanded=False):
        st.markdown(f"**Trigger:** {sop.get('trigger', '—')}")
        st.markdown(f"**Category:** {sop.get('category', '—')} | **Severity:** {sop.get('severity', '—')} | **Version:** {sop.get('version', '—')}")
        st.markdown(f"**Description:** {sop.get('description', '—')}")
        st.markdown("**Steps:**")
        for step in sop.get("steps", []):
            st.markdown(f"- **{step.get('name')}** — {step.get('description')}")
            if step.get("condition"):
                st.caption(f"Condition: `{step['condition']}`")
            if step.get("decision_point"):
                st.caption("⛳ Decision point")

st.divider()

st.subheader("Policy Rules")
policy_rules = data.get("policy_rules", [])
if policy_rules:
    st.dataframe(pd.DataFrame(policy_rules), width='stretch', hide_index=True)
else:
    st.info("No policy rules configured.")

st.divider()

st.subheader("Recent SOP Executions")
executions = data.get("recent_executions", [])
if executions:
    st.dataframe(pd.DataFrame(executions), width='stretch', hide_index=True)
else:
    st.info("No recent SOP executions recorded.")

st.divider()
st.caption("CommerceOS Web COO Dashboard | SOP & Rules")
