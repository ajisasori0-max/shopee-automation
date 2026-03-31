# Shopee Ads Auto-Optimizer
# Runs daily to optimize campaigns automatically

import requests
import hmac
import hashlib
import time
import json
from datetime import datetime, timedelta

# Config
PARTNER_ID = 2030650
PARTNER_KEY = 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69'
SHOP_ID = 1147948100
BASE_URL = "https://partner.shopeemobile.com"

# Thresholds
MIN_ROAS = 2.0  # Pause campaigns below this
TARGET_ROAS = 3.5  # Adjust towards this
ROAS_ADJUST_STEP = 0.2  # Max 20% change per day
MIN_SPEND = 50000  # Minimum spend to evaluate (Rp 50k)

print('='*70)
print('🤖 SHOPEE ADS AUTO-OPTIMIZER')
print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('='*70)

# Load tokens
try:
    with open('tokens_ads.json', 'r') as f:
        tokens = json.load(f)
    access_token = tokens['access_token']
except:
    print('❌ Error: Cannot load tokens')
    exit(1)

def make_request(path, params=None):
    """Make signed request to Shopee API."""
    ts = int(time.time())
    base = f"{PARTNER_ID}{path}{ts}{access_token}{SHOP_ID}"
    sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    
    url = f"{BASE_URL}{path}"
    default_params = {
        'partner_id': PARTNER_ID,
        'timestamp': ts,
        'sign': sign,
        'access_token': access_token,
        'shop_id': SHOP_ID
    }
    if params:
        default_params.update(params)
    
    resp = requests.get(url, params=default_params, timeout=10)
    return resp.json()

# Step 1: Get all campaigns
print('\n📊 STEP 1: Fetching campaigns...')
campaigns_data = make_request('/api/v2/ads/get_product_level_campaign_id_list', {
    'ad_type': 'all',
    'offset': 0,
    'limit': 100
})

if 'response' not in campaigns_data or 'campaign_list' not in campaigns_data['response']:
    print('❌ Error: Cannot fetch campaigns')
    exit(1)

campaigns = campaigns_data['response']['campaign_list']
print(f'✅ Found {len(campaigns)} campaigns')

# Step 2: Get performance for last 7 days
print('\n📈 STEP 2: Analyzing performance...')
end_date = datetime.now()
start_date = end_date - timedelta(days=7)
start_date_str = start_date.strftime('%d-%m-%Y')
end_date_str = end_date.strftime('%d-%m-%Y')

# Get shop-level performance (all campaigns combined)
perf_data = make_request('/api/v2/ads/get_all_cpc_ads_daily_performance', {
    'start_date': start_date_str,
    'end_date': end_date_str
})

total_spend = 0
total_gmv = 0
total_impressions = 0
total_clicks = 0

if 'response' in perf_data:
    for day in perf_data['response']:
        total_spend += day.get('expense', 0)
        total_gmv += day.get('direct_gmv', 0)
        total_impressions += day.get('impression', 0)
        total_clicks += day.get('clicks', 0)

shop_roas = total_gmv / total_spend if total_spend > 0 else 0
ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

print(f'   Total Spend: Rp {total_spend:,.0f}')
print(f'   Total GMV: Rp {total_gmv:,.0f}')
print(f'   Overall ROAS: {shop_roas:.2f}x')
print(f'   Overall CTR: {ctr:.2f}%')

# Step 3: Get individual campaign performance
print('\n🔍 STEP 3: Analyzing individual campaigns...')
campaign_ids = [c.get('campaign_id') for c in campaigns[:10]]  # Top 10
campaign_id_str = ','.join([str(cid) for cid in campaign_ids])

camp_perf = make_request('/api/v2/ads/get_product_campaign_daily_performance', {
    'campaign_id_list': campaign_id_str,
    'start_date': start_date_str,
    'end_date': end_date_str
})

# Step 4: Generate recommendations
print('\n🎯 STEP 4: Generating recommendations...')
recommendations = []

if shop_roas < MIN_ROAS:
    recommendations.append({
        'action': 'ALERT',
        'message': f'⚠️ Shop ROAS ({shop_roas:.2f}x) below minimum ({MIN_ROAS}x)',
        'priority': 'HIGH'
    })

if shop_roas < TARGET_ROAS:
    recommendations.append({
        'action': 'ROAS_UP',
        'message': f'📈 Increase ROAS target toward {TARGET_ROAS}x (current: {shop_roas:.2f}x)',
        'priority': 'MEDIUM'
    })

if ctr < 1.0:
    recommendations.append({
        'action': 'CREATIVE',
        'message': f'🎨 CTR ({ctr:.2f}%) is low - consider updating product images/titles',
        'priority': 'MEDIUM'
    })

if total_spend < 100000:
    recommendations.append({
        'action': 'BUDGET',
        'message': f'💰 Low spend (Rp {total_spend:,.0f}) - consider increasing budget for more data',
        'priority': 'LOW'
    })

# Print recommendations
print('\n📋 RECOMMENDATIONS:')
for rec in recommendations:
    print(f"   [{rec['priority']}] {rec['message']}")

# Step 5: Save report
print('\n💾 STEP 5: Saving report...')
report = {
    'timestamp': datetime.now().isoformat(),
    'shop_id': SHOP_ID,
    'summary': {
        'total_spend': total_spend,
        'total_gmv': total_gmv,
        'roas': shop_roas,
        'ctr': ctr,
        'campaigns_count': len(campaigns)
    },
    'recommendations': recommendations
}

report_file = f"reports/ads_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
import os
os.makedirs('reports', exist_ok=True)
with open(report_file, 'w') as f:
    json.dump(report, f, indent=2)

print(f'✅ Report saved: {report_file}')

print('\n' + '='*70)
print('✅ Auto-optimization complete!')
print('='*70)
print('\n📝 NEXT ACTIONS:')
if recommendations:
    for rec in recommendations:
        print(f"   - {rec['message']}")
else:
    print('   - No immediate actions needed. Performance is stable.')
print('\n⚡ For full automation, implement API endpoints to:')
print('   1. Pause campaigns (not available in current API permissions)')
print('   2. Adjust ROAS targets (not available in current API permissions)')
print('   3. Update budgets (not available in current API permissions)')
print('\n🎯 CURRENTLY: Recommendations are generated, manual action required.')
