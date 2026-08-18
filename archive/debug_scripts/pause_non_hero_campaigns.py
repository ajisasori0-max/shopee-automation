import sys
sys.path.insert(0, '/Users/gerard/.openclaw/workspace/shopee-api-onboarding')

import os, json, time
from full_automation import make_request, ADS_PARTNER_ID, ADS_PARTNER_KEY

os.chdir('/Users/gerard/.openclaw/workspace/shopee-api-onboarding')

# Pause non-hero campaigns
pause_campaigns = [
    447589870,  # PAYUNG LIPAT METALIK
    452409640,  # PAYUNG LIPAT MOTIF 3D
    452411592,  # PAYUNG LIPAT METALIK 2
]

results = []

for cid in pause_campaigns:
    body = {
        'campaign_id': cid,
        'reference_id': f'pause_{int(time.time())}_{cid}',
        'edit_action': 'pause'
    }
    r = make_request('/api/v2/ads/edit_manual_product_ads', {}, 'POST', body=body,
                     token_file='tokens_ads.json', partner_id=ADS_PARTNER_ID, partner_key=ADS_PARTNER_KEY)
    results.append({
        'campaign_id': cid,
        'action': 'pause',
        'response': r
    })
    print(f"{cid}: {r.get('error', 'OK')}")
    time.sleep(0.5)

with open('pause_campaigns_results.json', 'w') as f:
    json.dump(results, f, indent=2)
