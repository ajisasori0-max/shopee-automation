import streamlit as st
import json
import requests
import hmac
import hashlib
import time
from datetime import datetime, timedelta

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

def generate_sign(partner_id, path, timestamp, partner_key, access_token, shop_id):
    base_string = f"{partner_id}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()

def call_api(method, path, access_token, params=None):
    ts = int(time.time())
    sign = generate_sign(PARTNER_ID, path, ts, PARTNER_KEY, access_token, SHOP_ID)
    url = f"{BASE_URL}{path}"
    q = {"partner_id": PARTNER_ID, "timestamp": ts, "sign": sign, "access_token": access_token, "shop_id": SHOP_ID}
    if params: q.update(params)
    try:
        r = requests.get(url, params=q, headers={"Content-Type": "application/json"}, timeout=10)
        return r.json()
    except:
        return {"error": "Request failed"}

# Session state
for key in ['shop_data', 'ad_balance', 'orders', 'products', 'last_update']:
    if key not in st.session_state:
        st.session_state[key] = None

st.sidebar.title("🦊 PPMJ Platform")
app_mode = st.sidebar.radio("Select", ["🏪 Seller Dashboard", "📢 Ads Manager"])

# Load Data Button
st.sidebar.header("⚡ Actions")
if st.sidebar.button("🚀 Load Live Data"):
    tokens = load_tokens()
    if tokens:
        with st.spinner("Fetching live data..."):
            # Shop Info - WORKS
            shop = call_api("GET", "/api/v2/shop/get_shop_info", tokens['access_token'])
            if 'shop_name' in shop:
                st.session_state.shop_data = shop
            
            # Ad Balance - WORKS
            ads = call_api("GET", "/api/v2/ads/get_total_balance", tokens['access_token'])
            if 'total_balance' in ads:
                st.session_state.ad_balance = ads['total_balance']
            
            # Orders - NOW WORKS with time_range_field!
            time_from = int((datetime.now() - timedelta(days=7)).timestamp())
            time_to = int(datetime.now().timestamp())
            orders = call_api("GET", "/api/v2/order/get_order_list", tokens['access_token'], {
                "page_size": 20,
                "time_range_field": "create_time",
                "time_from": time_from,
                "time_to": time_to
            })
            if 'response' in orders and 'order_list' in orders['response']:
                st.session_state.orders = orders['response']['order_list']
            
            # Products - STILL BLOCKED by Shopee
            prod = call_api("GET", "/api/v2/product/get_item_list", tokens['access_token'], {"page_size": 50})
            if 'item_list' in prod or ('response' in prod and 'item_list' in prod['response']):
                items = prod.get('item_list', prod.get('response', {}).get('item_list', []))
                st.session_state.products = items
            
            st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
            st.rerun()
    else:
        st.sidebar.error("Tokens not found")

# Mock data fallback
MOCK_PRODUCTS = [
    {"item_name": "Payung Lipat Premium Red", "item_sku": "PAY-RED-001", "stock": 45, "price": 125000},
    {"item_name": "Payung Lipat Premium Blue", "item_sku": "PAY-BLU-002", "stock": 32, "price": 125000},
    {"item_name": "Payung Golf Besar Hitam", "item_sku": "PAY-GOLF-BLK", "stock": 18, "price": 185000},
    {"item_name": "Payung Anak Karakter", "item_sku": "PAY-KID-001", "stock": 8, "price": 85000},
]

if app_mode == "🏪 Seller Dashboard":
    st.title("🦊 PPMJ Ads")
    st.markdown("*Payung Murah Jakarta | 🚀 PRODUCTION*")
    
    # Connection status
    if st.session_state.shop_data:
        st.success(f"✅ **{st.session_state.shop_data.get('shop_name', 'Payung Murah Jakarta')}** | {st.session_state.shop_data.get('status', 'NORMAL')} | {st.session_state.shop_data.get('region', 'ID')}")
    else:
        st.info("👆 Click **'🚀 Load Live Data'** to connect")
    
    if st.session_state.last_update:
        st.caption(f"Last update: {st.session_state.last_update}")
    
    st.divider()
    
    # METRICS
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        products_count = len(st.session_state.products) if st.session_state.products else len(MOCK_PRODUCTS)
        st.metric("📦 Products", products_count)
    with col2:
        orders_count = len(st.session_state.orders) if st.session_state.orders else 0
        st.metric("📋 Orders (7 days)", orders_count)
    with col3:
        revenue = sum(o.get('total_amount', 0) for o in st.session_state.orders) if st.session_state.orders else 0
        st.metric("💰 Revenue", f"Rp {revenue:,}")
    with col4:
        ad_bal = st.session_state.ad_balance if st.session_state.ad_balance else 0
        st.metric("📢 Ad Balance", f"Rp {ad_bal:,}")
    
    st.divider()
    
    # ORDERS (LIVE if available)
    st.subheader("📋 Recent Orders")
    if st.session_state.orders:
        for order in st.session_state.orders[:5]:
            st.write(f"🟢 **{order.get('order_sn', 'N/A')}** | {datetime.fromtimestamp(order.get('create_time', 0)).strftime('%Y-%m-%d %H:%M')}")
        st.caption(f"Showing {min(5, len(st.session_state.orders))} of {len(st.session_state.orders)} orders")
    else:
        st.info("No orders loaded. Click 'Load Live Data' above.")
    
    st.divider()
    
    # PRODUCTS (Mock until API works)
    st.subheader("📦 Products")
    display_products = st.session_state.products if st.session_state.products else MOCK_PRODUCTS
    
    cols = st.columns(2)
    for i, p in enumerate(display_products[:4]):
        with cols[i % 2]:
            stock = p.get('stock', p.get('seller_stock', [{}])[0].get('stock', 0))
            st.metric(p['item_name'][:25], f"Rp {p.get('price', 0):,}", f"Stock: {stock}")
    
    st.divider()
    
    # API STATUS
    st.subheader("🔗 API Status")
    status_table = """
    | Feature | Status | Data Source |
    |---------|--------|-------------|
    | ✅ Shop Info | **WORKING** | Live API |
    | ✅ Orders | **WORKING** | Live API (last 7 days) |
    | ✅ Ad Balance | **WORKING** | Live API |
    | ⏳ Products | **PENDING** | Mock data (waiting Shopee) |
    """
    st.markdown(status_table)
    
    st.info("""
    **📧 Contact Shopee for Product API:**
    
    Subject: "Product API Access Request - Partner ID 2030653"
    
    Current error: `product.error_unknown` on `/api/v2/product/get_item_list`
    
    Shop Info and Orders APIs work correctly with same credentials.
    """)

elif app_mode == "📢 Ads Manager":
    st.title("📢 Ads Manager")
    st.info("Campaign management coming soon!")

st.divider()
st.caption("PPMJ Platform | Payung Murah Jakarta | Production Mode")
