# Shopee Ads Auto-Optimizer v2.0
# Full automation with auto-adjust capabilities

import requests
import hmac
import hashlib
import time
import json
import os
from datetime import datetime, timedelta

# Config
PARTNER_ID = 2030650
PARTNER_KEY = 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69'
SHOP_ID = 1147948100
BASE_URL = "https://partner.shopeemobile.com"

# Thresholds - PHASE 1: Foundation (Week 1-2)
MIN_ROAS = 4.0  # Starting minimum (scale to 10-12x in Phase 3)
TARGET_ROAS = 5.0  # Starting target (was 3.5, scale to 12x gradually)
ROAS_ADJUST_STEP = 0.2
MIN_SPEND = 50000
AUTO_ADJUST_ENABLED = True

# 12x ROAS Strategy
MAX_DAILY_BUDGET = 500000
LEARNING_PHASE_DAYS = 7

print('='*70)
print('🤖 SHOPEE ADS AUTO-OPTIMIZER v2.0')
print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('='*70)

# Load tokens
def load_tokens():
    try:
        with open('tokens_ads.json', 'r') as f:
            return json.load(f)
    except:
        return None

def refresh_tokens():
    """Refresh access token."""
    tokens = load_tokens()
    if not tokens:
        return None
    
    try:
        ts = int(time.time())
        path = "/api/v2/auth/access_token/get"
        base = f"{PARTNER_ID}{path}{ts}"
        sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
        
        url = f"{BASE_URL}{path}"
        resp = requests.post(url, 
                            params={"partner_id": PARTNER_ID, "timestamp": ts, "sign": sign},
                            json={"refresh_token": tokens['refresh_token'], "shop_id": SHOP_ID, "partner_id": PARTNER_ID},
                            timeout=10)
        data = resp.json()
        
        if 'access_token' in data:
            with open('tokens_ads.json', 'w') as f:
                json.dump(data, f, indent=2)
            return data
        return None
    except:
        return None

# Get valid tokens
tokens = load_tokens()
if not tokens:
    print('❌ Error: Cannot load tokens')
    exit(1)

access_token = tokens['access_token']

def make_request(path, params=None, method='GET', body=None):
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
    
    if method == 'POST':
        resp = requests.post(url, params=default_params, json=body, timeout=10)
    else:
        resp = requests.get(url, params=default_params, timeout=10)
    
    return resp.json()

def adjust_campaign_budget(campaign_id, new_budget, action='change_budget'):
    """Auto-adjust campaign budget."""
    try:
        ts = int(time.time())
        path = '/api/v2/ads/edit_manual_product_ads'
        base = f"{PARTNER_ID}{path}{ts}{access_token}{SHOP_ID}"
        sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
        
        url = f"{BASE_URL}{path}?partner_id={PARTNER_ID}&timestamp={ts}&sign={sign}&shop_id={SHOP_ID}&access_token={access_token}"
        
        body = {
            'campaign_id': campaign_id,
            'reference_id': f'auto_{action}_{int(time.time())}',
            'edit_action': action,
            'budget': new_budget
        }
        
        resp = requests.post(url, json=body, timeout=10)
        data = resp.json()
        
        if 'response' in data:
            return {'success': True, 'campaign_id': campaign_id}
        return {'success': False, 'error': data.get('error', 'Unknown')}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def pause_campaign(campaign_id):
    """Pause underperforming campaign."""
    try:
        ts = int(time.time())
        path = '/api/v2/ads/edit_manual_product_ads'
        base = f"{PARTNER_ID}{path}{ts}{access_token}{SHOP_ID}"
        sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
        
        url = f"{BASE_URL}{path}?partner_id={PARTNER_ID}&timestamp={ts}&sign={sign}&shop_id={SHOP_ID}&access_token={access_token}"
        
        body = {
            'campaign_id': campaign_id,
            'reference_id': f'auto_pause_{int(time.time())}',
            'edit_action': 'pause'
        }
        
        resp = requests.post(url, json=body, timeout=10)
        data = resp.json()
        
        if 'response' in data:
            return {'success': True, 'campaign_id': campaign_id}
        return {'success': False, 'error': data.get('error', 'Unknown')}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Step 1: Get all campaigns
