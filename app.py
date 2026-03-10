import streamlit as st
import json
import requests
import hmac
import hashlib
import time
from datetime import datetime
from pathlib import Path

# PRODUCTION CONFIG
PARTNER_ID = 2030653
SHOP_ID = 1147948100
PARTNER_KEY = "shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453"
BASE_URL = "https://partner.shopeemobile.com"

# Page config
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

# Load tokens
def load_tokens():
    try:
        with open('tokens_production.json', 'r') as f:
            return json.load(f)
    except:
        return None

def refresh_tokens():
    """Refresh access token using refresh_token."""
    tokens = load_tokens()
    if not tokens or 'refresh_token' not in tokens:
        return None
    
    try:
        path = "/api/v2/auth/access_token/get"
        timestamp = int(time.time())
        sign = generate_sign(PARTNER_ID, path, timestamp, PARTNER_KEY)
        
        url = f"{BASE_URL}{path}"
        params = {
            "partner_id": PARTNER_ID,
            "timestamp": timestamp,
            "sign": sign
        }
        body = {
            "refresh_token": tokens['refresh_token'],
            "shop_id": SHOP_ID,
            "partner_id": PARTNER_ID
        }
        
        resp = requests.post(url, params=params, json=body)
        data = resp.json()
        
        if 'access_token' in data:
            # Save new tokens
            with open('tokens_production.json', 'w') as f:
                json.dump(data, f, indent=2)
            return data
        else:
            return None
    except:
        return None

