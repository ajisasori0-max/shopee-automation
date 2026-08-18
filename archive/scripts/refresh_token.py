import json, hmac, hashlib, time, requests

with open('tokens_ads.json') as f:
    tokens = json.load(f)

partner_id = 2030650
partner_key = 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69'
shop_id = 1147948100
refresh_token = tokens['refresh_token']

path = '/api/v2/auth/access_token/get'
ts = int(time.time())
base = f'{partner_id}{path}{ts}'
sign = hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()

resp = requests.post(f'https://partner.shopeemobile.com{path}', json={
    'partner_id': partner_id,
    'refresh_token': refresh_token,
    'shop_id': shop_id
}, params={'partner_id': partner_id, 'timestamp': ts, 'sign': sign}, timeout=15)

print('Status:', resp.status_code)
print('Response:', resp.text[:500])

data = resp.json()
if 'access_token' in data:
    tokens['access_token'] = data['access_token']
    tokens['refresh_token'] = data.get('refresh_token', refresh_token)
    with open('tokens_ads.json', 'w') as f:
        json.dump(tokens, f, indent=2)
    print('Token refreshed and saved')
else:
    print('Refresh failed')
