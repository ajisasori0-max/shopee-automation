import json, hmac, hashlib, time, requests
from datetime import datetime, timedelta
from token_manager import TokenManager
from commerceos.platform.shopee_config import get_ads_credentials

# Auto-refresh tokens before use
manager = TokenManager()
access_token = manager.get_valid_token("ads")
if not access_token:
    print("❌ Failed to get valid ads token")
    exit(1)

_ads = get_ads_credentials()
partner_id = _ads["partner_id"]
partner_key = _ads["partner_key"]
shop_id = _ads["shop_id"]

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
    print('Response:', json.dumps(data, indent=2))
