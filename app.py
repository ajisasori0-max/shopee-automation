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

# ========== MOCK DATA (For Full Dashboard Display) ==========
MOCK_PRODUCTS = [
    {"item_name": "Payung Lipat Premium Red", "item_sku": "PAY-RED-001", "stock": 45, "price": 125000, "status": "NORMAL"},
    {"item_name": "Payung Lipat Premium Blue", "item_sku": "PAY-BLU-002", "stock": 32, "price": 125000, "status": "NORMAL"},
    {"item_name": "Payung Golf Besar Hitam", "item_sku": "PAY-GOLF-BLK", "stock": 18, "price": 185000, "status": "NORMAL"},
    {"item_name": "Payung Anak Karakter", "item_sku": "PAY-KID-001", "stock": 8, "price": 85000, "status": "LOW_STOCK"},
    {"item_name": "Payung Anti UV Silver", "item_sku": "PAY-UV-SLV", "stock": 67, "price": 145000, "status": "NORMAL"},
    {"item_name": "Payung Magic Umbrella", "item_sku": "PAY-MAG-001", "stock": 12, "price": 195000, "status": "NORMAL"},
]

MOCK_ORDERS = [
    {"order_sn": "250311ABC123", "buyer_username": "buyer_***", "total_amount": 250000, "status": "READY_TO_SHIP", "create_time": int(time.time()) - 3600},
    {"order_sn": "250311DEF456", "buyer_username": "buyer_***", "total_amount": 125000, "status": "PROCESSED", "create_time": int(time.time()) - 7200},
    {"order_sn": "250311GHI789", "buyer_username": "buyer_***", "total_amount": 370000, "status": "SHIPPED", "create_time": int(time.time()) - 86400},
]

MOCK_ADS = [
    {"campaign_name": "Flash Sale March", "status": "ACTIVE", "daily_budget": 100000, "roas": 2.8},
    {"campaign_name": "New Arrival Boost", "status": "PAUSED", "daily_budget": 50000, "roas": 0},
    {"campaign_name": "Auto GMV Max", "status": "ACTIVE", "daily_budget": 150000, "roas": 3.2},
]

# Session state init
for key in ['live_mode', 'shop_data', 'ad_balance', 'last_update']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'live_mode' else False

st.sidebar.title("🦊 PPMJ Platform")
app_mode = st.sidebar.radio("Select", ["🏪 Seller Dashboard", "📢 Ads Manager"])

# Connection Mode Toggle
st.sidebar.divider()
st.sidebar.subheader("🔗 Connection Mode")
mode = st.sidebar.radio("", ["🚀 LIVE (Limited)", "📊 FULL (Demo Data)"], index=1 if not st.session_state.live_mode else 0)
st.session_state.live_mode = (mode == "🚀 LIVE (Limited)")