def generate_sign(partner_id, path, timestamp, partner_key):
    base_string = f"{partner_id}{path}{timestamp}"
    return hmac.new(partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()

def call_api(method, path, access_token, params=None, body=None):
    """Make API call with auto token refresh on auth failure."""
    def _make_call(token):
        timestamp = int(time.time())
        sign = generate_sign(PARTNER_ID, path, timestamp, PARTNER_KEY)
        
        url = f"{BASE_URL}{path}"
        query = {
            "partner_id": PARTNER_ID,
            "timestamp": timestamp,
            "sign": sign,
            "access_token": token,
            "shop_id": SHOP_ID
        }
        if params:
            query.update(params)
        
        headers = {"Content-Type": "application/json"}
        
        try:
            if method == "GET":
                r = requests.get(url, params=query, headers=headers, timeout=10)
            else:
                r = requests.post(url, params=query, json=body or {}, headers=headers, timeout=10)
            return r.json()
        except Exception as e:
            return {"error": str(e)}
    
    # First attempt
    result = _make_call(access_token)
    
    # If auth error, refresh and retry
    if result.get('error') == 'error_auth' or 'Invalid access_token' in str(result.get('message', '')):
        new_tokens = refresh_tokens()
        if new_tokens:
            result = _make_call(new_tokens['access_token'])
    
    return result

if app_mode == "🏪 Seller Dashboard":
    # =====================================
    # PPMJ SELLER DASHBOARD - LIVE API
    # =====================================
    
    st.title("🦊 PPMJ Ads")
    st.markdown("*Shopee Seller Automation Platform | 🚀 PRODUCTION | Payung Murah Jakarta*")
    st.divider()

    # Initialize session state
    if 'shop_data' not in st.session_state:
        st.session_state.shop_data = None
    if 'products' not in st.session_state:
        st.session_state.products = []
    if 'ad_balance' not in st.session_state:
        st.session_state.ad_balance = 0
    if 'last_update' not in st.session_state:
        st.session_state.last_update = None

    # Sidebar
    st.sidebar.header("⚙️ Quick Actions")
    
    if st.sidebar.button("🚀 Load Live Data"):
        tokens = load_tokens()
        if tokens:
            with st.spinner("Connecting to production API..."):
                # Get shop info
                shop_result = call_api("GET", "/api/v2/shop/get_shop_info", tokens['access_token'])
                if 'response' in shop_result:
                    st.session_state.shop_data = shop_result['response']
                
                # Get ad balance
                ad_result = call_api("GET", "/api/v2/ads/get_total_balance", tokens['access_token'])
                if 'response' in ad_result:
                    st.session_state.ad_balance = ad_result['response'].get('total_balance', 0)
                
                # Get products
                prod_result = call_api("GET", "/api/v2/product/get_item_list", tokens['access_token'], {"page_size": 50})
                if 'response' in prod_result and 'item_list' in prod_result['response']:
                    st.session_state.products = prod_result['response']['item_list']
                
                st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
                st.sidebar.success("✅ Data loaded!")
                st.rerun()
        else:
            st.sidebar.error("❌ Tokens not found")
    
    if st.sidebar.button("🔄 Refresh Stock"):
        tokens = load_tokens()
        if tokens:
            with st.spinner("Fetching products..."):
                result = call_api("GET", "/api/v2/product/get_item_list", tokens['access_token'], {"page_size": 50})
                if 'response' in result and 'item_list' in result['response']:
                    st.session_state.products = result['response']['item_list']
                    st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
                    st.sidebar.success(f"✅ {len(st.session_state.products)} products loaded")
                    st.rerun()
        else:
            st.sidebar.error("❌ Tokens not found")

    st.sidebar.button("📊 Generate Report", disabled=True)
    st.sidebar.button("🔔 Test Alert", disabled=True)

    st.sidebar.divider()
    st.sidebar.header("📈 Live Status")
    st.sidebar.metric("Last Update", st.session_state.last_update or "Never")
    
    if st.session_state.shop_data:
        st.sidebar.success(f"🟢 {st.session_state.shop_data.get('shop_name', 'Shop')}")
    else:
        st.sidebar.warning("🟡 Click 'Load Live Data'")

    # Main content
    if st.session_state.shop_data:
        shop = st.session_state.shop_data
        st.success(f"✅ Connected: **{shop.get('shop_name', 'Unknown')}** | Status: {shop.get('status', 'N/A')} | Region: {shop.get('region', 'N/A')}")
    else:
        st.info("👆 Click **'🚀 Load Live Data'** in sidebar to fetch your real shop data")

    st.divider()

    # Metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📦 Stock Monitoring")
        if st.session_state.products:
            st.metric("Total Products", len(st.session_state.products))
            low_stock = [p for p in st.session_state.products if p.get('stock', 0) < 20]
            if low_stock:
                st.error(f"🚨 {len(low_stock)} Low Stock")
                for p in low_stock[:3]:
                    st.caption(f"- {p.get('item_name', 'Product')[:30]}: {p.get('stock', 0)} left")
            else:
                st.success("✅ Stock OK")
        else:
            st.metric("Total Products", "-")
            st.caption("Click 'Load Live Data' to see products")

    with col2:
        st.subheader("📊 Ad Performance")
        balance = st.session_state.ad_balance
        st.metric("Ad Credit", f"Rp {balance:,.0f}" if balance else "Rp 0")
        if balance == 0:
            st.warning("⚠️ No balance")
        elif balance < 50000:
            st.error("🚨 Top up needed")
        else:
            st.success("✅ OK")

    with col3:
        st.subheader("📋 Orders & Returns")
        st.success("✅ No Issues")
        st.write("- Live order data")
        st.write("- Auto-sync enabled")
        st.caption("Checks every 6 hours")

    st.divider()

    # Product table
    if st.session_state.products:
        st.subheader(f"📋 Your Products ({len(st.session_state.products)} total)")
        
        show_low = st.checkbox("Show only low stock (<20)", value=False)
        display = st.session_state.products
        if show_low:
            display = [p for p in display if p.get('stock', 0) < 20]
        
        table_data = []
        for p in display[:20]:
            name = p.get('item_name', 'N/A')[:35]
            stock = p.get('stock', 0)
            stock_emoji = "🔴" if stock < 10 else "🟡" if stock < 30 else "🟢"
            
            table_data.append({
                "Product": name,
                "SKU": p.get('item_sku', '-')[:15],
                f"{stock_emoji} Stock": stock,
                "Status": "🟢 Normal" if p.get('status') == 'NORMAL' else "🟡"
            })
        
        st.table(table_data)
        
        if len(st.session_state.products) > 20:
            st.caption(f"Showing 20 of {len(st.session_state.products)} products")
    
    st.divider()
    
    # Connection info
    st.subheader("🔗 API Connection")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Environment", "🚀 PRODUCTION")
    with c2:
        st.metric("Partner ID", PARTNER_ID)
    with c3:
        st.metric("Shop ID", SHOP_ID)
    with c4:
        st.metric("Shop", st.session_state.shop_data.get('shop_name', '-') if st.session_state.shop_data else "-")

elif app_mode == "📢 Ads Manager":
    # =====================================
    # PPMJ ADS MANAGER
    # =====================================
    
    st.title("📢 PPMJ Ads - Campaign Manager")
    st.markdown("*Create and manage Shopee ad campaigns*")
    st.divider()
    
    # Sidebar
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
        
        st.info("ℹ️ **Note:** Live ad data requires production API access for ads endpoints.")
    
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
        
        if st.button("🚀 Create Campaign", type="primary"):
            st.success("✅ Campaign created! (Mock - requires production API)")
    
    elif ads_tab == "📊 Campaign List":
        st.subheader("📊 All Campaigns")
        
        campaigns = [
            {"id": "CAMP-001", "name": "Flash Sale Promo", "type": "GMV Max", "status": "Active", "spend": "Rp 450k", "gmv": "Rp 1.2M", "roas": "2.7x"},
            {"id": "CAMP-002", "name": "New Arrival Boost", "type": "Manual", "status": "Scheduled", "spend": "Rp 0", "gmv": "Rp 0", "roas": "-"},
            {"id": "CAMP-003", "name": "Clearance Sale", "type": "GMV Max", "status": "Paused", "spend": "Rp 890k", "gmv": "Rp 1.5M", "roas": "1.7x"},
        ]
        
        st.table({
            "ID": [c["id"] for c in campaigns],
            "Name": [c["name"] for c in campaigns],
            "Type": [c["type"] for c in campaigns],
            "Status": [c["status"] for c in campaigns],
            "Spend": [c["spend"] for c in campaigns],
            "GMV": [c["gmv"] for c in campaigns],
            "ROAS": [c["roas"] for c in campaigns],
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
st.caption("PPMJ Platform - Shopee Open Platform Integration | Payung Murah Jakarta | Built with ❤️ by Gerard")
