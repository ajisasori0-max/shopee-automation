import streamlit as st
import json
from datetime import datetime, timedelta

st.set_page_config(
    page_title="PPMJ Ads - Campaign Manager",
    page_icon="📢",
    layout="wide"
)

st.title("📢 PPMJ Ads - Campaign Manager")
st.markdown("*Create and manage Shopee ad campaigns*")
st.divider()

# Sidebar
tab = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "➕ Create Campaign", "📊 Campaign List", "⚙️ Auto-Optimizer"]
)

if tab == "🏠 Dashboard":
    st.subheader("📈 Ads Performance Overview")
    
    # Mock data for sandbox
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Campaigns", "3", "+1 today")
    with col2:
        st.metric("Total Spend", "Rp 0", "Sandbox")
    with col3:
        st.metric("GMV Generated", "Rp 0", "Sandbox")
    with col4:
        st.metric("ROAS", "0.0x", "No data")
    
    st.divider()
    
    # Campaign status
    st.subheader("🎯 Campaign Status")
    campaigns = [
        {"name": "Flash Sale Promo", "status": "🟢 Active", "budget": "100k/day", "roas": "3.2x"},
        {"name": "New Arrival Boost", "status": "🟡 Scheduled", "budget": "50k/day", "roas": "-"},
        {"name": "Clearance Sale", "status": "🔴 Paused", "budget": "0", "roas": "1.8x"},
    ]
    
    for camp in campaigns:
        with st.container():
            cols = st.columns([3, 2, 2, 2, 1])
            cols[0].write(f"**{camp['name']}**")
            cols[1].write(camp['status'])
            cols[2].write(camp['budget'])
            cols[3].write(f"ROAS: {camp['roas']}")
            cols[4].button("Edit", key=f"edit_{camp['name']}")
    
    st.divider()
    st.info("ℹ️ **Note:** Live ad data requires production API access. Sandbox shows mock data for UI testing.")

elif tab == "➕ Create Campaign":
    st.subheader("➕ Create New Campaign")
    
    campaign_type = st.selectbox(
        "Campaign Type",
        ["GMV Max (AI Optimized)", "Manual Product Ads"]
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Campaign Name", placeholder="e.g., Flash Sale March")
        st.number_input("Daily Budget (IDR)", min_value=50000, value=100000, step=10000)
        st.date_input("Start Date", datetime.now())
        st.date_input("End Date", datetime.now() + timedelta(days=7))
    
    with col2:
        st.multiselect(
            "Select Products",
            ["Produk Tes Payung (Red)", "Produk Tes Payung (Blue)", "Product C", "Product D"],
            default=["Produk Tes Payung (Red)"]
        )
        
        if campaign_type == "GMV Max (AI Optimized)":
            st.selectbox("Optimization Goal", ["Maximize GMV", "Maximize Orders", "Balance Both"])
            st.slider("ROAS Target", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
        else:
            st.number_input("Bid per Click (IDR)", min_value=100, value=500, step=100)
    
    st.divider()
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🚀 Create Campaign", type="primary"):
            st.success("✅ Campaign created! (Mock - requires production API)")
    with col2:
        st.caption("In production, this creates a live campaign on Shopee.")

elif tab == "📊 Campaign List":
    st.subheader("📊 All Campaigns")
    
    filter_status = st.selectbox("Filter by Status", ["All", "Active", "Scheduled", "Paused", "Ended"])
    
    # Mock campaign data
    all_campaigns = [
        {"id": "CAMP-001", "name": "Flash Sale Promo", "type": "GMV Max", "status": "Active", "spend": "Rp 450k", "gmv": "Rp 1.2M", "roas": "2.7x"},
        {"id": "CAMP-002", "name": "New Arrival Boost", "type": "Manual", "status": "Scheduled", "spend": "Rp 0", "gmv": "Rp 0", "roas": "-"},
        {"id": "CAMP-003", "name": "Clearance Sale", "type": "GMV Max", "status": "Paused", "spend": "Rp 890k", "gmv": "Rp 1.5M", "roas": "1.7x"},
    ]
    
    st.table({
        "ID": [c["id"] for c in all_campaigns],
        "Name": [c["name"] for c in all_campaigns],
        "Type": [c["type"] for c in all_campaigns],
        "Status": [c["status"] for c in all_campaigns],
        "Spend": [c["spend"] for c in all_campaigns],
        "GMV": [c["gmv"] for c in all_campaigns],
        "ROAS": [c["roas"] for c in all_campaigns],
    })

elif tab == "⚙️ Auto-Optimizer":
    st.subheader("⚙️ Auto-Optimizer Settings")
    
    st.write("Automatically manage campaigns based on performance:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.checkbox("✅ Auto-pause low ROAS campaigns", value=True)
        st.number_input("Pause if ROAS below", min_value=0.5, max_value=5.0, value=1.5, step=0.1)
        
        st.checkbox("✅ Auto-increase budget for high performers", value=True)
        st.number_input("Increase budget if ROAS above", min_value=2.0, max_value=10.0, value=4.0, step=0.5)
    
    with col2:
        st.checkbox("✅ Auto-adjust bids", value=False)
        st.checkbox("✅ Send alerts to Telegram", value=True)
        
        st.selectbox("Check frequency", ["Every hour", "Every 6 hours", "Daily"])
    
    st.divider()
    
    if st.button("💾 Save Settings"):
        st.success("Settings saved! (Mock - requires production API)")
    
    st.info("ℹ️ Auto-optimizer runs via cron jobs every 6 hours in production.")

st.divider()
st.caption("PPMJ Ads - Shopee Ad Campaign Management | Built with ❤️ by Gerard")
