import streamlit as st
import json
import requests
import hmac
import hashlib
import time
from datetime import datetime, timedelta

# ============================================================================
# CONFIG - PRODUCTION
# ============================================================================
PARTNER_ID = 2030653
SHOP_ID = 1147948100
PARTNER_KEY = "shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453"
BASE_URL = "https://partner.shopeemobile.com"

# App version
APP_VERSION = "1.2.0"

# ============================================================================
# MOCK DATA (Fallback when APIs fail)
# ============================================================================
MOCK_PRODUCTS = [
    {"item_name": "Payung Lipat Premium Red", "item_sku": "PAY-RED-001", "stock": 45, "price": 125000},
    {"item_name": "Payung Lipat Premium Blue", "item_sku": "PAY-BLU-002", "stock": 32, "price": 125000},
    {"item_name": "Payung Golf Besar Hitam", "item_sku": "PAY-GOLF-BLK", "stock": 18, "price": 185000},
    {"item_name": "Payung Anak Karakter", "item_sku": "PAY-KID-001", "stock": 8, "price": 85000},
    {"item_name": "Payung Anti UV Silver", "item_sku": "PAY-UV-SLV", "stock": 67, "price": 145000},
]

# ============================================================================
# TOKEN MANAGEMENT (Auto-refresh)
# ============================================================================
def load_tokens():
    """Load tokens from file."""
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
        ts = int(time.time())
        base = f"{PARTNER_ID}{path}{ts}"
        sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
        
        url = f"{BASE_URL}{path}"
        resp = requests.post(url, 
                            params={"partner_id": PARTNER_ID, "timestamp": ts, "sign": sign},
                            json={"refresh_token": tokens['refresh_token'], "shop_id": SHOP_ID, "partner_id": PARTNER_ID},
                            timeout=10)
        data = resp.json()
        
        if 'access_token' in data:
            with open('tokens_production.json', 'w') as f:
                json.dump(data, f, indent=2)
            return data
        return None
    except:
        return None

def get_valid_tokens():
    """Get tokens, refreshing if needed."""
    tokens = load_tokens()
    if not tokens:
        return None
    
    # Test if current token works
    ts = int(time.time())
    base = f"{PARTNER_ID}/api/v2/shop/get_shop_info{ts}{tokens['access_token']}{SHOP_ID}"
    sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}/api/v2/shop/get_shop_info"
    params = {"partner_id": PARTNER_ID, "timestamp": ts, "sign": sign, "access_token": tokens['access_token'], "shop_id": SHOP_ID}
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if 'shop_name' in data:
            return tokens  # Token still valid
    except:
        pass
    
    # Token expired, refresh
    return refresh_tokens()

# ============================================================================
# API CALLS (With error handling)
# ============================================================================
def call_api(path, access_token, params=None):
    """Make API call with proper signature."""
    ts = int(time.time())
    base = f"{PARTNER_ID}{path}{ts}{access_token}{SHOP_ID}"
    sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    
    url = f"{BASE_URL}{path}"
    query = {"partner_id": PARTNER_ID, "timestamp": ts, "sign": sign, "access_token": access_token, "shop_id": SHOP_ID}
    if params:
        query.update(params)
    
    try:
        resp = requests.get(url, params=query, headers={"Content-Type": "application/json"}, timeout=10)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def get_shop_info(tokens):
    """Get shop info - ALWAYS WORKS."""
    data = call_api("/api/v2/shop/get_shop_info", tokens['access_token'])
    if 'shop_name' in data:
        return {'success': True, 'data': data}
    return {'success': False, 'error': data.get('error', 'Unknown')}

def get_ad_balance(tokens):
    """Get ad balance - WORKS (in response.total_balance)."""
    data = call_api("/api/v2/ads/get_total_balance", tokens['access_token'])
    # Ad balance is in response.total_balance
    if 'response' in data and 'total_balance' in data['response']:
        return {'success': True, 'data': data['response']['total_balance']}
    return {'success': False, 'error': data.get('error', 'No data'), 'raw': data}

