import json, hmac, hashlib, time, requests
from datetime import datetime, timedelta

with open('/Users/gerard/.openclaw/workspace/shopee-api-onboarding/tokens_ads.json') as f:
    tokens = json.load(f)

partner_id = 2030650
partner_key = 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69'
shop_id = 1147948100
refresh_token = tokens['refresh_token']

path = '/api/v2/auth/access_token/get'
ts = int(time.time())
base = f'{partner_id}{path}{ts}'
sign = hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()

resp = requests.post(f'https://partner.shopeemobile.com{path}', params={
    'partner_id': partner_id, 'timestamp': ts, 'sign': sign,
}, json={
    'shop_id': shop_id,
    'partner_id': partner_id,
    'refresh_token': refresh_token
}, timeout=15)

print('Refresh Status:', resp.status_code)
print('Refresh Response:', json.dumps(resp.json(), indent=2))
