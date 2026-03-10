import streamlit as st
import json
from datetime import datetime

# Page config
st.set_page_config(
    page_title="PPMJ Ads - Shopee Automation",
    page_icon="🦊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f1f1f;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        border-left: 4px solid #667eea;
    }
    .status-active {
        color: #28a745;
        font-weight: bold;
    }
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    .status-critical {
        color: #dc3545;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">🦊 PPMJ Ads</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Shopee Seller Automation Platform | Automated Monitoring & Management</p>', unsafe_allow_html=True)
st.divider()

# Sidebar
st.sidebar.header("⚙️ Quick Actions")
st.sidebar.button("🔄 Refresh Stock Check", disabled=True)
st.sidebar.button("📊 Generate Report", disabled=True)
st.sidebar.button("🔔 Test Alert", disabled=True)

st.sidebar.divider()
st.sidebar.header("📈 System Status")
st.sidebar.metric("Last Check", "2 hours ago")
st.sidebar.metric("Stock Alerts", "2 Critical")
st.sidebar.metric("Ad Balance", "Rp 0")

# Main content - 3 columns
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📦 Stock Monitoring")
    st.markdown('<p class="status-critical">🚨 2 Critical Alerts</p>', unsafe_allow_html=True)
    st.write("- Produk Tes Payung (Red): 50 left")
    st.write("- Produk Tes Payung (Blue): 100 left")
    st.caption("Checks every 4 hours automatically")

with col2:
    st.subheader("📊 Ad Performance")
    st.markdown('<p class="status-warning">⚠️ Balance Low</p>', unsafe_allow_html=True)
    st.write("- Balance: Rp 0")
    st.write("- ROAS: N/A")
    st.write("- Status: Needs top-up")
    st.caption("Monitors daily at 9 AM")

with col3:
    st.subheader("📋 Orders & Returns")
    st.markdown('<p class="status-active">✅ No Issues</p>', unsafe_allow_html=True)
    st.write("- No returns pending")
    st.write("- No cancellations")
    st.write("- 0 orders this week")
    st.caption("Checks every 6 hours")

st.divider()

# Automation Schedule
st.subheader("⏰ Automation Schedule")

schedule_data = [
    ["Stock Check", "Every 4 hours", "✅ Active"],
    ["Order Monitor", "Every 6 hours", "✅ Active"],
    ["Price Check", "Daily 8 AM", "✅ Active"],
    ["Ad Check", "Daily 9 AM", "✅ Active"],
    ["Growth Insights", "Daily 10 AM", "✅ Active"],
    ["Full Report", "Daily 7 AM", "✅ Active"],
    ["Monthly Report", "29th 11:59 PM", "✅ Active"]
]

st.table({
    "Task": [row[0] for row in schedule_data],
    "Frequency": [row[1] for row in schedule_data],
    "Status": [row[2] for row in schedule_data]
})

st.divider()

# API Connection Status
st.subheader("🔗 API Connection")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Environment", "🚀 PRODUCTION", "Live Mode")
with col2:
    st.metric("Partner ID", "2030653")
with col3:
    st.metric("Shop ID", "1147948100")

st.divider()

# Recent Activity
st.subheader("📝 Recent Activity")

logs = [
    {"Time": "2026-02-26 19:04", "Event": "Stock check completed", "Status": "✅"},
    {"Time": "2026-02-26 19:04", "Event": "Critical stock alert: Red variant", "Status": "🚨"},
    {"Time": "2026-02-26 19:04", "Event": "Critical stock alert: Blue variant", "Status": "🚨"},
    {"Time": "2026-02-26 18:30", "Event": "Monthly report generated", "Status": "✅"},
    {"Time": "2026-02-26 18:28", "Event": "Full automation check", "Status": "✅"},
]

st.table({
    "Time": [log["Time"] for log in logs],
    "Event": [log["Event"] for log in logs],
    "Status": [log["Status"] for log in logs]
})

st.divider()

# Footer
st.caption("PPMJ Ads - Shopee Open Platform Integration | Built with ❤️ by Gerard")
