import streamlit as st
import json
from datetime import datetime
import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="PPMJ Ads - Shopee Automation",
    page_icon="🦊",
    layout="wide"
)

# Header
st.title("🦊 PPMJ Ads - Shopee Automation Dashboard")
st.markdown("*Automated monitoring and management for Shopee sellers*")
st.divider()

# Sidebar
st.sidebar.header("⚙️ Quick Actions")
st.sidebar.button("🔄 Refresh Stock Check", disabled=True)
st.sidebar.button("📊 Generate Report", disabled=True)
st.sidebar.button("🔔 Test Alert", disabled=True)

st.sidebar.divider()
st.sidebar.header("📈 Status")
st.sidebar.metric("Last Check", "2 hours ago")
st.sidebar.metric("Stock Alerts", "2 Critical")
st.sidebar.metric("Ad Balance", "Rp 0")

# Main content
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📦 Stock Monitoring")
    st.info("🚨 2 products at critical stock (≤101)")
    st.write("- Produk Tes Payung (Red): 50 left")
    st.write("- Produk Tes Payung (Blue): 100 left")
    st.caption("Checks every 4 hours automatically")

with col2:
    st.subheader("📊 Ad Performance")
    st.warning("⚠️ Ad balance critically low")
    st.write("- Balance: Rp 0")
    st.write("- ROAS: N/A (no active campaigns)")
    st.write("- Status: Needs top-up")
    st.caption("Monitors daily at 9 AM")

with col3:
    st.subheader("📋 Orders & Returns")
    st.success("✅ No issues found")
    st.write("- No returns pending")
    st.write("- No cancellations")
    st.write("- 0 orders this week")
    st.caption("Checks every 6 hours")

st.divider()

# Automation Schedule
st.subheader("⏰ Automation Schedule")
schedule_data = {
    "Task": ["Stock Check", "Order Monitor", "Price Check", "Ad Check", "Growth Insights", "Full Report", "Monthly Report"],
    "Frequency": ["Every 4 hours", "Every 6 hours", "Daily 8 AM", "Daily 9 AM", "Daily 10 AM", "Daily 7 AM", "29th 11:59 PM"],
    "Status": ["✅ Active", "✅ Active", "✅ Active", "✅ Active", "✅ Active", "✅ Active", "✅ Active"]
}

import pandas as pd
df = pd.DataFrame(schedule_data)
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# API Connection Status
st.subheader("🔗 API Connection")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Environment", "🏗️ Sandbox", "Testing phase")
with col2:
    st.metric("Partner ID", "1221616")
with col3:
    st.metric("Shop ID", "226682118")

st.divider()

# Recent Logs
st.subheader("📝 Recent Activity")
logs = [
    {"Time": "2026-02-26 19:04", "Event": "Stock check completed", "Status": "✅"},
    {"Time": "2026-02-26 19:04", "Event": "Critical stock alert: Red variant", "Status": "🚨"},
    {"Time": "2026-02-26 19:04", "Event": "Critical stock alert: Blue variant", "Status": "🚨"},
    {"Time": "2026-02-26 18:30", "Event": "Monthly report generated", "Status": "✅"},
    {"Time": "2026-02-26 18:28", "Event": "Full automation check", "Status": "✅"},
]

logs_df = pd.DataFrame(logs)
st.dataframe(logs_df, use_container_width=True, hide_index=True)

st.divider()

# Footer
st.caption("PPMJ Ads - Shopee Open Platform Integration | Built with ❤️ by Gerard")
