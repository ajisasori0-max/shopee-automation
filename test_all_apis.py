import requests, hmac, hashlib, time, json, os
from datetime import datetime, timedelta

PARTNER_ID = 2030653
SHOP_ID = 1147948100
PARTNER_KEY = 'shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453'

print("="*70)
print("COMPLETE API DIAGNOSTIC")
print("="*70)
print()

# Step 1: Check token file exists
if not os.path.exists('tokens_production.json'):
    print("❌ CRITICAL: tokens_production.json not found")
    exit()

with open('tokens_production.json', 'r') as f:
    tokens = json.load(f)

print(f"✅ Token file found")
print(f"   Access token: {tokens['access_token'][:30]}...")
print(f"   Expires in: {tokens.get('expire_in', 'unknown')} seconds")
print()

# Step 2: Test if current token works
def test_api(path, params=None):
    ts = int(time.time())
    access_token = tokens['access_token']
    base = f'{PARTNER_ID}{path}{ts}{access_token}{SHOP_ID}'
    sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    url = f'https://partner.shopeemobile.com{path}'
    q = {'partner_id': PARTNER_ID, 'timestamp': ts, 'sign': sign, 'access_token': access_token, 'shop_id': SHOP_ID}
    if params: q.update(params)
    try:
        r = requests.get(url, params=q, timeout=10)
        return r.json()
    except Exception as e:
        return {'error': str(e)}

print("TEST 1: Shop Info (should work)")
shop = test_api('/api/v2/shop/get_shop_info')
shop_works = 'shop_name' in shop
print(f"   Result: {shop.get('shop_name', shop.get('error', 'FAIL'))}")
print(f"   Status: {'✅ WORKS' if shop_works else '❌ FAIL'}")
print()

if not shop_works and 'invalid_acceess_token' in str(shop):
    print("TOKEN EXPIRED - Refreshing...")
    
    # Refresh token
    path = '/api/v2/auth/access_token/get'
    ts = int(time.time())
    base = f'{PARTNER_ID}{path}{ts}'
    sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    resp = requests.post(f'https://partner.shopeemobile.com{path}',
                        params={'partner_id': PARTNER_ID, 'timestamp': ts, 'sign': sign},
                        json={'refresh_token': tokens['refresh_token'], 'shop_id': SHOP_ID, 'partner_id': PARTNER_ID})
    refresh_data = resp.json()
    
    if 'access_token' in refresh_data:
        with open('tokens_production.json', 'w') as f:
            json.dump(refresh_data, f, indent=2)
        tokens = refresh_data
        print(f"   ✅ Token refreshed!")
        
        # Re-test shop
        shop = test_api('/api/v2/shop/get_shop_info')
        print(f"   Shop re-test: {shop.get('shop_name', shop.get('error', 'FAIL'))}")
    else:
        print(f"   ❌ Refresh failed: {refresh_data}")
        exit()

print()
print("TEST 2: Ad Balance")
ads = test_api('/api/v2/ads/get_total_balance')
ads_works = 'total_balance' in ads
if ads_works:
    print(f"   Result: Rp {ads.get('total_balance', 0):,}")
else:
    print(f"   Result: {ads.get('error', 'NO DATA')}")
print(f"   Status: {'✅ WORKS' if ads_works else '⚠️ NO DATA'}")
print()

print("TEST 3: Orders (with time_range_field)")
time_from = int((datetime.now() - timedelta(days=7)).timestamp())
time_to = int(datetime.now().timestamp())
orders = test_api('/api/v2/order/get_order_list', {
    'page_size': 20,
    'time_range_field': 'create_time',
    'time_from': time_from,
    'time_to': time_to
})
orders_works = 'response' in orders and 'order_list' in orders['response']
if orders_works:
    print(f"   Result: {len(orders['response']['order_list'])} orders")
else:
    print(f"   Result: {orders.get('error', orders.get('message', 'FAIL'))}")
print(f"   Status: {'✅ WORKS' if orders_works else '❌ FAIL'}")
print()

print("TEST 4: Products (expected to fail - permission)")
prod = test_api('/api/v2/product/get_item_list', {'page_size': 50})
prod_works = 'item_list' in prod or ('response' in prod and 'item_list' in prod['response'])
print(f"   Result: {prod.get('error', 'NO ERROR')}")
print(f"   Status: {'✅ WORKS' if prod_works else '⛔ BLOCKED BY SHOPEE'}")
print()

print("="*70)
print("SUMMARY FOR DASHBOARD:")
print("="*70)
print(f"Shop Info:   {'✅ LIVE' if shop_works else '❌ ERROR'}")
print(f"Ad Balance:  {'✅ LIVE' if ads_works else '⚠️ MOCK'}")
print(f"Orders:      {'✅ LIVE' if orders_works else '⚠️ MOCK'}")
print(f"Products:    {'✅ LIVE' if prod_works else '⚠️ MOCK (Shopee)'}")
print("="*70)
