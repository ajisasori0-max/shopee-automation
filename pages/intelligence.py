"""Intelligence page for the Web COO Dashboard."""
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.coo.web_service import WebCOODashboardService
from commerceos.platform.database.connection import get_session

st.set_page_config(page_title="Intelligence — CommerceOS", page_icon="💡", layout="wide")

SETTINGS = get_settings()
STORE_ID = st.secrets.get("COMMERCEOS_STORE_ID", "store-ppm-001")


@st.cache_resource(show_spinner=False)
def _get_session():
    return get_session(SETTINGS.database_url)


def _currency(value: float) -> str:
    try:
        return f"Rp {value:,.0f}"
    except (TypeError, ValueError):
        return f"Rp {value}"


st.title("💡 Intelligence")
st.caption("What changed, why it matters, and what to do.")

session = _get_session()
service = WebCOODashboardService(session, store_id=STORE_ID)
days = st.sidebar.slider("Window (days)", 1, 30, 7)
data = service.get_intelligence(days=days)

if data.get("errors"):
    with st.expander("Warnings"):
        for error in data["errors"]:
            st.caption(f"⚠️ {error}")

business = data.get("business_summary", {})
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Overall Severity", business.get("overall_severity", "info").upper())
with col2:
    st.metric("Insights", business.get("insight_count", 0))
with col3:
    st.metric("Categories", len(business.get("categories", {})))

st.divider()

# What changed
st.subheader("What Changed")
wc = data.get("what_changed", {})
cols = st.columns(4)
with cols[0]:
    st.metric("Revenue Δ", f"{wc.get('revenue_delta_pct', 0)*100:.1f}%")
with cols[1]:
    st.metric("Orders Δ", f"{wc.get('orders_delta_pct', 0)*100:.1f}%")
with cols[2]:
    st.metric("Ad Spend Δ", f"{wc.get('ad_spend_delta_pct', 0)*100:.1f}%")
with cols[3]:
    st.metric("ROAS Δ", f"{wc.get('roas_delta_pct', 0)*100:.1f}%")

st.divider()

# Insights
st.subheader("Priority Insights")
insights = data.get("insights", [])
if not insights:
    st.info("No business insights in the selected window. Run the operational cycle to generate intelligence.")
else:
    for insight in insights:
        severity = insight.get("severity", "info")
        card_class = {
            "critical": "insight-critical",
            "high": "insight-high",
            "warning": "insight-warning",
            "notice": "insight-warning",
        }.get(severity, "insight-info")
        with st.expander(f"[{severity.upper()}] {insight.get('title', 'Insight')}", expanded=False):
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            st.markdown(f"**{insight.get('explanation', '—')}**")
            if insight.get("evidence"):
                st.json(insight["evidence"])
            st.markdown(f"_Generated: {insight.get('created_at', '—')}_")
            st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# Trends
st.subheader("Trends")
trends = data.get("trends", [])
if trends:
    df = pd.DataFrame(trends)
    st.dataframe(df, width='stretch', hide_index=True)
else:
    st.info("No trend snapshots available.")

st.divider()

# Daily sales
st.subheader("Daily Sales")
daily_sales = data.get("daily_sales", [])
if daily_sales:
    df = pd.DataFrame(daily_sales)
    st.dataframe(df, width='stretch', hide_index=True)
else:
    st.info("No daily sales data for the selected window.")

st.divider()

# Analytics summary
st.subheader("Analytics Summary")
analytics = data.get("analytics_summary", {})
if analytics:
    st.json(analytics)
else:
    st.info("Analytics summary unavailable.")

st.divider()
st.caption("CommerceOS Web COO Dashboard | Intelligence")
