import sys
sys.path.insert(0, '/Users/gerard/.openclaw/workspace/shopee-api-onboarding')

import os, json, time
from full_automation import make_request, ADS_PARTNER_ID, ADS_PARTNER_KEY

os.chdir('/Users/gerard/.openclaw/workspace/shopee-api-onboarding')

campaigns = [
    (445446513, 'PAYUNG LIPAT ANTI UV', 150000),
    (447589870, 'PAYUNG LIPAT METALIK', 150000),
    (452409640, 'PAYUNG LIPAT MOTIF 3D', 112500),
    (452411592, 'PAYUNG LIPAT METALIK 2', 50000),
    (445311693, 'PAYUNG OTOMATIS 3D', 50000),
    (445335702, 'PAYUNG GOLF SILVER', 0),
]

results = []

for cid, name, _ in campaigns:
    # Try to update ROAS target via auto_bidding change
    body = {
        'campaign_id': cid,
        'reference_id': f'roas_change_{int(time.time())}_{cid}',
        'edit_action': 'change_roas_target',
        'roas_target': 4.5
    }
    r = make_request('/api/v2/ads/edit_manual_product_ads', {}, 'POST', body=body,
                     token_file='tokens_ads.json', partner_id=ADS_PARTNER_ID, partner_key=ADS_PARTNER_KEY)
    results.append({
        'campaign_id': cid,
        'name': name,
        'action': 'change_auto_bidding_roas_4.5',
        'response': r
    })
    print(f"{cid} {name}: {r.get('error', 'OK')[:50] if isinstance(r.get('error'), str) else r.get('error')}")
    time.sleep(0.5)

with open('roas_change_results.json', 'w') as f:
    json.dump(results, f, indent=2)
