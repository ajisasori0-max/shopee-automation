import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Financial Dashboard", page_icon="📊", layout="wide")

st.markdown("""
<style>
.big-number { font-size: 2rem; font-weight: bold; }
.metric-label { font-size: 0.9rem; color: #666; }
.temp-badge { background: #fff3cd; color: #856404; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

st.title("📊 CommerceOS Financial Dashboard")
st.caption("Net sales, P&L, and ad performance from CommerceOS canonical tables.")

BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from commerceos.dashboard.query_service import DashboardQueryService

STORE_ID = st.secrets.get("COMMERCEOS_STORE_ID", "store-1")

@st.cache_resource
def get_query_service():
    return DashboardQueryService()

qs = get_query_service()

# --- Sidebar ---
st.sidebar.header("⚙️ Settings")

period = st.sidebar.selectbox(
    "Quick period",
    ["Last 7 days", "Last 30 days", "This month", "Last month", "Custom"],
    index=1,
)

end_date = datetime.now()
if period == "Last 7 days":
    start_date = end_date - timedelta(days=7)
elif period == "Last 30 days":
    start_date = end_date - timedelta(days=30)
elif period == "This month":
    start_date = end_date.replace(day=1)
elif period == "Last month":
    start_date = (end_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    end_date = end_date.replace(day=1) - timedelta(days=1)
else:
    start_date = st.sidebar.date_input("Start date", end_date - timedelta(days=30))
    end_date = st.sidebar.date_input("End date", end_date)

start_date = datetime.combine(start_date, datetime.min.time())
end_date = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1, seconds=-1)

st.sidebar.divider()

if st.sidebar.button("🔄 Sync Orders & Payments"):
    st.sidebar.info("Trigger via SyncEngine — not yet wired to button")

if st.sidebar.button("🔄 Sync Ads"):
    st.sidebar.info("Trigger via SyncEngine — not yet wired to button")

st.sidebar.divider()
st.sidebar.header("📊 Data Freshness")

with qs:
    freshness = qs.get_freshness(STORE_ID)
    for entity, info in freshness.items():
        hours = info["hours_since_sync"]
        if hours < 1:
            st.sidebar.success(f"🟢 {entity}: {hours*60:.0f}m ago")
        elif hours < 24:
            st.sidebar.warning(f"🟡 {entity}: {hours:.1f}h ago")
        else:
            st.sidebar.error(f"🔴 {entity}: {hours/24:.1f}d ago")

# --- Load data ---
with qs:
    daily_sales = qs.get_daily_sales(STORE_ID, start_date, end_date)
    pl = qs.get_pl_summary(STORE_ID, start_date, end_date)
    ads = qs.get_ad_performance_summary(STORE_ID, start_date, end_date)
    orders = qs.get_order_list(STORE_ID, start_date, end_date)

# --- KPIs ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Net Sales", f"Rp {pl['net_sales']:,.0f}", f"{pl['order_count']} orders")
with col2:
    st.metric("Gross Profit", f"Rp {pl['gross_profit']:,.0f}", f"{pl['gross_margin_pct']:.1f}% margin")
with col3:
    st.metric("Ad Spend", f"Rp {ads['total_spend']:,.0f}", f"{ads['roas']:.2f}x ROAS")
with col4:
    st.metric("AOV", f"Rp {pl['aov']:,.0f}")

st.divider()

# --- Charts ---
if daily_sales:
    df = pd.DataFrame(daily_sales)
    df["date"] = pd.to_datetime(df["date"])

    col_left, col_right = st.columns(2)

    with col_left:
        fig = px.line(df, x="date", y=["gross_sales", "net_income"],
                      labels={"value": "Amount (Rp)", "variable": "Metric"},
                      title="Daily Sales Trend")
        st.plotly_chart(fig, width='stretch')

    with col_right:
        fig2 = px.bar(df, x="date", y="order_count",
                      labels={"order_count": "Orders", "date": "Date"},
                      title="Daily Orders")
        st.plotly_chart(fig2, width='stretch')
else:
    st.info("No orders in this period. Run a sync to populate CommerceOS.")

st.divider()

# --- Financial Statements ---
tab1, tab2, tab3, tab4 = st.tabs(["P&L", "Ad Performance", "Order Details", "Data Quality"])

with tab1:
    st.caption('<span class="temp-badge">TEMPORARY</span> Computed from canonical tables. Will switch to KPI Engine in E1.4.', unsafe_allow_html=True)
    pl_data = [
        ["Gross Sales", pl["gross_sales"]],
        ["Less: Discounts", -pl["discounts"]],
        ["Net Sales", pl["net_sales"]],
        ["Shopee Fees", -pl["shopee_fees"]],
        ["Gross Profit", pl["gross_profit"]],
        ["Gross Margin %", f"{pl['gross_margin_pct']:.2f}%"],
    ]
    st.dataframe(pd.DataFrame(pl_data, columns=["Item", "Amount"]), width='stretch', hide_index=True)

with tab2:
    st.caption('<span class="temp-badge">TEMPORARY</span> From canonical AdPerformance.', unsafe_allow_html=True)
    ads_data = [
        ["Total Spend", ads["total_spend"]],
        ["Total Revenue", ads["total_revenue"]],
        ["ROAS", f"{ads['roas']:.2f}x"],
        ["Impressions", ads["total_impressions"]],
        ["Clicks", ads["total_clicks"]],
        ["CTR", f"{ads['ctr']:.2f}%"],
        ["Conversions", ads["total_conversions"]],
    ]
    st.dataframe(pd.DataFrame(ads_data, columns=["Metric", "Value"]), width='stretch', hide_index=True)

with tab3:
    if orders:
        st.dataframe(pd.DataFrame(orders), width='stretch', hide_index=True)
    else:
        st.info("No orders to display.")

with tab4:
    with qs:
        dq = qs.get_data_quality_summary(STORE_ID)
        st.subheader("Missing Provenance")
        if dq["missing_provenance"]:
            st.dataframe(pd.DataFrame(dq["missing_provenance"]), width='stretch', hide_index=True)
        else:
            st.success("✅ All canonical records have provenance")

        st.subheader("Recent Failures")
        if dq["recent_failures"]:
            st.dataframe(pd.DataFrame(dq["recent_failures"]), width='stretch', hide_index=True)
        else:
            st.success("✅ No recent sync failures")

st.divider()
st.caption("PPMJ Platform | Payung Murah Jakarta | CommerceOS Financial Dashboard")
