"""Experiments page for the Web COO Dashboard."""
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.coo.web_service import WebCOODashboardService
from commerceos.platform.database.connection import get_session

st.set_page_config(page_title="Experiments — CommerceOS", page_icon="🧪", layout="wide")

SETTINGS = get_settings()
STORE_ID = st.secrets.get("COMMERCEOS_STORE_ID", "store-ppm-001")


@st.cache_resource(show_spinner=False)
def _get_session():
    return get_session(SETTINGS.database_url)


st.title("🧪 Experiments")
st.caption("Controlled business experiments: hypothesis → action → observation → result → lesson.")

session = _get_session()
service = WebCOODashboardService(session, store_id=STORE_ID)
data = service.get_experiments()

if data.get("errors"):
    with st.expander("Warnings"):
        for error in data["errors"]:
            st.caption(f"⚠️ {error}")

st.subheader("Active / Pending Experiment Decisions")
exp_decisions = data.get("experiment_decisions", [])
if exp_decisions:
    for decision in exp_decisions:
        with st.expander(decision.get("title", "Experiment"), expanded=False):
            st.markdown(f"**Hypothesis:** {decision.get('description', '—')}")
            st.markdown(f"**Rationale:** {decision.get('rationale', '—')}")
            st.markdown(f"**Expected Impact:** {decision.get('expected_impact', '—')}")
            st.markdown(f"**Status:** {decision.get('status', '—')} | **Confidence:** {decision.get('confidence', '—')}")
else:
    st.info("No active or pending experiment decisions. Create an experiment to see it here.")

st.divider()

st.subheader("Recent Experiment Plans")
exp_plans = data.get("experiment_plans", [])
if exp_plans:
    st.dataframe(pd.DataFrame(exp_plans), width='stretch', hide_index=True)
else:
    st.info("No experiment execution plans in the last 7 days.")

st.divider()

st.subheader("Run a Scenario")
scenario_type = st.selectbox("Scenario type", ["ad_spend_increase", "sales_decline", "supplier_delay"])
params: dict = {}
if scenario_type == "ad_spend_increase":
    params["increase_pct"] = st.number_input("Ad spend increase %", value=20.0)
    params["horizon_days"] = st.number_input("Horizon (days)", value=7, min_value=1, max_value=30)
elif scenario_type == "sales_decline":
    params["decline_pct"] = st.number_input("Sales decline %", value=20.0)
    params["horizon_days"] = st.number_input("Horizon (days)", value=7, min_value=1, max_value=30)
elif scenario_type == "supplier_delay":
    params["sku"] = st.text_input("SKU", value="W-001-RED")
    params["baseline_lead_time"] = st.number_input("Baseline lead time (days)", value=7, min_value=1)
    params["scenario_lead_time"] = st.number_input("Scenario lead time (days)", value=14, min_value=1)

if st.button("Run Scenario"):
    result = service.run_scenario(scenario_type, params)
    if result.get("error"):
        st.error(result["error"])
    else:
        st.json(result)

st.divider()
st.caption("CommerceOS Web COO Dashboard | Experiments")