print('\n📊 STEP 1: Fetching campaigns...')
campaigns_data = make_request('/api/v2/ads/get_product_level_campaign_id_list', {
    'ad_type': 'all', 'offset': 0, 'limit': 100
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

perf_data = make_request('/api/v2/ads/get_all_cpc_ads_daily_performance', {
    'start_date': start_date_str, 'end_date': end_date_str
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

# Step 3: Get individual campaign details and performance
print('\n🔍 STEP 3: Analyzing individual campaigns...')
campaign_details = []

for camp in campaigns[:10]:  # Top 10
    camp_id = camp.get('campaign_id')
    
    # Get campaign details
    detail_data = make_request('/api/v2/ads/get_product_level_campaign_setting_info', {
        'campaign_id_list': str(camp_id), 'info_type_list': '1'
    })
    
    if 'response' in detail_data and 'campaign_list' in detail_data['response']:
        camp_detail = detail_data['response']['campaign_list'][0]
        common = camp_detail.get('common_info', {})
        
        campaign_details.append({
            'id': camp_id,
            'name': common.get('ad_name', 'Unnamed')[:40],
            'status': common.get('campaign_status', 'unknown'),
            'budget': common.get('campaign_budget', 0),
            'ad_type': common.get('ad_type', 'manual')
        })

# Step 4: Generate recommendations and auto-adjust
print('\n🎯 STEP 4: Generating recommendations and auto-adjusting...')
actions_taken = []
recommendations = []

# Shop-level recommendations
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

# Campaign-level actions
for camp in campaign_details:
    # Pause low-budget campaigns (underperforming)
    if camp['budget'] < 20000 and camp['status'] == 'ongoing':
        if AUTO_ADJUST_ENABLED:
            print(f"   ⏸️ Pausing campaign {camp['id']} (budget too low: Rp {camp['budget']:,})")
            result = pause_campaign(camp['id'])
            if result['success']:
                actions_taken.append(f"Paused campaign {camp['id']}")
            else:
                recommendations.append({
                    'action': 'MANUAL_PAUSE',
                    'message': f"⏸️ Consider pausing campaign {camp['id']} (low budget)",
                    'priority': 'MEDIUM'
                })
        else:
            recommendations.append({
                'action': 'PAUSE',
                'message': f"⏸️ Campaign {camp['id']} has low budget (Rp {camp['budget']:,})",
                'priority': 'MEDIUM'
            })
    
    # Increase budget for high-performers (example logic)
    elif camp['budget'] >= 100000 and camp['status'] == 'ongoing' and shop_roas > TARGET_ROAS:
        new_budget = int(camp['budget'] * 1.1)  # Increase 10%
        if AUTO_ADJUST_ENABLED:
            print(f"   💰 Increasing budget for {camp['id']} from Rp {camp['budget']:,} to Rp {new_budget:,}")
            result = adjust_campaign_budget(camp['id'], new_budget)
            if result['success']:
                actions_taken.append(f"Increased budget for campaign {camp['id']} to Rp {new_budget:,}")
            else:
                recommendations.append({
                    'action': 'MANUAL_BUDGET',
                    'message': f"💰 Consider increasing budget for {camp['id']} (high ROAS)",
                    'priority': 'LOW'
                })

# Print recommendations
print('\n📋 RECOMMENDATIONS:')
for rec in recommendations:
    print(f"   [{rec['priority']}] {rec['message']}")

if actions_taken:
    print('\n✅ ACTIONS TAKEN:')
    for action in actions_taken:
        print(f"   - {action}")

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
    'recommendations': recommendations,
    'actions_taken': actions_taken,
    'auto_adjust_enabled': AUTO_ADJUST_ENABLED
}

os.makedirs('reports', exist_ok=True)
report_file = f"reports/ads_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_file, 'w') as f:
    json.dump(report, f, indent=2)

print(f'✅ Report saved: {report_file}')

print('\n' + '='*70)
if AUTO_ADJUST_ENABLED:
    print('✅ Auto-optimization complete with AUTO-ADJUST enabled!')
else:
    print('✅ Analysis complete (recommendations only mode)')
print('='*70)

if recommendations:
    print('\n📝 NEXT ACTIONS:')
    for rec in recommendations:
        print(f"   - {rec['message']}")
else:
    print('\n🎉 No immediate actions needed. Performance is stable.')