if app_mode == "🏪 Seller Dashboard":
    st.title("🦊 PPMJ Ads")
    st.markdown("*Payung Murah Jakarta | 🚀 PRODUCTION | Full Dashboard View*")
    
    # Connection status banner
    if st.session_state.live_mode:
        st.info("🚀 **LIVE MODE**: Showing real data where APIs permit. Product/Order data requires additional Shopee approval.")
    else:
        st.warning("📊 **DEMO MODE**: Showing sample data. Toggle to 'LIVE' for real shop info + ad balance.")
    
    st.divider()

    # LIVE DATA FETCH
    if st.session_state.live_mode:
        if st.sidebar.button("🔄 Refresh Live Data"):
            tokens = load_tokens()
            if tokens:
                with st.spinner("Fetching..."):
                    shop = call_api("GET", "/api/v2/shop/get_shop_info", tokens['access_token'])
                    if 'shop_name' in shop:
                        st.session_state.shop_data = shop
                    
                    ads = call_api("GET", "/api/v2/ads/get_total_balance", tokens['access_token'])
                    if 'total_balance' in ads:
                        st.session_state.ad_balance = ads['total_balance']
                    
                    st.session_state.last_update = datetime.now().strftime("%H:%M:%S")
                    st.rerun()
        
        # Show live data
        if st.session_state.shop_data:
            st.success(f"✅ **{st.session_state.shop_data.get('shop_name', 'Payung Murah Jakarta')}** | {st.session_state.shop_data.get('status', 'NORMAL')} | {st.session_state.shop_data.get('region', 'ID')}")
        if st.session_state.ad_balance is not None:
            st.metric("💰 Live Ad Balance", f"Rp {st.session_state.ad_balance:,}")
        if st.session_state.last_update:
            st.caption(f"Last live update: {st.session_state.last_update}")
    
    st.divider()

    # ========== FULL DASHBOARD (Always Shows Data) ==========
    
    # METRICS ROW
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Total Products", len(MOCK_PRODUCTS))
    with col2:
        st.metric("📋 Today's Orders", len([o for o in MOCK_ORDERS if datetime.fromtimestamp(o['create_time']).date() == datetime.now().date()]))
    with col3:
        st.metric("💰 Revenue Today", f"Rp {sum(o['total_amount'] for o in MOCK_ORDERS):,}")
    with col4:
        st.metric("📢 Active Campaigns", len([a for a in MOCK_ADS if a['status'] == 'ACTIVE']))
    
    st.divider()
    
    # PRODUCTS SECTION
    st.subheader("📦 Products & Stock")
    
    low_stock = [p for p in MOCK_PRODUCTS if p['stock'] < 20]
    if low_stock:
        st.error(f"🚨 {len(low_stock)} items low on stock!")
    else:
        st.success("✅ All stock levels healthy")
    
    prod_cols = st.columns(3)
    for i, p in enumerate(MOCK_PRODUCTS):
        with prod_cols[i % 3]:
            stock_emoji = "🔴" if p['stock'] < 10 else "🟡" if p['stock'] < 30 else "🟢"
            st.metric(p['item_name'][:20], f"{stock_emoji} {p['stock']}", f"Rp {p['price']:,}")
    
    # Stock table
    with st.expander("📋 Full Product List"):
        st.table([{
            "Product": p['item_name'],
            "SKU": p['item_sku'],
            "Stock": p['stock'],
            "Price": f"Rp {p['price']:,}",
            "Status": p['status']
        } for p in MOCK_PRODUCTS])
    
    st.divider()
    
    # ORDERS SECTION
    st.subheader("📋 Recent Orders")
    
    for order in MOCK_ORDERS[:3]:
        status_color = "🟢" if order['status'] == "SHIPPED" else "🟡" if order['status'] == "PROCESSED" else "🔵"
        st.write(f"{status_color} **{order['order_sn']}** | Rp {order['total_amount']:,} | {order['status']} | {datetime.fromtimestamp(order['create_time']).strftime('%H:%M')}")
    
    st.divider()
    
    # ADS SECTION
    st.subheader("📢 Ad Campaigns")
    
    ad_cols = st.columns(3)
    for i, ad in enumerate(MOCK_ADS):
        with ad_cols[i]:
            status_emoji = "🟢" if ad['status'] == "ACTIVE" else "🔴"
            st.metric(f"{status_emoji} {ad['campaign_name']}", f"ROAS: {ad['roas']}x" if ad['roas'] > 0 else "Paused", f"Budget: Rp {ad['daily_budget']:,}")
    
    st.divider()
    
    # AUTOMATION SCHEDULE
    st.subheader("⏰ Automation Schedule")
    schedule = [
        ["Stock Check", "Every 4 hours", "⏳ Pending API"],
        ["Order Monitor", "Every 6 hours", "⏳ Pending API"],
        ["Price Check", "Daily 8 AM", "⏳ Pending API"],
        ["Ad Check", "Daily 9 AM", "⏳ Pending API"],
    ]
    st.table({"Task": [s[0] for s in schedule], "Frequency": [s[1] for s in schedule], "Status": [s[2] for s in schedule]})
    
    st.divider()
    
    # API STATUS FOOTER
    st.subheader("🔗 API Access Status")
    
    api_status = """
    | Feature | Status | Action Required |
    |---------|--------|-----------------|
    | ✅ Shop Info | **WORKING** | None — live data available |
    | ✅ Ad Balance | **WORKING** | None — live data available |
    | ⏳ Product API | **PENDING** | Contact Shopee support |
    | ⏳ Order API | **PENDING** | Contact Shopee support |
    | ⏳ Returns API | **PENDING** | Contact Shopee support |
    | ⏳ Wallet API | **PENDING** | Contact Shopee support |
    """
    st.markdown(api_status)
    
    st.info("""
    **📧 Contact Shopee Open Platform:**
    
    Subject: "Request Product & Order API Access — Partner ID 2030653"
    
    Body:
    > Hello Shopee Team,
    > 
    > Our app (Partner ID: 2030653, Shop ID: 1147948100) is approved for production.
    > Currently receiving `product.error_unknown` and `error_param` on operational APIs.
    > 
    > Requesting access to:
    > - /api/v2/product/get_item_list
    > - /api/v2/order/get_order_list (accept masked buyer data)
    > - /api/v2/returns/get_return_list
    > 
    > Thank you.
    """)

elif app_mode == "📢 Ads Manager":
    st.title("📢 PPMJ Ads Manager")
    st.markdown("*Campaign Management | Payung Murah Jakarta*")
    st.divider()
    
    # Campaign list
    st.subheader("📊 Active Campaigns")
    for ad in MOCK_ADS:
        cols = st.columns([3, 2, 2, 2, 1])
        status_color = "🟢" if ad['status'] == "ACTIVE" else "🔴"
        cols[0].write(f"**{ad['campaign_name']}**")
        cols[1].write(f"{status_color} {ad['status']}")
        cols[2].write(f"Rp {ad['daily_budget']:,}/day")
        cols[3].write(f"ROAS: {ad['roas']}x" if ad['roas'] > 0 else "-")
        cols[4].button("Edit", key=f"edit_{ad['campaign_name']}")
    
    st.divider()
    
    # Create campaign
    st.subheader("➕ Quick Campaign")
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("Type", ["GMV Max", "Manual CPC"])
        st.number_input("Budget", value=100000, step=10000)
    with col2:
        st.text_input("Campaign Name", placeholder="e.g., Weekend Flash Sale")
        st.date_input("Start Date", datetime.now())
    st.button("🚀 Create Campaign", type="primary")

st.divider()
st.caption("PPMJ Platform | Payung Murah Jakarta | Production Mode with Demo Data")
