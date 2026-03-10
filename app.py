import streamlit as st
import json
import requests
import hmac
import hashlib
import time
import os
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

# DEBUG: Show working directory and files
st.sidebar.header("🔧 Debug Info")
st.sidebar.code(f"CWD: {os.getcwd()}")

# Check for tokens file in multiple locations
tokens_paths = [
    'tokens_production.json',
    '/app/tokens_production.json',
    '/home/appuser/tokens_production.json',
    str(Path(__file__).parent / 'tokens_production.json')
]

tokens_found = []
for p in tokens_paths:
    if os.path.exists(p):
        tokens_found.append(f"✅ {p}")
    else:
        tokens_found.append(f"❌ {p}")

st.sidebar.code("\n".join(tokens_found))

# Load tokens with full path
def load_tokens():
    paths_to_try = [
        Path('tokens_production.json').resolve(),
        Path(__file__).parent / 'tokens_production.json',
        Path('/app/tokens_production.json'),
    ]
    
    for p in paths_to_try:
        try:
            if p.exists():
                with open(p, 'r') as f:
                    return json.load(f)
        except Exception as e:
            st.sidebar.code(f"Error loading {p}: {e}")
    
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
            r = requests.get(url, params=query, headers=headers, timeout=15)
        else:
            r = requests.post(url, params=query, json=body or {}, headers=headers, timeout=15)
        
        result = r.json()
        
        # Debug: show status
        if 'error' in result:
            st.sidebar.code(f"API Error: {result.get('message', 'Unknown')}")
        
        return result
    except Exception as e:
        st.sidebar.code(f"Request Error: {str(e)[:100]}")
        return {"error": str(e)}

# Navigation
st.sidebar.title("🦊 PPMJ Platform")
app_mode = st.sidebar.radio("Select App", ["🏪 Seller Dashboard", "📢 Ads Manager"])

if app_mode == "🏪 Seller Dashboard":
    st.title("🦊 PPMJ Ads")
    st.markdown("*Shopee Seller Automation | 🚀 PRODUCTION | Payung Murah Jakarta*")
    st.divider()

    # Session state
    if 'shop_data' not in st.session_state:
        st.session_state.shop_data = None
    if 'products' not in st.session_state:
        st.session_state.products = []
    if 'ad_balance' not in st.session_state:
        st.session_state.ad_balance = 0
    if 'api_error' not in st.session_state:
        st.session_state.api_error = None

    # Actions
    st.sidebar.header("⚙️ Actions")
    
    if st.sidebar.button("🚀 Load Live Data"):
        tokens = load_tokens()
        
        if not tokens:
            st.session_state.api_error = "❌ Tokens file not found in any location"
            st.error(st.session_state.api_error)
        else:
            st.sidebar.code(f"Token loaded: {tokens.get('access_token', 'N/A')[:20]}...")
            
            with st.spinner("Calling API..."):
                # Test shop info
                shop_result = call_api("GET", "/api/v2/shop/get_shop_info", tokens['access_token'])
                st.sidebar.code(f"Shop result keys: {list(shop_result.keys())}")
                
                if 'response' in shop_result:
                    st.session_state.shop_data = shop_result['response']
                    st.success(f"✅ Connected: {shop_result['response'].get('shop_name', 'Unknown')}")
                else:
                    st.error(f"❌ Shop API failed: {shop_result.get('message', 'No response')}")
                    st.session_state.api_error = str(shop_result)
                
                # Get ad balance
                ad_result = call_api("GET", "/api/v2/ads/get_total_balance", tokens['access_token'])
                if 'response' in ad_result:
                    st.session_state.ad_balance = ad_result['response'].get('total_balance', 0)
                else:
                    st.warning(f"Ad balance error: {ad_result.get('message', 'N/A')}")
                
                # Get products
                prod_result = call_api("GET", "/api/v2/product/get_item_list", tokens['access_token'], {"page_size": 50})
                if 'response' in prod_result and 'item_list' in prod_result['response']:
                    st.session_state.products = prod_result['response']['item_list']
                else:
                    st.warning(f"Products error: {prod_result.get('message', 'N/A')}")
                
                st.rerun()

    # Display data
    if st.session_state.shop_data:
        shop = st.session_state.shop_data
        st.success(f"✅ **{shop.get('shop_name', 'Unknown')}** | {shop.get('status', 'N/A')} | {shop.get('region', 'N/A')}")
    else:
        st.info("👆 Click **'🚀 Load Live Data'** to fetch your real shop data")
    
    if st.session_state.api_error:
        st.error(f"Last Error: {st.session_state.api_error[:200]}")

    st.divider()

    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("📦 Products")
        st.metric("Total", len(st.session_state.products) if st.session_state.products else 0)
    with col2:
        st.subheader("💰 Ad Balance")
        st.metric("Credit", f"Rp {st.session_state.ad_balance:,.0f}")
    with col3:
        st.subheader("🔗 Connection")
        st.metric("Status", "🚀 PRODUCTION")

    # Products table
    if st.session_state.products:
        st.divider()
        st.subheader(f"📋 Products ({len(st.session_state.products)})")
        
        table_data = []
        for p in st.session_state.products[:15]:
            table_data.append({
                "Name": p.get('item_name', 'N/A')[:30],
                "Stock": p.get('stock', 0),
                "Price": f"Rp {p.get('price', 0):,.0f}"
            })
        st.table(table_data)

elif app_mode == "📢 Ads Manager":
    st.title("📢 Ads Manager")
    st.info("Ads management features coming soon!")

st.divider()
st.caption("PPMJ Platform | Production Mode")
