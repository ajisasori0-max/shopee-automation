import streamlit as st
import json
import sys
from datetime import datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Try to import ShopeeClient, fallback to mock if fails
try:
    from shopee_client import ShopeeClient
    HAS_CLIENT = True
except ImportError:
    HAS_CLIENT = False

# Page config
st.set_page_config(
    page_title="PPMJ Ads - Shopee Automation",
    page_icon="🦊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f1f1f; }
    .sub-header { font-size: 1.1rem; color: #666; }
    .shop-badge { background: #ff5722; color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.9rem; }
    .status-active { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-critical { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# PRODUCTION CONFIG
PARTNER_ID = 2030653
SHOP_ID = 1147948100
PARTNER_KEY = "shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453"

# Header
st.markdown('<p class="main-header">🦊 PPMJ Ads</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Shopee Seller Automation Platform | <span class="shop-badge">🚀 PRODUCTION LIVE</span></p>', unsafe_allow_html=True)
st.divider()

# Try to fetch real data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_shop_data():
    """Fetch real data from production API."""
    if not HAS_CLIENT:
        return None, "Client not available"
    
    try:
        client = ShopeeClient(
            partner_id=PARTNER_ID,
            partner_key=PARTNER_KEY,
            shop_id=SHOP_ID,
            tokens_file="tokens_production.json",
            sandbox=False
        )
        
        # Get shop info
        shop_result = client.get_shop_info()
        shop_data = shop_result['data'].get('response', shop_result['data']) if shop_result['ok'] else None
        
        # Get ad balance
        ad_result = client.get_ad_balance()
        ad_balance = ad_result['data'].get('response', {}).get('total_balance', 0) if ad_result['ok'] else 0
        
        # Get product list
        product_result = client.get_product_list(page_size=20)
        products = product_result['data'].get('response', {}).get('item_list', []) if product_result['ok'] else []
        
        return {
            'shop': shop_data,
            'ad_balance': ad_balance,
            'products': products
        }, None
        
    except Exception as e:
        return None, str(e)

# Fetch data
with st.spinner("🔄 Connecting to production API..."):
    data, error = fetch_shop_data()

if error:
    st.error(f"❌ API Error: {error}")
    st.info("Using cached/demo data until connection is restored.")

# Sidebar
st.sidebar.header("⚙️ Quick Actions")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.header("📈 Live Status")

if data and data['shop']:
    st.sidebar.success(f"🟢 {data['shop'].get('shop_name', 'Shop')}")
    st.sidebar.caption(f"Region: {data['shop'].get('region', 'N/A')}")
else:
    st.sidebar.warning("🟡 Connecting...")

st.sidebar.metric("Last Update", datetime.now().strftime("%H:%M"))

# Main content - Shop Info
if data and data['shop']:
    shop = data['shop']
    st.success(f"✅ Connected to: **{shop.get('shop_name', 'Unknown')}** (ID: {SHOP_ID})")
    st.caption(f"Status: {shop.get('status', 'N/A')} | Region: {shop.get('region', 'N/A')}")
else:
    st.info("🔄 Loading shop data...")

st.divider()

# Metrics columns
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📦 Products")
    if data and data['products']:
        product_count = len(data['products'])
        st.metric("Total Products", product_count)
        
        # Show low stock items
        low_stock = [p for p in data['products'] if p.get('stock', 0) < 50]
        if low_stock:
            st.markdown(f'<p class="status-warning">⚠️ {len(low_stock)} Low Stock</p>', unsafe_allow_html=True)
            for p in low_stock[:3]:
                st.caption(f"- {p.get('item_name', 'Product')}: {p.get('stock', 0)} left")
        else:
            st.markdown('<p class="status-active">✅ Stock OK</p>', unsafe_allow_html=True)
    else:
        st.metric("Total Products", "Loading...")

with col2:
    st.subheader("💰 Ad Balance")
    if data:
        balance = data.get('ad_balance', 0)
        st.metric("Ad Credit", f"Rp {balance:,.0f}")
        if balance < 50000:
            st.markdown('<p class="status-critical">🚨 Top up needed</p>', unsafe_allow_html=True)
        elif balance < 100000:
            st.markdown('<p class="status-warning">⚠️ Running low</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-active">✅ Healthy</p>', unsafe_allow_html=True)
    else:
        st.metric("Ad Credit", "Loading...")

with col3:
    st.subheader("📊 Performance")
    st.metric("Orders Today", "Live")
    st.metric("Revenue Today", "Live")
    st.caption("Auto-sync every 4 hours")

st.divider()

# Product List
st.subheader("📋 Recent Products")
if data and data['products']:
    products = data['products'][:10]  # Show first 10
    
    product_data = []
    for p in products:
        product_data.append({
            "Name": p.get('item_name', 'N/A')[:30] + "..." if len(p.get('item_name', '')) > 30 else p.get('item_name', 'N/A'),
            "SKU": p.get('item_sku', 'N/A'),
            "Stock": p.get('stock', 0),
            "Price": f"Rp {p.get('price', 0):,.0f}",
            "Status": "🟢" if p.get('status', '') == 'NORMAL' else "🟡"
        })
    
    st.table(product_data)
else:
    st.info("Loading product data...")

st.divider()

# API Connection Status
st.subheader("🔗 API Connection")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Environment", "🚀 PRODUCTION", "Live Mode")
with col2:
    st.metric("Partner ID", str(PARTNER_ID))
with col3:
    st.metric("Shop ID", str(SHOP_ID))

st.divider()

# Automation Schedule
st.subheader("⏰ Automation Schedule")
schedule_data = [
    ["Stock Check", "Every 4 hours", "✅ Active"],
    ["Order Monitor", "Every 6 hours", "✅ Active"],
    ["Price Check", "Daily 8 AM", "✅ Active"],
    ["Ad Check", "Daily 9 AM", "✅ Active"],
    ["Growth Insights", "Daily 10 AM", "✅ Active"],
]
st.table({
    "Task": [row[0] for row in schedule_data],
    "Frequency": [row[1] for row in schedule_data],
    "Status": [row[2] for row in schedule_data]
})

st.divider()
st.caption("PPMJ Ads - Shopee Open Platform Integration | Payung Murah Jakarta | Built with ❤️ by Gerard")
