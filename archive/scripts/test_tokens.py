import sys
sys.path.insert(0, '/Users/gerard/.openclaw/workspace/shopee-api-onboarding')

from full_automation import make_request, get_token, SELLER_PARTNER_ID, SELLER_PARTNER_KEY
import os, json

os.chdir('/Users/gerard/.openclaw/workspace/shopee-api-onboarding')

print('=== SELLER TOKEN TEST ===')
tok, refresh = get_token('tokens_production.json', SELLER_PARTNER_ID, SELLER_PARTNER_KEY)
print('token present:', bool(tok), 'len:', len(tok) if tok else 0)

# Test shop info endpoint
r = make_request('/api/v2/shop/get_shop_info', {}, 'GET', token_file='tokens_production.json', partner_id=SELLER_PARTNER_ID, partner_key=SELLER_PARTNER_KEY)
print('shop info:', r)

print('\n=== ADS TOKEN TEST ===')
tok2, refresh2 = get_token('tokens_ads.json', 2030650, 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69')
print('token present:', bool(tok2), 'len:', len(tok2) if tok2 else 0)

# Test ad balance endpoint
r2 = make_request('/api/v2/ads/get_ad_balance', {}, 'GET', token_file='tokens_ads.json', partner_id=2030650, partner_key='shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69')
print('ad balance:', r2)
