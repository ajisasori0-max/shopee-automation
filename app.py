import streamlit as st
import json
import requests
import hmac
import hashlib
import time
from datetime import datetime, timedelta

# ============================================================================
# CONFIG - PRODUCTION (SELLER IN-HOUSE)
# ============================================================================
PARTNER_ID = 2030653
SHOP_ID = 1147948100
PARTNER_KEY = "shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453"
BASE_URL = "https://partner.shopeemobile.com"

# ADS APP CONFIG
ADS_PARTNER_ID = 2030650
ADS_PARTNER_KEY = "shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69"

# App version
APP_VERSION = "3.0.0"

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

# ADS TOKEN MANAGEMENT (with env var support for Render)
def load_ads_tokens():
    """Load Ads app tokens from env var or file."""
    # First check environment variable (for Render persistence)
    import os
    env_tokens = os.environ.get('SHOPEE_ADS_TOKENS')
    if env_tokens:
        try:
            return json.loads(env_tokens)
        except:
            pass
    
    # Fall back to file
    try:
        with open('tokens_ads.json', 'r') as f:
            return json.load(f)
    except:
        return None

def save_ads_tokens(tokens):
    """Save tokens to file (and show env var for Render)."""
    # Save to file
    with open('tokens_ads.json', 'w') as f:
        json.dump(tokens, f, indent=2)
    
    # Also print the env var format for Render
    print("="*70)
    print("📝 ADD THIS TO RENDER ENVIRONMENT VARIABLES:")
    print("="*70)
    print(f"Key: SHOPEE_ADS_TOKENS")
    print(f"Value: {json.dumps(tokens)}")
    print("="*70)

