"""Analytics page for the Web COO Dashboard."""
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.coo.web_service import WebCOODashboardService
from commerceos.platform.database.connection import get_session

st.set_page_config(page_title="Analytics — CommerceOS", page_icon="📊", layout="wide")

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


st.title("📊 Analytics")
st.caption("Campaign, SKU, financial, and inventory analytics from Epic 5.")

session = _get_session()
service = WebCOODashboardService(session, store_id=STORE_ID)

days = st.sidebar.slider("Window (days)", 7, 90, 30)
data = service.get_analytics(days=days)

if data.get("errors"):
    with st.expander("Warnings"):
        for error in data["errors"]:
            st.caption(f"⚠️ {error}")

# Financial
st.subheader("Financial")
financial = data.get("financial", {})
actual = financial.get("actual_pnl", {})
cols = st.columns(4)
with cols[0]:
    st.metric("Revenue", _currency(actual.get("revenue", 0)))
with cols[1]:
    st.metric("Marketplace Fees", _currency(actual.get("marketplace_fees", 0)))
with cols[2]:
    st.metric("Advertising", _currency(actual.get("advertising", 0)))
with cols[3]:
    st.metric("Contribution Profit", _currency(actual.get("contribution_profit", 0)))

for note in actual.get("notes", []):
    st.caption(f"ℹ️ {note}")

st.divider()

# SKU profitability
st.subheader("SKU Profitability")
summary = data.get("summary", {})
sku_data = summary.get("sku_profitability", {}).get("skus", [])
if sku_data:
    st.dataframe(pd.DataFrame(sku_data), width='stretch', hide_index=True)
else:
    st.info("No SKU profitability data.")

st.divider()

# Campaign profitability
st.subheader("Campaign Profitability")
campaign_data = summary.get("campaign_profitability", {}).get("campaigns", [])
if campaign_data:
    st.dataframe(pd.DataFrame(campaign_data), width='stretch', hide_index=True)
else:
    st.info("No campaign profitability data.")

st.divider()

# Inventory
st.subheader("Inventory Intelligence")
inventory = data.get("inventory", {})
recs = inventory.get("recommendations", [])
if recs:
    st.dataframe(pd.DataFrame(recs), width='stretch', hide_index=True)
else:
    st.info("No inventory recommendations.")

st.divider()

# Forecast
st.subheader("Sales Forecast (14 days)")
forecast = data.get("sales_forecast", {})
if forecast.get("points"):
    st.dataframe(pd.DataFrame(forecast["points"]), width='stretch', hide_index=True)
else:
    st.info(forecast.get("notes", ["No sales forecast available."])[0])

st.divider()
st.caption("CommerceOS Web COO Dashboard | Analytics")
