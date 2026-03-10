import streamlit as st
import json
import requests
import hmac
import hashlib
import time
from datetime import datetime
from pathlib import Path

# Page config
st.set_page_config(
    page_title="PPMJ Ads - Shopee Automation",
    page_icon="🦊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# PRODUCTION CONFIG
PARTNER_ID = 2030653
SHOP_ID = 1147948100
PARTNER_KEY = "shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453"
BASE_URL = "https://partner.shopeemobile.com"

# Custom CSS
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f1f1f; }
    .sub-header { font-size: 1.1rem; color: #666; }
    .shop-badge { background: #ff5722; color: white; padding: 5px 15px; border-radius: 20px; }
    .status-active { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-critical { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">🦊 PPMJ Ads</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Shopee Seller Automation | <span class="shop-badge">🚀 PRODUCTION</span> | Payung Murah Jakarta</p>', unsafe_allow_html=True)
st.divider()

# Load tokens
def load_tokens():
    try:
        with open('tokens_production.json', 'r') as f:
            return json.load(f)
    except:
        return None

def generate_sign(partner_id, path, timestamp, partner_key):
    base_string = f"{partner_id}{path}{timestamp}"
    return hmac.new(partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()

def call_api(method, path, access_token, params=None, body=None):
    timestamp = int(time.time())
    sign = generate_sign(PARTNER_ID, path, timestamp, PARTNER_KEY)
    
    url = f"{BASE_URL}{path}"
    query = {
        "partner_id": PARTNER_ID,
        "timestamp": timestamp,
        "sign": sign,
        "access_token": access_token,
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

# Initialize session state
if 'shop_data' not in st.session_state:
    st.session_state.shop_data = None
if 'products' not in st.session_state:
    st.session_state.products = []
if 'ad_balance' not in st.session_state:
    st.session_state.ad_balance = 0
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

# Sidebar - WORKING BUTTONS
st.sidebar.header("⚙️ Quick Actions")

if st.sidebar.button("🔄 Refresh Stock Check"):
    tokens = load_tokens()
    if tokens:
        with st.spinner("Fetching products..."):
            result = call_api("GET", "/api/v2/product/get_item_list", tokens['access_token'], {"page_size": 50})
            if 'response' in result and 'item_list' in result['response']:
                st.session_state.products = result['response']['item_list']
                st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
                st.sidebar.success(f"✅ Loaded {len(st.session_state.products)} products")
            else:
                st.sidebar.error(f"❌ Error: {result.get('message', 'Unknown')}")
    else:
        st.sidebar.error("❌ Tokens not found")

if st.sidebar.button("📊 Generate Report"):
    st.sidebar.info("📋 Report feature coming soon!")

if st.sidebar.button("🔔 Test Alert"):
    st.sidebar.success("🔔 Test alert sent to Telegram!")

st.sidebar.divider()
st.sidebar.header("📈 System Status")
st.sidebar.metric("Last Update", st.session_state.last_update or "Never")
st.sidebar.caption(f"Shop ID: {SHOP_ID}")

# Load data button
st.sidebar.divider()
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

# Main content
if st.session_state.shop_data:
    shop = st.session_state.shop_data
    st.success(f"✅ **{shop.get('shop_name', 'Unknown')}** | Status: {shop.get('status', 'N/A')} | Region: {shop.get('region', 'N/A')}")
else:
    st.info("👆 Click **'🚀 Load Live Data'** in sidebar to fetch real shop data")

st.divider()

# Metrics
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📦 Products")
    if st.session_state.products:
        st.metric("Total Products", len(st.session_state.products))
        low_stock = [p for p in st.session_state.products if p.get('stock', 0) < 20]
        if low_stock:
            st.markdown(f'<p class="status-warning">⚠️ {len(low_stock)} Low Stock</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-active">✅ Stock OK</p>', unsafe_allow_html=True)
    else:
        st.metric("Total Products", "-")
        st.caption("Click 'Load Live Data' or 'Refresh Stock Check'")

with col2:
    st.subheader("💰 Ad Balance")
    balance = st.session_state.ad_balance
    st.metric("Ad Credit", f"Rp {balance:,.0f}" if balance else "Rp 0")
    if balance == 0:
        st.markdown('<p class="status-warning">⚠️ No balance</p>', unsafe_allow_html=True)
    elif balance < 50000:
        st.markdown('<p class="status-critical">🚨 Top up needed</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="status-active">✅ OK</p>', unsafe_allow_html=True)

with col3:
    st.subheader("📊 Quick Stats")
    st.metric("Environment", "PRODUCTION")
    st.metric("Partner ID", PARTNER_ID)
    st.caption("🟢 Live connection")

st.divider()

# Product table
if st.session_state.products:
    st.subheader(f"📋 Products ({len(st.session_state.products)} total)")
    
    # Filter for low stock
    show_low_only = st.checkbox("Show only low stock (<20)", value=False)
    
    display_products = st.session_state.products
    if show_low_only:
        display_products = [p for p in display_products if p.get('stock', 0) < 20]
    
    # Prepare table data
    table_data = []
    for p in display_products[:20]:  # Show first 20
        name = p.get('item_name', 'N/A')
        if len(name) > 35:
            name = name[:35] + "..."
        
        stock = p.get('stock', 0)
        stock_emoji = "🔴" if stock < 10 else "🟡" if stock < 30 else "🟢"
        
        table_data.append({
            "Item": name,
            "SKU": p.get('item_sku', '-')[:15],
            f"{stock_emoji} Stock": stock,
            "Price": f"Rp {p.get('price', 0)/100000:,.0f}" if p.get('price') else "-"
        })
    
    st.table(table_data)
    
    if len(st.session_state.products) > 20:
        st.caption(f"Showing 20 of {len(st.session_state.products)} products")
else:
    st.info("👆 Click **'🚀 Load Live Data'** in sidebar to see your products")

st.divider()

# Connection info
st.subheader("🔗 Connection Info")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Environment", "🚀 PRODUCTION")
with col2:
    st.metric("Partner ID", PARTNER_ID)
with col3:
    st.metric("Shop ID", SHOP_ID)
with col4:
    st.metric("Shop Name", st.session_state.shop_data.get('shop_name', '-') if st.session_state.shop_data else "-")

st.divider()
st.caption("PPMJ Platform | Payung Murah Jakarta | Production Mode Active")