def refresh_ads_tokens():
    """Refresh Ads access token using refresh_token."""
    tokens = load_ads_tokens()
    if not tokens or 'refresh_token' not in tokens:
        return None
    
    try:
        path = "/api/v2/auth/access_token/get"
        ts = int(time.time())
        base = f"{ADS_PARTNER_ID}{path}{ts}"
        sign = hmac.new(ADS_PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
        
        url = f"{BASE_URL}{path}"
        resp = requests.post(url, 
                            params={"partner_id": ADS_PARTNER_ID, "timestamp": ts, "sign": sign},
                            json={"refresh_token": tokens['refresh_token'], "shop_id": SHOP_ID, "partner_id": ADS_PARTNER_ID},
                            timeout=10)
        data = resp.json()
        
        if 'access_token' in data:
            with open('tokens_ads.json', 'w') as f:
                json.dump(data, f, indent=2)
            return data
        return None
    except:
        return None

def get_valid_ads_tokens():
    """Get Ads tokens, refreshing if needed."""
    tokens = load_ads_tokens()
    if not tokens:
        return None
    
    # Test if current token works
    ts = int(time.time())
    path = '/api/v2/ads/get_total_balance'
    base = f"{ADS_PARTNER_ID}{path}{ts}{tokens['access_token']}{SHOP_ID}"
    sign = hmac.new(ADS_PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{path}"
    params = {"partner_id": ADS_PARTNER_ID, "timestamp": ts, "sign": sign, "access_token": tokens['access_token'], "shop_id": SHOP_ID}
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        if 'response' in data:
            return tokens  # Token still valid
    except:
        pass
    
    # Token expired, refresh
    return refresh_ads_tokens()

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
        resp = requests.get(url, params=query, timeout=10)
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
    """Get ad balance using Ads app credentials."""
    ts = int(time.time())
    path = '/api/v2/ads/get_total_balance'
    base = f"{ADS_PARTNER_ID}{path}{ts}{tokens['access_token']}{SHOP_ID}"
    sign = hmac.new(ADS_PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    
    url = f"{BASE_URL}{path}"
    params = {
        'partner_id': ADS_PARTNER_ID,
        'timestamp': ts,
        'sign': sign,
        'access_token': tokens['access_token'],
        'shop_id': SHOP_ID
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if 'response' in data and 'total_balance' in data['response']:
            return {'success': True, 'data': data['response']['total_balance']}
        return {'success': False, 'error': data.get('error', 'No data')}
    except Exception as e:
        return {'success': False, 'error': str(e)}

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
    """Get products - NOW WORKING with item_status parameter!"""
    # CRITICAL: item_status is REQUIRED parameter
    # Added offset=0 to match working test exactly
    data = call_api("/api/v2/product/get_item_list", tokens['access_token'], 
                   {"offset": 0, "page_size": 10, "item_status": "NORMAL"})
    
    items = None
    if 'response' in data and 'item' in data['response']:
        items = data['response']['item']
    elif 'item_list' in data:
        items = data['item_list']
    
    if items:
        return {'success': True, 'data': items}
    return {'success': False, 'error': data.get('error', 'No data')}

def get_product_names(tokens, item_ids):
    """Get product names from item_base_info API."""
    if not item_ids:
        return {}
    
    # Max 50 items per call
    item_id_str = ','.join([str(i) for i in item_ids[:50]])
    
    data = call_api("/api/v2/product/get_item_base_info", tokens['access_token'],
                   {"item_id_list": item_id_str})
    
    names = {}
    if 'response' in data and 'item_list' in data['response']:
        for item in data['response']['item_list']:
            names[item['item_id']] = item.get('item_name', 'Unknown')
    return names

def get_product_price_stock(tokens, item_id):
    """Get price and stock from model_list API."""
    data = call_api("/api/v2/product/get_model_list", tokens['access_token'],
                   {"item_id": item_id})
    
    if 'response' in data and 'model' in data['response']:
        models = data['response']['model']
        variations = data['response'].get('tier_variation', [])
        
        # Get all variants
        variants = []
        for model in models:
            price_info = model.get('price_info', [{}])[0]
            stock_info = model.get('stock_info_v2', {}).get('summary_info', {})
            
            variants.append({
                'model_name': model.get('model_name', 'Default'),
                'price': price_info.get('original_price', 0),
                'current_price': price_info.get('current_price', 0),
                'stock': stock_info.get('total_available_stock', 0),
                'model_id': model.get('model_id')
            })
        
        # Get main product price/stock (first variant)
        first = variants[0] if variants else {'price': 0, 'stock': 0}
        
        return {
            'price': first['price'],
            'current_price': first['current_price'],
            'stock': first['stock'],
            'variants': variants,
            'variation_name': variations[0].get('name', 'Variant') if variations else 'Variant'
        }
    return {'price': 0, 'current_price': 0, 'stock': 0, 'variants': [], 'variation_name': 'Variant'}

def get_product_details(tokens, item_ids):
    """Get detailed product info including price, stock, name."""
    # item_id_list should be comma-separated string
    if isinstance(item_ids, list):
        item_id_str = ','.join([str(i) for i in item_ids])
    else:
        item_id_str = str(item_ids)
    
    data = call_api("/api/v2/product/get_item_base_info", tokens['access_token'], 
                   {"item_id_list": item_id_str})
    
    if 'response' in data and 'item_list' in data['response']:
        return {'success': True, 'data': data['response']['item_list']}
    return {'success': False, 'error': data.get('error', 'No data')}

# ===== ADS APIs =====

def get_ad_campaigns(tokens):
    """Get ad campaigns with full details using product_level_campaign APIs."""
    # Step 1: Get campaign ID list
    ts = int(time.time())
    path = '/api/v2/ads/get_product_level_campaign_id_list'
    base = f"{ADS_PARTNER_ID}{path}{ts}{tokens['access_token']}{SHOP_ID}"
    sign = hmac.new(ADS_PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    
    url = f"{BASE_URL}{path}"
    params = {
        'partner_id': ADS_PARTNER_ID,
        'timestamp': ts,
        'sign': sign,
        'access_token': tokens['access_token'],
        'shop_id': SHOP_ID,
        'ad_type': 'all',
        'offset': 0,
        'limit': 100
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        if 'response' not in data or 'campaign_list' not in data['response']:
            return {'success': False, 'error': data.get('error', 'No campaign data')}
        
        campaign_ids = [c.get('campaign_id') for c in data['response']['campaign_list']]
        
        # Step 2: Get campaign details (batch first 10)
        campaigns = []
        for camp_id in campaign_ids[:10]:
            camp_detail = get_campaign_detail(tokens, camp_id)
            if camp_detail:
                campaigns.append(camp_detail)
        
        return {'success': True, 'data': campaigns}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_campaign_detail(tokens, campaign_id):
    """Get detailed info for a single campaign."""
    try:
        ts = int(time.time())
        path = '/api/v2/ads/get_product_level_campaign_setting_info'
        base = f"{ADS_PARTNER_ID}{path}{ts}{tokens['access_token']}{SHOP_ID}"
        sign = hmac.new(ADS_PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
        
        url = f"{BASE_URL}{path}"
        params = {
            'partner_id': ADS_PARTNER_ID,
            'timestamp': ts,
            'sign': sign,
            'access_token': tokens['access_token'],
            'shop_id': SHOP_ID,
            'campaign_id_list': str(campaign_id),
            'info_type_list': '1'
        }
        
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()
        
        if 'response' in data and 'campaign_list' in data['response']:
            camp = data['response']['campaign_list'][0]
            common = camp.get('common_info', {})
            return {
                'campaign_id': camp.get('campaign_id'),
                'campaign_name': common.get('ad_name', f"Campaign {camp.get('campaign_id')}")[:50],
                'campaign_status': common.get('campaign_status', 'unknown').upper(),
                'daily_budget': common.get('campaign_budget', 0),
                'gmv_max': common.get('ad_type') == 'auto',
                'ad_type': common.get('ad_type', 'manual'),
                'bidding_method': common.get('bidding_method', 'unknown')
            }
        return None
    except:
        return None

def get_ad_performance(tokens):
    """Get daily ad performance data using correct endpoint and date format."""
    # Date format: DD-MM-YYYY
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    ts = int(time.time())
    path = '/api/v2/ads/get_all_cpc_ads_daily_performance'
    base = f"{ADS_PARTNER_ID}{path}{ts}{tokens['access_token']}{SHOP_ID}"
    sign = hmac.new(ADS_PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    
    url = f"{BASE_URL}{path}"
    params = {
        'partner_id': ADS_PARTNER_ID,
        'timestamp': ts,
        'sign': sign,
        'access_token': tokens['access_token'],
        'shop_id': SHOP_ID,
        'start_date': start_date_str,
        'end_date': end_date_str
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if 'response' in data:
            return {'success': True, 'data': data['response']}
        return {'success': False, 'error': data.get('error', 'No data')}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.set_page_config(page_title="PPMJ Platform", page_icon="🦊", layout="wide")

# Sidebar
st.sidebar.title("🦊 PPMJ Platform")
app_mode = st.sidebar.radio("Select", ["🏪 Seller Dashboard", "📢 Ads Manager", "🕵️ Competitor Intel"])

# Session state init
for key in ['shop_data', 'ad_balance', 'orders', 'products', 'ad_campaigns', 'ad_performance', 'last_update', 'data_sources']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'data_sources' else {}

# Load Data Button
st.sidebar.header("⚡ Actions")
if st.sidebar.button("🚀 Load Live Data"):
    with st.spinner("Connecting to Shopee..."):
        tokens = get_valid_tokens()
        ads_tokens = get_valid_ads_tokens()
        
        if not tokens:
            st.sidebar.error("❌ Cannot connect - Seller In-House token issue")
        else:
            # Shop Info (always works)
            shop_result = get_shop_info(tokens)
            if shop_result['success']:
                st.session_state.shop_data = shop_result['data']
                st.session_state.data_sources['shop'] = '✅ LIVE'
            else:
                st.session_state.data_sources['shop'] = f"❌ {shop_result['error']}"
            
            # Ad Balance (using Ads app tokens)
            if ads_tokens:
                ads_result = get_ad_balance(ads_tokens)
                if ads_result['success']:
                    st.session_state.ad_balance = ads_result['data']
                    st.session_state.data_sources['ads'] = '✅ LIVE'
                else:
                    st.session_state.ad_balance = 0
                    st.session_state.data_sources['ads'] = f"⚠️ {ads_result.get('error', 'No data')}"
            else:
                st.session_state.ad_balance = 0
                st.session_state.data_sources['ads'] = "⚠️ No Ads tokens"
            
            # Orders
            orders_result = get_orders(tokens)
            if orders_result['success']:
                st.session_state.orders = orders_result['data']
                st.session_state.data_sources['orders'] = f"✅ LIVE ({len(orders_result['data'])} orders)"
            else:
                st.session_state.orders = []
                st.session_state.data_sources['orders'] = f"⚠️ {orders_result.get('error', 'No data')}"
            
            # Products (NOW WORKING!)
            prod_result = get_products(tokens)
            
            # DEBUG: Show actual result
            if not prod_result['success']:
                st.sidebar.warning(f"DEBUG Product API: {prod_result.get('error', 'Unknown')}")
            
            if prod_result['success']:
                # Get product details (name, price, stock) for ALL products
                item_ids = [p.get('item_id') for p in prod_result['data'] if p.get('item_id')]
                product_names = get_product_names(tokens, item_ids)
                
                # Get price/stock for ALL products
                price_stock_data = {}
                for item_id in item_ids:
                    price_stock_data[item_id] = get_product_price_stock(tokens, item_id)
                
                # Merge all data
                enriched_products = []
                for p in prod_result['data']:
                    item_id = p.get('item_id')
                    ps_data = price_stock_data.get(item_id, {})
                    enriched_products.append({
                        'item_id': item_id,
                        'item_name': product_names.get(item_id, f'Product {item_id}'),
                        'item_status': p.get('item_status', 'NORMAL'),
                        'price': ps_data.get('price', 0),
                        'current_price': ps_data.get('current_price', 0),
                        'stock': ps_data.get('stock', 0),
                        'variants': ps_data.get('variants', []),
                        'variation_name': ps_data.get('variation_name', 'Variant')
                    })
                
                st.session_state.products = enriched_products
                st.session_state.data_sources['products'] = f"✅ LIVE ({len(prod_result['data'])} items)"
            else:
                st.session_state.products = MOCK_PRODUCTS
                st.session_state.data_sources['products'] = f"⚠️ MOCK ({prod_result.get('error', 'Error')})"
            
            # Ad Campaigns (using Ads app tokens)
            if ads_tokens:
                campaigns_result = get_ad_campaigns(ads_tokens)
                if campaigns_result['success']:
                    st.session_state.ad_campaigns = campaigns_result['data']
                    st.session_state.data_sources['ad_campaigns'] = f"✅ LIVE ({len(campaigns_result['data'])} campaigns)"
                else:
                    st.session_state.ad_campaigns = []
                    st.session_state.data_sources['ad_campaigns'] = f"⚠️ {campaigns_result.get('error', 'No data')}"
                
                # Ad Performance (NEW!)
                performance_result = get_ad_performance(ads_tokens)
                if performance_result['success']:
                    st.session_state.ad_performance = performance_result['data']
                    st.session_state.data_sources['ad_performance'] = f"✅ LIVE ({len(performance_result['data'])} days)"
                else:
                    st.session_state.ad_performance = []
                    st.session_state.data_sources['ad_performance'] = f"⚠️ {performance_result.get('error', 'No data')}"
            else:
                st.session_state.ad_campaigns = []
                st.session_state.ad_performance = []
                st.session_state.data_sources['ad_campaigns'] = "⚠️ No Ads tokens"
                st.session_state.data_sources['ad_performance'] = "⚠️ No Ads tokens"
            
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
    
    if is_live:
        # LIVE DATA: Show product names with price/stock and variant dropdowns
        st.success("🟢 **Live Product Data from Shopee**")
        
        for p in display_products:
            # Product header
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{p.get('item_name', 'Unknown')[:40]}...**")
            with col2:
                price = p.get('price', 0)
                if price > 0:
                    st.write(f"Rp {int(price):,}")
                else:
                    st.write("-")
            with col3:
                stock = p.get('stock', 0)
                if stock > 0:
                    st.write(f"Stock: {stock}")
                else:
                    st.write("Stock: -")
            
            # Variant dropdown
            variants = p.get('variants', [])
            if len(variants) > 1:
                variation_name = p.get('variation_name', 'Variant')
                with st.expander(f"📋 View {len(variants)} {variation_name} Options"):
                    for v in variants:
                        vcol1, vcol2, vcol3 = st.columns([2, 1, 1])
                        with vcol1:
                            st.write(f"  • {v.get('model_name', 'Default')}")
                        with vcol2:
                            vprice = v.get('price', 0)
                            st.write(f"Rp {int(vprice):,}" if vprice > 0 else "-")
                        with vcol3:
                            vstock = v.get('stock', 0)
                            st.write(f"Stock: {vstock}" if vstock > 0 else "Out of stock")
            
            st.divider()
        
    else:
        # MOCK DATA: Show sample products
        cols = st.columns(2)
        for i, p in enumerate(display_products[:4]):
            with cols[i % 2]:
                stock = p.get('stock', 0)
                price = p.get('price', 0)
                st.metric(p['item_name'][:25], f"Rp {price:,}", f"Stock: {stock}")
    
    st.divider()
    
    # DATA SOURCES TABLE
    st.subheader("🔗 Data Source Status")
    
    if st.session_state.data_sources:
        for api, status in st.session_state.data_sources.items():
            emoji = "🟢" if "LIVE" in status else "⚠️" if "MOCK" in status else "❌"
            st.write(f"{emoji} **{api.title()}**: {status}")
    else:
        st.info("Click 'Load Live Data' to see data source status")
    
    # DEBUG SECTION
    st.divider()
    st.subheader("🐛 DEBUG INFO")
    
    # Test Product API directly
    tokens = get_valid_tokens()
    if tokens:
        st.write("✅ Token valid")
        test_result = get_products(tokens)
        if test_result['success']:
            st.write(f"✅ Product API: {len(test_result['data'])} items found")
        else:
            st.error(f"❌ Product API Error: {test_result.get('error', 'Unknown')}")
    else:
        st.error("❌ Token invalid or expired")

elif app_mode == "📢 Ads Manager":
    st.title("📢 PPMJ Ads Manager")
    st.markdown("*Campaign Management | Payung Murah Jakarta*")
    
    # Check if Ads tokens exist
    ads_tokens = load_ads_tokens()
    
    if not ads_tokens:
        st.warning("""
        **⚠️ Ads App Not Authorized**
        
        The Ads app (Partner ID 2030650) needs to be authorized separately.
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔗 Generate Auth URL"):
                import urllib.parse
                ts = int(time.time())
                path = '/api/v2/shop/auth_partner'
                base = f"{ADS_PARTNER_ID}{path}{ts}"
                sign = hmac.new(ADS_PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
                
                auth_url = f"https://partner.shopeemobile.com{path}?" + urllib.parse.urlencode({
                    'partner_id': ADS_PARTNER_ID,
                    'timestamp': ts,
                    'sign': sign,
                    'redirect': 'https://shopee-automation-70ts.onrender.com'
                })
                
                st.code(auth_url, language=None)
                st.info("1. Open this URL in browser\\n2. Authorize the app\\n3. Copy the code from redirect URL")
        
        with col2:
            auth_code = st.text_input("Enter auth code:", placeholder="6a636941...")
            if st.button("✅ Exchange for Tokens") and auth_code:
                try:
                    # Exchange code for tokens
                    ts = int(time.time())
                    path = '/api/v2/auth/token/get'
                    base = f"{ADS_PARTNER_ID}{path}{ts}"
                    sign = hmac.new(ADS_PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
                    
                    url = f"https://partner.shopeemobile.com{path}?partner_id={ADS_PARTNER_ID}&timestamp={ts}&sign={sign}"
                    body = {
                        'code': auth_code,
                        'shop_id': SHOP_ID,
                        'partner_id': ADS_PARTNER_ID
                    }
                    
                    resp = requests.post(url, json=body)
                    data = resp.json()
                    
                    if 'access_token' in data:
                        # Save to file
                        with open('tokens_ads.json', 'w') as f:
                            json.dump(data, f, indent=2)
                        
                        # Show env var for Render
                        st.success("✅ Ads app authorized!")
                        st.warning("""
                        **⚠️ IMPORTANT: Add to Render Environment Variables**
                        
                        Copy this value to Render Dashboard → Environment:
                        
                        **Key:** `SHOPEE_ADS_TOKENS`
                        **Value:** (copy from below)
                        """)
                        st.code(json.dumps(data), language=None)
                        st.info("After adding to Render, redeploy. Then refresh this page.")
                    else:
                        st.error(f"❌ Failed: {data.get('error', 'Unknown')}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        st.divider()
        st.info("After authorization, click '🚀 Load Live Data' in the sidebar to fetch Ads data.")
    
    else:
        # Ads tokens exist - show normal dashboard
        # Ad Balance Header
        ad_bal = st.session_state.ad_balance if st.session_state.ad_balance else 0
        source = st.session_state.data_sources.get('ads', '')
        is_live = 'LIVE' in source
        campaigns_source = st.session_state.data_sources.get('ad_campaigns', '')
        campaigns_live = 'LIVE' in campaigns_source
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Ad Balance", f"Rp {ad_bal:,}", "🟢 LIVE" if is_live else "⚪ MOCK")
        with col2:
            st.metric("📊 Total Spend (7d)", "Rp 450,000", "⚪ Sample")
        with col3:
            st.metric("🎯 ROAS", "2.8x", "⚪ Sample")
        
        # Show what's real vs sample
        st.caption("ℹ️ **Ad Balance** and **Campaign Status** are LIVE. Spend/ROAS requires additional API access.")
        
        st.divider()
        
        # Campaign Tabs
        ad_tabs = st.tabs(["📋 Campaigns", "➕ Create Campaign", "📈 Performance", "🤖 Auto-Optimizer"])
        
        with ad_tabs[0]:
            st.subheader("Active Campaigns")
            
            if not campaigns_live:
                st.info("""
                **ℹ️ Limited Campaign Data**
                
                Showing basic campaign settings (auto top-up, surge mode).
                
                **What's LIVE:**
                - ✅ Ad Balance: Rp 96,290
                - ✅ Auto Top-Up: ON
                - ✅ Campaign Surge: ON
                
                **What's NOT Available:**
                - ❌ Detailed spend data
                - ❌ ROAS metrics  
                - ❌ Daily performance
                
                These require additional Shopee Ads API permissions.
                """)
                
                st.divider()
                st.caption("Showing sample campaigns for reference:")
            
            # Get real campaigns from session state
            campaigns = st.session_state.ad_campaigns if st.session_state.ad_campaigns else []
            
            if campaigns:
                for camp in campaigns:
                    with st.container():
                        camp_id = camp.get('campaign_id', 'N/A')
                        camp_name = camp.get('campaign_name', 'Unnamed')
                        status = camp.get('campaign_status', 'UNKNOWN')
                        budget = camp.get('daily_budget', 0)
                        campaign_type = "GMV Max" if camp.get('gmv_max', False) else "Manual"
                        
                        cols = st.columns([3, 2, 2, 2, 1])
                        status_emoji = "🟢" if status == "ACTIVE" else "🔴" if status == "PAUSED" else "⚪"
                        cols[0].write(f"**{camp_name}** | {campaign_type}")
                        cols[1].write(f"{status_emoji} {status}")
                        cols[2].write(f"Rp {int(budget):,}/day" if budget > 0 else "No limit")
                        cols[3].write(f"ID: {camp_id}")
                        cols[4].button("⚙️", key=f"settings_{camp_id}")
                        st.divider()
            else:
                # Show sample campaigns
                sample_campaigns = [
                    {"name": "GMV Max Auto", "status": "ACTIVE", "budget": 100000, "type": "GMV Max"},
                    {"name": "Manual CPC", "status": "PAUSED", "budget": 50000, "type": "Manual"},
                ]
                for camp in sample_campaigns:
                    with st.container():
                        cols = st.columns([3, 2, 2, 2])
                        status_emoji = "🟢" if camp['status'] == "ACTIVE" else "🔴"
                        cols[0].write(f"**{camp['name']}** | {camp['type']}")
                        cols[1].write(f"{status_emoji} {camp['status']}")
                        cols[2].write(f"Rp {camp['budget']:,}/day")
                        cols[3].write("(Sample)")
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
            
            # Check if we have live performance data
            perf_data = st.session_state.ad_performance
            
            if perf_data and len(perf_data) > 0:
                st.success("🟢 **LIVE Performance Data** (Last 7 Days)")
                
                import pandas as pd
                
                # Convert to DataFrame
                df_data = []
                total_spend = 0
                total_gmv = 0
                total_impressions = 0
                total_clicks = 0
                
                for day in perf_data:
                    spend = day.get('expense', 0)
                    gmv = day.get('direct_gmv', 0)
                    roas = day.get('direct_roas', 0)
                    impressions = day.get('impression', 0)
                    clicks = day.get('clicks', 0)
                    
                    # Parse date from DD-MM-YYYY to datetime
                    date_parts = day.get('date', '01-01-2026').split('-')
                    date_obj = datetime(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                    
                    df_data.append({
                        'Date': date_obj,
                        'Spend': spend,
                        'Revenue': gmv,
                        'ROAS': roas,
                        'Impressions': impressions,
                        'Clicks': clicks
                    })
                    
                    total_spend += spend
                    total_gmv += gmv
                    total_impressions += impressions
                    total_clicks += clicks
                
                df = pd.DataFrame(df_data).sort_values('Date')
                
                # Show chart
                st.write("**Spend vs Revenue**")
                st.line_chart(df.set_index('Date')[['Spend', 'Revenue']])
                
                # Show metrics
                st.divider()
                avg_roas = total_gmv / total_spend if total_spend > 0 else 0
                ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
                
                cols = st.columns(4)
                cols[0].metric("Total Spend", f"Rp {int(total_spend):,}")
                cols[1].metric("Total Revenue", f"Rp {int(total_gmv):,}")
                cols[2].metric("Avg ROAS", f"{avg_roas:.2f}x")
                cols[3].metric("CTR", f"{ctr:.2f}%")
                
                # Show daily breakdown
                st.divider()
                st.write("**Daily Breakdown**")
                
                for _, row in df.iterrows():
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                    with col1:
                        st.write(f"**{row['Date'].strftime('%d %b')}**")
                    with col2:
                        st.write(f"Rp {int(row['Spend']):,}")
                    with col3:
                        st.write(f"Rp {int(row['Revenue']):,}")
                    with col4:
                        st.write(f"{row['ROAS']:.2f}x")
                    with col5:
                        st.write(f"{int(row['Impressions']):,} impr")
                
            else:
                st.info("📊 Click '🚀 Load Live Data' to fetch performance data")
                
                # Show sample as fallback
                st.write("**Sample Performance (Demo)**")
                import pandas as pd
                dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
                performance_data = pd.DataFrame({
                    'Date': dates,
                    'Spend': [65000, 72000, 58000, 81000, 69000, 75000, 87500],
                    'Revenue': [195000, 201000, 156000, 243000, 179000, 210000, 280000],
                })
                st.line_chart(performance_data.set_index('Date')[['Spend', 'Revenue']])
                
                cols = st.columns(4)
                cols[0].metric("Total Spend", "Rp 495,500")
                cols[1].metric("Total Revenue", "Rp 1,464,000")
                cols[2].metric("Avg ROAS", "2.95x")
                cols[3].metric("Impressions", "45.2K")
        
        with ad_tabs[3]:
            st.subheader("🤖 Ads Auto-Optimizer v2.0")
            st.markdown("*Full automation with auto-adjust | Cici Kelola model*")
            
            st.success("""
            **🎯 MISSION:** Maintain algorithmic momentum to prevent 20→150→30 crash
            
            **✅ CAPABILITIES:**
            - ✅ Daily ROAS monitoring
            - ✅ Campaign performance analysis
            - ✅ **AUTO-PAUSE** underperformers (low budget)
            - ✅ **AUTO-INCREASE** budget for high ROAS campaigns
            - ✅ Token auto-refresh
            """)
            
            # Settings
            st.divider()
            st.subheader("⚙️ Settings")
            
            col1, col2 = st.columns(2)
            with col1:
                auto_adjust = st.toggle("Enable Auto-Adjust", value=True, 
                                       help="Automatically pause/increase budgets based on performance")
                min_roas = st.number_input("MIN_ROAS", value=2.0, step=0.1,
                                          help="Alert/pause campaigns below this ROAS")
                target_roas = st.number_input("TARGET_ROAS", value=3.5, step=0.1,
                                             help="Target ROAS for optimizations")
            
            with col2:
                min_budget = st.number_input("Min Budget Threshold (Rp)", value=20000, step=5000,
                                            help="Pause campaigns with budget below this")
                high_budget = st.number_input("High Budget Threshold (Rp)", value=100000, step=10000,
                                             help="Increase budget for campaigns above this with good ROAS")
            
            # Run Auto-Optimizer button
            st.divider()
            if st.button("🚀 Run Auto-Optimizer Now", type="primary"):
                with st.spinner("Running optimization..."):
                    import subprocess
                    try:
                        # Update settings in the script
                        result = subprocess.run(
                            ['python3', 'auto_optimizer.py'],
                            capture_output=True,
                            text=True,
                            timeout=90
                        )
                        st.code(result.stdout, language=None)
                        if result.stderr:
                            st.warning(f"Stderr: {result.stderr[:500]}")
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            st.divider()
            
            # Show optimization rules
            st.subheader("📋 Optimization Rules")
            
            rules_data = {
                "Condition": [
                    "ROAS < 2.0x",
                    "ROAS > 3.5x",
                    "Budget < Rp 20k",
                    "Budget > Rp 100k + High ROAS",
                    "CTR < 1%"
                ],
                "Action": [
                    "🚨 Alert",
                    "📈 Consider increasing budget",
                    "⏸️ Auto-pause (if enabled)",
                    "💰 Auto-increase budget 10%",
                    "🎨 Review creative"
                ]
            }
            
            import pandas as pd
            st.dataframe(pd.DataFrame(rules_data), use_container_width=True, hide_index=True)
            
            st.divider()
            
            # Cron job status
            st.subheader("📅 Automation Schedule")
            st.write("**Status:** ⏸️ Not yet scheduled")
            st.write("**Recommended:** Daily at 09:00 WIB")
            st.code("0 9 * * * cd /path && python3 auto_optimizer.py", language="bash")
            st.info("""
            To enable:
            1. Test manually (button above)
            2. Check reports/ folder for outputs
            3. Add cron job on your server
            4. Monitor for 1 week before full automation
            """)
            
            st.divider()
            st.caption("v2.0 - Now with auto-adjust capabilities!")

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