def get_orders(tokens):
    """Get orders - WORKS with time_range_field."""
    time_from = int((datetime.now() - timedelta(days=7)).timestamp())
    time_to = int(datetime.now().timestamp())
    
    data = call_api("/api/v2/order/get_order_list", tokens['access_token'], {
        "page_size": 50,
        "time_range_field": "create_time",
        "time_from": time_from,
        "time_to": time_to
    })
    
    if 'response' in data and 'order_list' in data['response']:
        return {'success': True, 'data': data['response']['order_list']}
    return {'success': False, 'error': data.get('error', data.get('message', 'No data'))}

def get_products(tokens):
    """Get products - BLOCKED BY SHOPEE (permission issue)."""
    data = call_api("/api/v2/product/get_item_list", tokens['access_token'], {"page_size": 50})
    
    items = None
    if 'item_list' in data:
        items = data['item_list']
    elif 'response' in data and 'item_list' in data['response']:
        items = data['response']['item_list']
    
    if items:
        return {'success': True, 'data': items}
    return {'success': False, 'error': data.get('error', 'No data'), 'blocked': data.get('error') == 'product.error_unknown'}

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="PPMJ Platform", page_icon="🦊", layout="wide")

# Sidebar
st.sidebar.title("🦊 PPMJ Platform")
app_mode = st.sidebar.radio("Select", ["🏪 Seller Dashboard", "📢 Ads Manager", "🕵️ Competitor Intel"])

# Session state init
for key in ['shop_data', 'ad_balance', 'orders', 'products', 'last_update', 'data_sources']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'data_sources' else {}

# Load Data Button
st.sidebar.header("⚡ Actions")
if st.sidebar.button("🚀 Load Live Data"):
    with st.spinner("Connecting to Shopee..."):
        tokens = get_valid_tokens()
        
        if not tokens:
            st.sidebar.error("❌ Cannot connect - token issue")
        else:
            # Shop Info (always works)
            shop_result = get_shop_info(tokens)
            if shop_result['success']:
                st.session_state.shop_data = shop_result['data']
                st.session_state.data_sources['shop'] = '✅ LIVE'
            else:
                st.session_state.data_sources['shop'] = f"❌ {shop_result['error']}"
            
            # Ad Balance
            ads_result = get_ad_balance(tokens)
            if ads_result['success']:
                st.session_state.ad_balance = ads_result['data']
                st.session_state.data_sources['ads'] = '✅ LIVE'
            else:
                st.session_state.ad_balance = 0
                st.session_state.data_sources['ads'] = f"⚠️ {ads_result.get('error', 'No data')}"
            
            # Orders
            orders_result = get_orders(tokens)
            if orders_result['success']:
                st.session_state.orders = orders_result['data']
                st.session_state.data_sources['orders'] = f"✅ LIVE ({len(orders_result['data'])} orders)"
            else:
                st.session_state.orders = []
                st.session_state.data_sources['orders'] = f"⚠️ {orders_result.get('error', 'No data')}"
            
            # Products (will fail - Shopee permission)
            prod_result = get_products(tokens)
            if prod_result['success']:
                st.session_state.products = prod_result['data']
                st.session_state.data_sources['products'] = f"✅ LIVE ({len(prod_result['data'])} items)"
            else:
                st.session_state.products = MOCK_PRODUCTS
                if prod_result.get('blocked'):
                    st.session_state.data_sources['products'] = '⚠️ MOCK (Shopee permission required)'
                else:
                    st.session_state.data_sources['products'] = f"⚠️ MOCK ({prod_result.get('error', 'Error')})"
            
            st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()

