import streamlit as st
import json
import requests
import hmac
import hashlib
import time
from datetime import datetime

# PRODUCTION CONFIG
PARTNER_ID = 2030653
SHOP_ID = 1147948100
PARTNER_KEY = "shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453"
BASE_URL = "https://partner.shopeemobile.com"

st.set_page_config(page_title="PPMJ Platform", page_icon="🦊", layout="wide")

def load_tokens():
    try:
        with open('tokens_production.json', 'r') as f:
            return json.load(f)
    except:
        return None

def call_api(method, path, access_token, params=None):
    ts = int(time.time())
    base = f"{PARTNER_ID}{path}{ts}{access_token}{SHOP_ID}"
    sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{path}"
    q = {"partner_id": PARTNER_ID, "timestamp": ts, "sign": sign, "access_token": access_token, "shop_id": SHOP_ID}
    if params: q.update(params)
    try:
        r = requests.get(url, params=q, headers={"Content-Type": "application/json"}, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

st.sidebar.title("🦊 PPMJ Platform")
app_mode = st.sidebar.radio("Select", ["🏪 Seller Dashboard", "📢 Ads Manager"])

if app_mode == "🏪 Seller Dashboard":
    st.title("🦊 PPMJ Ads")
    st.markdown("*Payung Murah Jakarta | 🚀 PRODUCTION*")
    st.divider()

    # Session state
    for key in ['shop_data', 'ad_balance', 'last_update', 'api_status']:
        if key not in st.session_state:
            st.session_state[key] = None if key != 'api_status' else {}

    # Load Data Button
    st.sidebar.header("⚡ Actions")
    if st.sidebar.button("🚀 Load Live Data"):
        tokens = load_tokens()
        if tokens:
            with st.spinner("Loading..."):
                # Shop Info - WORKS
                shop = call_api("GET", "/api/v2/shop/get_shop_info", tokens['access_token'])
                if 'shop_name' in shop:
                    st.session_state.shop_data = shop
                    st.session_state.api_status['shop_info'] = '✅'
                else:
                    st.session_state.api_status['shop_info'] = f"❌ {shop.get('error', 'Failed')}"
                
                # Ad Balance - WORKS  
                ads = call_api("GET", "/api/v2/ads/get_total_balance", tokens['access_token'])
                if 'total_balance' in ads:
                    st.session_state.ad_balance = ads['total_balance']
                    st.session_state.api_status['ad_balance'] = '✅'
                else:
                    st.session_state.ad_balance = 0
                    st.session_state.api_status['ad_balance'] = f"⚠️ {ads.get('error', 'No data')}"
                
                st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
                st.rerun()
        else:
            st.sidebar.error("Tokens not found")

    # Display Shop Info
    if st.session_state.shop_data:
        shop = st.session_state.shop_data
        cols = st.columns(4)
        cols[0].metric("Shop", shop.get('shop_name', '-'))
        cols[1].metric("Status", shop.get('status', '-'))
        cols[2].metric("Region", shop.get('region', '-'))
        cols[3].metric("Last Update", st.session_state.last_update or '-')
    else:
        st.info("👆 Click **'🚀 Load Live Data'** to connect")

    st.divider()

    # WORKING FEATURES
    st.subheader("✅ Active Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.success("**Shop Connection**")
        st.write("- Shop name, status, region")
        st.write("- Basic shop metrics")
        if st.session_state.api_status.get('shop_info'):
            st.caption(f"Status: {st.session_state.api_status['shop_info']}")
    
    with col2:
        st.success("**Ad Balance**")
        if st.session_state.ad_balance is not None:
            st.metric("Current Balance", f"Rp {st.session_state.ad_balance:,}")
        else:
            st.metric("Current Balance", "-")
        st.caption("Real-time ad credit")

    st.divider()

    # PENDING PERMISSIONS
    st.subheader("⏳ Pending API Permissions")
    
    st.warning("""
    **The following features require additional Shopee API permissions:**
    
    | Feature | Status | Note |
    |---------|--------|------|
    | 📦 Products | ⏳ Pending | `product.error_unknown` - needs approval |
    | 📋 Orders | ⏳ Pending | `error_param` - buyer data masked |
    | 🔄 Returns | ⏳ Pending | `error_data` - buyer data masked |
    | 💰 Wallet | ⏳ Pending | `error_not_found` - needs approval |
    """)
    
    st.info("""
    **Next Steps:**
    1. Contact Shopee Open Platform support
    2. Request Product API + Order API access
    3. Reference: Partner ID 2030653, Shop ID 1147948100
    """)

    st.divider()
    
    # Debug section
    with st.expander("🔧 API Debug Status"):
        if st.session_state.api_status:
            for api, status in st.session_state.api_status.items():
                st.write(f"{api}: {status}")
        else:
            st.write("No API calls made yet")

elif app_mode == "📢 Ads Manager":
    st.title("📢 Ads Manager")
    st.info("Campaign management coming soon!")
    st.write("Current ad balance will be shown here once Product API is approved.")

st.divider()
st.caption("PPMJ Platform | Payung Murah Jakarta | Production Mode")
