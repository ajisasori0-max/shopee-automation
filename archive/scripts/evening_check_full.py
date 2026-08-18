import json, hmac, hashlib, time, requests
from datetime import datetime, timedelta

# Load current tokens
with open('tokens_ads.json') as f:
    tokens = json.load(f)

partner_id = 2030650
partner_key = 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69'
shop_id = 1147948100

# Step 1: Refresh access token
refresh_path = '/api/v2/auth/access_token/get'
ts = int(time.time())
base = f'{partner_id}{refresh_path}{ts}'
sign = hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()

refresh_resp = requests.post(f'https://partner.shopeemobile.com{refresh_path}', params={
    'partner_id': partner_id,
    'timestamp': ts,
    'sign': sign,
}, json={
    'refresh_token': tokens['refresh_token'],
    'shop_id': shop_id,
    'partner_id': partner_id,
}, timeout=15)

refresh_data = refresh_resp.json()
if refresh_data.get('error'):
    print(f"Token refresh failed: {refresh_data.get('message')}")
    exit(1)

# Save new tokens
tokens = refresh_data
with open('tokens_ads.json', 'w') as f:
    json.dump(tokens, f, indent=2)

access_token = tokens['access_token']

# Step 2: Fetch ads performance
path = '/api/v2/ads/get_all_cpc_ads_daily_performance'
ts = int(time.time())
base = f'{partner_id}{path}{ts}{access_token}{shop_id}'
sign = hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()

end = datetime.now()
start = end - timedelta(days=1)
resp = requests.get(f'https://partner.shopeemobile.com{path}', params={
    'partner_id': partner_id, 'timestamp': ts, 'sign': sign,
    'access_token': access_token, 'shop_id': shop_id,
    'start_date': start.strftime('%d-%m-%Y'),
    'end_date': end.strftime('%d-%m-%Y')
}, timeout=15)

data = resp.json()
if 'response' in data and data['response']:
    day = data['response'][0]
    spend = day.get('expense', 0)
    gmv = day.get('direct_gmv', 0)
    roas = gmv/spend if spend > 0 else 0
    orders = day.get('direct_order', 0) or day.get('orders', 0)
    clicks = day.get('clicks', 0)
    impressions = day.get('impression', 0)
    ctr = (clicks/impressions*100) if impressions > 0 else 0
    print(f'Evening Check — {day.get("date")}')
    print(f'ROAS: {roas:.2f}x | Spend: Rp {spend:,.0f} | GMV: Rp {gmv:,.0f}')
    print(f'Orders: {orders} | CTR: {ctr:.2f}% | Clicks: {clicks}')
    if roas < 4.0:
        print('ALERT: ROAS below emergency floor!')
    elif roas < 4.5:
        print('WARNING: ROAS below floor')
    else:
        print('STATUS: ROAS healthy')
else:
    print('No data')