if app_mode == "🏪 Seller Dashboard":
    st.title("🦊 PPMJ Ads")
    st.markdown("*Payung Murah Jakarta | 🚀 PRODUCTION*")
    
    # Header with connection status
    if st.session_state.shop_data:
        shop = st.session_state.shop_data
        st.success(f"✅ **{shop.get('shop_name', 'Payung Murah Jakarta')}** | {shop.get('status', 'NORMAL')} | {shop.get('region', 'ID')}")
    else:
        st.info("👆 Click **'🚀 Load Live Data'** to connect to your shop")
    
    if st.session_state.last_update:
        st.caption(f"Last updated: {st.session_state.last_update}")
    
    st.divider()
    
    # METRICS
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        prod_count = len(st.session_state.products) if st.session_state.products else len(MOCK_PRODUCTS)
        source = st.session_state.data_sources.get('products', 'Click Load Data')
        is_live = 'LIVE' in source
        st.metric(f"📦 Products", prod_count, f"{'🟢 LIVE' if is_live else '⚪ MOCK'}")
    
    with col2:
        order_count = len(st.session_state.orders) if st.session_state.orders else 0
        source = st.session_state.data_sources.get('orders', 'Click Load Data')
        is_live = 'LIVE' in source
        st.metric(f"📋 Orders (7d)", order_count, f"{'🟢 LIVE' if is_live else '⚪ MOCK'}")
    
    with col3:
        revenue = sum(o.get('total_amount', 0) for o in st.session_state.orders) if st.session_state.orders else 0
        st.metric(f"💰 Revenue (7d)", f"Rp {revenue:,}", "🟢 LIVE" if st.session_state.orders else "⚪ MOCK")
    
    with col4:
        ad_bal = st.session_state.ad_balance if st.session_state.ad_balance else 0
        source = st.session_state.data_sources.get('ads', 'Click Load Data')
        is_live = 'LIVE' in source
        st.metric(f"📢 Ad Balance", f"Rp {ad_bal:,}", f"{'🟢 LIVE' if is_live else '⚪ MOCK'}")
    
    st.divider()
    
    # ORDERS SECTION
    st.subheader("📋 Recent Orders")
    if st.session_state.orders:
        for order in st.session_state.orders[:5]:
            order_sn = order.get('order_sn', 'N/A')
            create_time = order.get('create_time', 0)
            date_str = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M') if create_time else 'N/A'
            st.write(f"🟢 **{order_sn}** | {date_str}")
        st.caption(f"🟢 Showing {min(5, len(st.session_state.orders))} of {len(st.session_state.orders)} orders (LIVE DATA)")
    else:
        st.info("No orders loaded yet. Click 'Load Live Data' above.")
    
    st.divider()
    
    # PRODUCTS SECTION
    st.subheader("📦 Products")
    display_products = st.session_state.products if st.session_state.products else MOCK_PRODUCTS
    source = st.session_state.data_sources.get('products', 'MOCK')
    is_live = 'LIVE' in source
    
    cols = st.columns(2)
    for i, p in enumerate(display_products[:4]):
        with cols[i % 2]:
            stock = p.get('stock', 0)
            price = p.get('price', 0)
            st.metric(p['item_name'][:25], f"Rp {price:,}", f"Stock: {stock}")
    
    if not is_live:
        st.info("⚠️ **Product data is mock/sample** — Shopee Product API permission pending")
    
    st.divider()
    
    # DATA SOURCES TABLE
    st.subheader("🔗 Data Source Status")
    
    if st.session_state.data_sources:
        for api, status in st.session_state.data_sources.items():
            emoji = "🟢" if "LIVE" in status else "⚠️" if "MOCK" in status else "❌"
            st.write(f"{emoji} **{api.title()}**: {status}")
    else:
        st.info("Click 'Load Live Data' to see data source status")
    
    # SHOPEE SUPPORT INFO
    if st.session_state.data_sources.get('products', '').startswith('⚠️ MOCK'):
        st.divider()
        st.warning("""
        **📧 Contact Shopee for Product API Access:**
        
        Subject: "Product API Access Request - Partner ID 2030653"
        
        Partner ID: 2030653
        Shop ID: 1147948100
        Error: product.error_unknown
        Endpoint: /api/v2/product/get_item_list
        
        Shop Info and Order APIs work correctly.
        """)

