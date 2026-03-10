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

def load_tokens():
    try:
        with open('tokens_production.json', 'r') as f:
            return json.load(f)
    except:
        return None

def generate_sign(partner_id, path, timestamp, partner_key, access_token, shop_id):
    base_string = f"{partner_id}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()

def call_api(method, path, access_token, params=None, body=None):
    timestamp = int(time.time())
    sign = generate_sign(PARTNER_ID, path, timestamp, PARTNER_KEY, access_token, SHOP_ID)
    
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
        return r.json()
    except Exception as e:
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
    if 'ad_balance' not in st.session_state:
        st.session_state.ad_balance = None
    if 'api_status' not in st.session_state:
        st.session_state.api_status = {}

    # Actions
    st.sidebar.header("⚙️ Actions")
    
    if st.sidebar.button("🚀 Load Live Data"):
        tokens = load_tokens()
        
        if not tokens:
            st.error("❌ Tokens not found")
        else:
            with st.spinner("Connecting to Shopee API..."):
                # Get shop info
                shop_result = call_api("GET", "/api/v2/shop/get_shop_info", tokens['access_token'])
                if 'shop_name' in shop_result:
                    st.session_state.shop_data = shop_result
                    st.session_state.api_status['shop'] = '✅'
                else:
                    st.session_state.api_status['shop'] = f"❌ {shop_result.get('error', 'Unknown')}"
                
                # Get ad balance
                ad_result = call_api("GET", "/api/v2/ads/get_total_balance", tokens['access_token'])
                if 'total_balance' in ad_result:
                    st.session_state.ad_balance = ad_result.get('total_balance', 0)
                    st.session_state.api_status['ads'] = '✅'
                else:
                    st.session_state.ad_balance = 0
                    st.session_state.api_status['ads'] = f"⚠️ {ad_result.get('error', 'No data')}"
                
                st.rerun()

    # Display data
    if st.session_state.shop_data:
        shop = st.session_state.shop_data
        st.success(f"✅ **{shop.get('shop_name', 'Unknown')}** | {shop.get('status', 'N/A')} | {shop.get('region', 'N/A')}")
    else:
        st.info("👆 Click **'🚀 Load Live Data'** to connect to your shop")

    st.divider()

    # Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📦 Products")
        st.metric("Status", "⚠️ Pending")
        st.caption("Product API: Permission required")
        st.info("""
        **Note:** Product API access pending. 
        
        Your Go Live approval may still be processing for product endpoints. 
        Contact Shopee Open Platform support if this persists.
        """)
    
    with col2:
        st.subheader("💰 Ad Balance")
        if st.session_state.ad_balance is not None:
            st.metric("Credit", f"Rp {st.session_state.ad_balance:,.0f}")
        else:
            st.metric("Credit", "-")
            st.caption("Click Load Live Data")
    
    with col3:
        st.subheader("🔗 Connection")
        st.metric("Status", "🚀 PRODUCTION")
        st.caption(f"Shop ID: {SHOP_ID}")
        if st.session_state.api_status:
            st.write("API Status:")
            for api, status in st.session_state.api_status.items():
                st.caption(f"{api}: {status}")

elif app_mode == "📢 Ads Manager":
    st.title("📢 Ads Manager")
    st.info("Campaign management features coming soon!")

st.divider()
st.caption("PPMJ Platform | Payung Murah Jakarta | Production Mode")
