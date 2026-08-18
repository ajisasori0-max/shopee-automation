import json, hmac, hashlib, time, requests

with open('tokens_production.json') as f:
    tokens = json.load(f)

partner_id = 2030653
partner_key = 'shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453'
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
data = resp.json()
print('Has access_token:', 'access_token' in data)
print('Error:', data.get('error'))
if 'access_token' in data:
    print('Refresh successful')
    # Save via token_manager to preserve metadata (_saved_at etc.)
    from token_manager import TokenManager
    tm = TokenManager()
    tm._save_tokens('production', data)
    print('Saved to tokens_production.json via token_manager')
else:
    print('Message:', data.get('message'))
