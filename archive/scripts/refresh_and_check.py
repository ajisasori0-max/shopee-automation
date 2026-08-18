import json, hmac, hashlib, time, requests
from datetime import datetime, timedelta

PARTNER_ID = 2030650
PARTNER_KEY = 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69'
SHOP_ID = 1147948100
BASE_URL = 'https://partner.shopeemobile.com'

# Load tokens
with open('tokens_ads.json') as f:
    tokens = json.load(f)

# Refresh access token
ts = int(time.time())
path = "/api/v2/auth/access_token/get"
base = f"{PARTNER_ID}{path}{ts}"
sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()

url = f"{BASE_URL}{path}"
resp = requests.post(url,
                    params={"partner_id": PARTNER_ID, "timestamp": ts, "sign": sign},
                    json={"refresh_token": tokens['refresh_token'], "shop_id": SHOP_ID, "partner_id": PARTNER_ID},
                    timeout=10)
data = resp.json()

if 'access_token' not in data:
    print('Token refresh failed:', data)
    exit(1)

# Save new tokens
with open('tokens_ads.json', 'w') as f:
    json.dump(data, f, indent=2)

access_token = data['access_token']

# Now fetch ads performance
ts = int(time.time())
path = '/api/v2/ads/get_all_cpc_ads_daily_performance'
base = f'{PARTNER_ID}{path}{ts}{access_token}{SHOP_ID}'
sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()

end = datetime.now()
start = end - timedelta(days=1)
resp = requests.get(f'{BASE_URL}{path}', params={
    'partner_id': PARTNER_ID, 'timestamp': ts, 'sign': sign,
    'access_token': access_token, 'shop_id': SHOP_ID,
    'start_date': start.strftime('%d-%m-%Y'),
    'end_date': end.strftime('%d-%m-%Y')
}, timeout=15)

data = resp.json()
print('API Response:', json.dumps(data, indent=2))

if 'response' in data and data['response']:
    day = data['response'][0]
    spend = day.get('expense', 0)
    gmv = day.get('direct_gmv', 0)
    roas = gmv/spend if spend > 0 else 0
    orders = day.get('direct_order', 0) or day.get('orders', 0)
    clicks = day.get('clicks', 0)
    impressions = day.get('impression', 0)
    ctr = (clicks/impressions*100) if impressions > 0 else 0
    print(f'Midday Check — {day.get("date")}')
    print(f'ROAS: {roas:.2f}x | Spend: Rp {spend:,.0f} | GMV: Rp {gmv:,.0f}')
    print(f'Orders: {orders} | CTR: {ctr:.2f}% | Clicks: {clicks}')
else:
    print('No data')
