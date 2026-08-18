import json, hmac, hashlib, time, requests
from datetime import datetime, timedelta

with open('tokens_ads.json') as f:
    tokens = json.load(f)

partner_id = 2030650
partner_key = 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69'
shop_id = 1147948100
access_token = tokens['access_token']

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

print('Status:', resp.status_code)
print('Response:', json.dumps(resp.json(), indent=2)[:2000])
