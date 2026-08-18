import json, hmac, hashlib, time, requests

with open('/Users/gerard/.openclaw/workspace/shopee-api-onboarding/tokens_production.json') as f:
    tokens = json.load(f)

partner_id = 2030653
partner_key = 'shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453'
shop_id = 1147948100
access_token = tokens['access_token']

path = '/api/v2/product/get_item_list'
ts = int(time.time())
base = f'{partner_id}{path}{ts}{access_token}{shop_id}'
sign = hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()

resp = requests.get(f'https://partner.shopeemobile.com{path}', params={
    'partner_id': partner_id, 'timestamp': ts, 'sign': sign,
    'access_token': access_token, 'shop_id': shop_id,
    'offset': '0', 'page_size': '1', 'item_status': 'NORMAL'
}, timeout=15)

print('Status:', resp.status_code)
print('Response:', resp.text[:500])
