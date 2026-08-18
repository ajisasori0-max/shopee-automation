import requests, hmac, hashlib, time, json
from pathlib import Path

WORKSPACE = Path('/Users/gerard/.openclaw/workspace/shopee-api-onboarding')
PARTNER_ID_ADS = 2030650
PARTNER_KEY_ADS = 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69'
SHOP_ID = 1147948100
BASE_URL = 'https://partner.shopeemobile.com'

with open(WORKSPACE / 'tokens_ads.json') as f:
    data = json.load(f)
    refresh_token = data['refresh_token']

path = '/api/v2/auth/access_token/get'
ts = int(time.time())
base = f'{PARTNER_ID_ADS}{path}{ts}'
sign = hmac.new(PARTNER_KEY_ADS.encode(), base.encode(), hashlib.sha256).hexdigest()
resp = requests.post(f'{BASE_URL}{path}',
    params={'partner_id': PARTNER_ID_ADS, 'timestamp': ts, 'sign': sign},
    json={'refresh_token': refresh_token, 'shop_id': SHOP_ID, 'partner_id': PARTNER_ID_ADS},
    timeout=15)
print('Status:', resp.status_code)
print('Response:', resp.text[:2000])

if resp.status_code == 200:
    new_data = resp.json()
    if 'access_token' in new_data:
        with open(WORKSPACE / 'tokens_ads.json', 'w') as f:
            json.dump(new_data, f, indent=2)
        print('Token refreshed successfully!')
    else:
        print('No access_token in response')
else:
    print('Failed to refresh token')