elif app_mode == "📢 Ads Manager":
    st.title("📢 PPMJ Ads Manager")
    st.markdown("*Campaign Management | Payung Murah Jakarta*")
    
    # Ad Balance Header
    ad_bal = st.session_state.ad_balance if st.session_state.ad_balance else 0
    source = st.session_state.data_sources.get('ads', '')
    is_live = 'LIVE' in source
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Ad Balance", f"Rp {ad_bal:,}", "🟢 LIVE" if is_live else "⚪ MOCK")
    with col2:
        st.metric("📊 Total Spend (7d)", "Rp 450,000", "Sample")
    with col3:
        st.metric("🎯 ROAS", "2.8x", "Sample")
    
    st.divider()
    
    # Campaign Tabs
    ad_tabs = st.tabs(["📋 Campaigns", "➕ Create Campaign", "📈 Performance"])
    
    with ad_tabs[0]:
        st.subheader("Active Campaigns")
        
        campaigns = [
            {"name": "Flash Sale March", "status": "ACTIVE", "budget": 100000, "spend": 87500, "roas": 3.2, "type": "GMV Max"},
            {"name": "New Arrival Boost", "status": "PAUSED", "budget": 50000, "spend": 0, "roas": 0, "type": "Manual"},
            {"name": "Auto GMV Max", "status": "ACTIVE", "budget": 150000, "spend": 142000, "roas": 2.1, "type": "GMV Max"},
        ]
        
        for camp in campaigns:
            with st.container():
                cols = st.columns([3, 2, 2, 2, 1])
                status_emoji = "🟢" if camp['status'] == "ACTIVE" else "🔴"
                cols[0].write(f"**{camp['name']}** | {camp['type']}")
                cols[1].write(f"{status_emoji} {camp['status']}")
                cols[2].write(f"Rp {camp['budget']:,}/day")
                cols[3].write(f"ROAS: {camp['roas']}x" if camp['roas'] > 0 else "-")
                cols[4].button("⚙️", key=f"settings_{camp['name']}")
                st.progress(min(camp['spend'] / camp['budget'], 1.0), text=f"Spend: Rp {camp['spend']:,} / Rp {camp['budget']:,}")
                st.divider()
    
    with ad_tabs[1]:
        st.subheader("Create New Campaign")
        
        with st.form("create_campaign"):
            col1, col2 = st.columns(2)
            with col1:
                camp_name = st.text_input("Campaign Name", placeholder="e.g., Weekend Flash Sale")
                camp_type = st.selectbox("Campaign Type", ["GMV Max (AI Optimized)", "Manual CPC"])
                daily_budget = st.number_input("Daily Budget (Rp)", min_value=50000, value=100000, step=10000)
            with col2:
                start_date = st.date_input("Start Date", datetime.now())
                end_date = st.date_input("End Date", datetime.now() + timedelta(days=7))
                
                if camp_type == "GMV Max (AI Optimized)":
                    roas_target = st.slider("ROAS Target", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
                else:
                    bid_per_click = st.number_input("Bid Per Click (Rp)", min_value=100, value=500, step=100)
            
            st.divider()
            st.write("**Select Products to Promote:**")
            products_to_promote = st.multiselect(
                "Products",
                ["Payung Lipat Premium Red", "Payung Lipat Premium Blue", "Payung Golf Besar", "Payung Anak Karakter"],
                default=["Payung Lipat Premium Red"]
            )
            
            submitted = st.form_submit_button("🚀 Create Campaign", type="primary")
            if submitted:
                st.success(f"✅ Campaign '{camp_name}' created successfully! (Demo mode)")
                st.info("Note: In production, this would create a real campaign via Shopee Ads API.")
    
    with ad_tabs[2]:
        st.subheader("Campaign Performance")
        
        # Performance chart placeholder
        st.write("**Spend vs Revenue (Last 7 Days)**")
        
        import pandas as pd
        import numpy as np
        
        # Sample performance data
        dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
        performance_data = pd.DataFrame({
            'Date': dates,
            'Spend': [65000, 72000, 58000, 81000, 69000, 75000, 87500],
            'Revenue': [195000, 201000, 156000, 243000, 179000, 210000, 280000],
        })
        performance_data['ROAS'] = performance_data['Revenue'] / performance_data['Spend']
        
        st.line_chart(performance_data.set_index('Date')[['Spend', 'Revenue']])
        
        st.divider()
        
        cols = st.columns(4)
        cols[0].metric("Total Spend", "Rp 495,500")
        cols[1].metric("Total Revenue", "Rp 1,464,000")
        cols[2].metric("Avg ROAS", "2.95x")
        cols[3].metric("Impressions", "45.2K")
        
        st.divider()
        st.caption("📊 Performance data is sample/demo. Real data requires Shopee Ads API production access.")

elif app_mode == "🕵️ Competitor Intel":
    st.title("🕵️ Competitor Intelligence")
    st.markdown("*Weekly competitor tracking | Brother inputs data every Friday*")
    
    # Setup instructions (only show once, can be collapsed)
    with st.expander("📋 Setup Instructions (for Brother)", expanded=False):
        st.write("""
        **Weekly Task (Every Friday, 10 minutes):**
        
        1. Open competitor Shopee shops:
           - [PayungMurahJkt](https://shopee.co.id/payungmurahjkt)
           - [TokoPayungID](https://shopee.co.id/tokopayungid)
           - [JakartaPayung](https://shopee.co.id/jakartapayung)
        
        2. Check these 5 products:
           - Payung Lipat Premium
           - Payung Golf Besar
           - Payung Anak Karakter
           - Payung Anti UV
           - Payung Lipat Mini
        
        3. Copy price & stock into Google Sheet:
           [Link to Sheet]
        
        **That's it! Dashboard updates automatically.**
        """)
    
    st.divider()
    
    # Sample competitor data (until real sheet is connected)
    st.subheader("📊 This Week's Intel (Sample Data)")
    
    sample_data = {
        "week": "March 13, 2026",
        "competitors": [
            {
                "name": "PayungMurahJkt",
                "products": [
                    {"name": "Payung Lipat Premium", "price": 119000, "stock": 23, "trend": "stable"},
                    {"name": "Payung Golf Besar", "price": 179000, "stock": 0, "trend": "out_of_stock"},
                    {"name": "Payung Anak Karakter", "price": 89000, "stock": 8, "trend": "low"},
                ]
            },
            {
                "name": "JakartaPayung",
                "products": [
                    {"name": "Payung Lipat Premium", "price": 135000, "stock": 67, "trend": "discount"},
                    {"name": "Payung Anti UV", "price": 149000, "stock": 12, "trend": "stable"},
                ]
            }
        ]
    }
    
    # Display competitor comparison
    cols = st.columns(2)
    for i, comp in enumerate(sample_data["competitors"]):
        with cols[i]:
            st.markdown(f"**{comp['name']}**")
            for prod in comp["products"]:
                stock_emoji = "🔴" if prod["stock"] == 0 else "🟡" if prod["stock"] < 10 else "🟢"
                trend_emoji = {"stable": "➡️", "out_of_stock": "🚨", "low": "⚠️", "discount": "🏷️"}.get(prod["trend"], "➡️")
                st.write(f"{trend_emoji} {prod['name'][:20]}")
                st.write(f"   💰 Rp {prod['price']:,} | {stock_emoji} Stock: {prod['stock']}")
            st.divider()
    
    st.divider()
    
    # AI Analysis Section
    st.subheader("🎯 AI Analysis & Opportunities")
    
    # Opportunity alerts
    opportunities = [
        {
            "type": "stock_out",
            "priority": "HIGH",
            "title": "🔥 STOCK OUT ALERT",
            "competitor": "PayungMurahJkt",
            "product": "Payung Golf Besar",
            "action": "Raise your price from Rp185k → Rp210k",
            "impact": "+Rp25k profit per unit",
            "urgency": "Act within 24h"
        },
        {
            "type": "price_gap",
            "priority": "MEDIUM", 
            "title": "💰 PRICE GAP OPPORTUNITY",
            "competitor": "JakartaPayung",
            "product": "Payung Lipat Premium",
            "action": "Safe to raise to Rp130k (you're at Rp125k)",
            "impact": "+Rp5k per unit, still cheapest",
            "urgency": "This week"
        },
        {
            "type": "threat",
            "priority": "LOW",
            "title": "⚠️ COMPETITIVE THREAT",
            "competitor": "JakartaPayung", 
            "product": "Payung Lipat Premium",
            "action": "Monitor sales this week — they dropped price 10%",
            "impact": "Your sales may dip 5-10%",
            "urgency": "Watch only"
        }
    ]
    
    for opp in opportunities:
        priority_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[opp["priority"]]
        with st.container():
            st.markdown(f"**{priority_color} {opp['title']}**")
            st.write(f"**Competitor:** {opp['competitor']} | **Product:** {opp['product']}")
            st.info(f"**Action:** {opp['action']}")
            st.success(f"**Impact:** {opp['impact']}")
            st.caption(f"⏰ {opp['urgency']}")
            st.divider()
    
    st.divider()
    
    # Trend Analysis
    st.subheader("📈 4-Week Trends")
    
    trend_data = {
        "PayungMurahJkt": {
            "Payung Lipat Premium": [119000, 119000, 125000, 119000],
            "Payung Golf Besar": [179000, 179000, 189000, 179000],
        },
        "JakartaPayung": {
            "Payung Lipat Premium": [149000, 145000, 139000, 135000],
        }
    }
    
    for comp_name, products in trend_data.items():
        st.markdown(f"**{comp_name}**")
        for prod_name, prices in products.items():
            direction = "📉" if prices[-1] < prices[0] else "📈" if prices[-1] > prices[0] else "➡️"
            st.write(f"{direction} {prod_name}: {prices[0]/1000:.0f}k → {prices[-1]/1000:.0f}k")
        st.caption("Pattern: Testing optimal price points" if "119000" in str(prices) else "Aggressive discounting")
    
    st.divider()
    
    # Your Position Summary
    st.subheader("🏆 Your Position")
    
    metrics_cols = st.columns(3)
    metrics_cols[0].metric("Price Competitiveness", "7/10", "Mid-range")
    metrics_cols[1].metric("Stock Advantage", "9/10", "Strong")
    metrics_cols[2].metric("Opportunities This Week", "2", "Act now")
    
    st.info("""
    **💡 Strategy Recommendation:**
    
    You're well-positioned this week. Competitor #1 is out of stock on Golf umbrellas — 
    this is your chance to capture that market segment. Competitor #2 is in a price war, 
    but you have stock depth they don't. Hold your prices, focus on availability messaging.
    """)
    
    st.divider()
    
    # Google Sheets Connection Status
    st.subheader("🔗 Data Source")
    st.warning("⚠️ **Google Sheet not connected yet**")
    st.write("""
    To enable live data:
    1. Create Google Sheet with columns: Week | Competitor | Product | Price | Stock | Notes
    2. Share sheet with service account: `ppmj-platform@...`
    3. Paste Sheet ID here:
    """)
    sheet_id = st.text_input("Google Sheet ID", placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
    if st.button("Connect Sheet"):
        st.success("✅ Sheet connected! (Demo mode — real connection requires setup)")

st.divider()
st.caption("PPMJ Platform | Payung Murah Jakarta | Production Mode")
