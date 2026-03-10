import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="PPMJ Platform - Shopee Automation",
    page_icon="🦊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Navigation
st.sidebar.title("🦊 PPMJ Platform")
app_mode = st.sidebar.radio(
    "Select App",
    ["🏪 Seller Dashboard", "📢 Ads Manager"]
)

if app_mode == "🏪 Seller Dashboard":
    # =====================================
    # PPMJ SELLER DASHBOARD
    # =====================================
    
    st.title("🦊 PPMJ Ads")
    st.markdown("*Shopee Seller Automation Platform | Automated Monitoring & Management*")
    st.divider()

    # Sidebar extras for Seller
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
        st.error("🚨 2 Critical Alerts")
        st.write("- Produk Tes Payung (Red): 50 left")
        st.write("- Produk Tes Payung (Blue): 100 left")
        st.caption("Checks every 4 hours automatically")

    with col2:
        st.subheader("📊 Ad Performance")
        st.warning("⚠️ Balance Low")
        st.write("- Balance: Rp 0")
        st.write("- ROAS: N/A")
        st.write("- Status: Needs top-up")
        st.caption("Monitors daily at 9 AM")

    with col3:
        st.subheader("📋 Orders & Returns")
        st.success("✅ No Issues")
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

elif app_mode == "📢 Ads Manager":
    # =====================================
    # PPMJ ADS MANAGER
    # =====================================
    
    st.title("📢 PPMJ Ads - Campaign Manager")
    st.markdown("*Create and manage Shopee ad campaigns*")
    st.divider()
    
    # Sidebar for Ads
    ads_tab = st.sidebar.radio(
        "Ads Section",
        ["📈 Dashboard", "➕ Create Campaign", "📊 Campaign List", "⚙️ Auto-Optimizer"]
    )
    
    if ads_tab == "📈 Dashboard":
        st.subheader("📈 Ads Performance Overview")
        
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
        
        st.subheader("🎯 Campaign Status")
        campaigns = [
            {"name": "Flash Sale Promo", "status": "🟢 Active", "budget": "100k/day", "roas": "3.2x"},
            {"name": "New Arrival Boost", "status": "🟡 Scheduled", "budget": "50k/day", "roas": "-"},
            {"name": "Clearance Sale", "status": "🔴 Paused", "budget": "0", "roas": "1.8x"},
        ]
        
        for camp in campaigns:
            cols = st.columns([3, 2, 2, 2, 1])
            cols[0].write(f"**{camp['name']}**")
            cols[1].write(camp['status'])
            cols[2].write(camp['budget'])
            cols[3].write(f"ROAS: {camp['roas']}")
            cols[4].button("Edit", key=f"edit_{camp['name']}")
        
        st.info("ℹ️ **Note:** Live ad data requires production API access.")
    
    elif ads_tab == "➕ Create Campaign":
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
            st.date_input("End Date", datetime.now())
        
        with col2:
            st.multiselect(
                "Select Products",
                ["Produk Tes Payung (Red)", "Produk Tes Payung (Blue)"],
                default=["Produk Tes Payung (Red)"]
            )
            
            if campaign_type == "GMV Max (AI Optimized)":
                st.selectbox("Optimization Goal", ["Maximize GMV", "Maximize Orders", "Balance Both"])
                st.slider("ROAS Target", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
            else:
                st.number_input("Bid per Click (IDR)", min_value=100, value=500, step=100)
        
        st.divider()
        
        if st.button("🚀 Create Campaign", type="primary"):
            st.success("✅ Campaign created! (Mock - requires production API)")
    
    elif ads_tab == "📊 Campaign List":
        st.subheader("📊 All Campaigns")
        
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
    
    elif ads_tab == "⚙️ Auto-Optimizer":
        st.subheader("⚙️ Auto-Optimizer Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.checkbox("✅ Auto-pause low ROAS campaigns", value=True)
            st.number_input("Pause if ROAS below", min_value=0.5, max_value=5.0, value=1.5, step=0.1)
            st.checkbox("✅ Auto-increase budget for high performers", value=True)
        
        with col2:
            st.checkbox("✅ Auto-adjust bids", value=False)
            st.checkbox("✅ Send alerts to Telegram", value=True)
            st.selectbox("Check frequency", ["Every hour", "Every 6 hours", "Daily"])
        
        if st.button("💾 Save Settings"):
            st.success("Settings saved!")

st.divider()
st.caption("PPMJ Platform - Shopee Open Platform Integration | Built with ❤️ by Gerard")
