# Shopee Ads Auto-Optimizer v2.0
# Full automation with auto-adjust capabilities

import requests
import hmac
import hashlib
import time
import json
import os
from datetime import datetime, timedelta

from commerceos.platform.tokens import get_access_token
from commerceos.platform.shopee_config import get_ads_credentials

_ads = get_ads_credentials()

# Config
PARTNER_ID = _ads["partner_id"]
PARTNER_KEY = _ads["partner_key"]
SHOP_ID = _ads["shop_id"]
BASE_URL = "https://partner.shopeemobile.com"

# Thresholds - REALISTIC MODE (Based on historical 3.1-3.2x ROAS)
MIN_ROAS = 2.5  # Floor — don't go below break-even
TARGET_ROAS = 3.5  # Achievable target (was 7.0, unrealistic)
CURRENT_ROAS_STEP = 0.1  # Increase 0.1x every 3-5 days (conservative)
MIN_SPEND = 100000  # Minimum daily spend
AUTO_ADJUST_ENABLED = True  # Enable auto-adjust
MAX_DAILY_BUDGET = 500000  # 500k max (was 1M, unrealistic)
AGGRESSIVE_MODE = False  # Conservative mode for stability

print('='*70)
print('🚀 SHOPEE ADS AUTO-OPTIMIZER v3.1 - STABLE MODE')
print(f'Target: 3.5x ROAS | Max Budget: Rp 500k/day | Conservative')
print('='*70)

# Get valid access token from the central token authority.
access_token = get_access_token('ads')
if not access_token:
    print('❌ Error: Cannot get valid access token')
    exit(1)

def refresh_tokens():
    """Refresh access token via central token authority."""
    global access_token
    access_token = get_access_token('ads', force_refresh=True)
    return {'access_token': access_token} if access_token else None

def make_request(path, params=None, method='GET', body=None, _retried=False):
    """Make signed request to Shopee API with auth retry."""
    global access_token
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
    
    data = resp.json()
    if not _retried and data.get('error') in ('invalid_acceess_token', 'invalid_access_token', 'error_auth'):
        print('⚠️  Auth error, refreshing token and retrying...')
        new_tokens = refresh_tokens()
        if new_tokens:
            access_token = new_tokens['access_token']
            return make_request(path, params, method, body, _retried=True)
    
    return data

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

def restructure_campaign_budget(campaign_id, target_budget):
    """Restructure campaign to target budget for 12x ROAS strategy."""
    try:
        ts = int(time.time())
        path = '/api/v2/ads/edit_manual_product_ads'
        base = f"{PARTNER_ID}{path}{ts}{access_token}{SHOP_ID}"
        sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
        
        url = f"{BASE_URL}{path}?partner_id={PARTNER_ID}&timestamp={ts}&sign={sign}&shop_id={SHOP_ID}&access_token={access_token}"
        
        body = {
            'campaign_id': campaign_id,
            'reference_id': f'restructure_{int(time.time())}',
            'edit_action': 'change_budget',
            'budget': target_budget
        }
        
        resp = requests.post(url, json=body, timeout=10)
        data = resp.json()
        
        if 'response' in data:
            return {'success': True, 'campaign_id': campaign_id, 'new_budget': target_budget}
        return {'success': False, 'error': data.get('error', 'Unknown')}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# REALISTIC MODE - Campaign Tiers (Based on actual performance)
# Historical: 3.1-3.2x ROAS at ~350-400k/day spend
CAMPAIGN_TIERS = {
    # Hero Tier: 150k/day each (300k total) — proven performers
    'hero': {
        'campaigns': [445446513, 447589870],
        'target_budget': 150000,  # 150k each (was 400k)
        'target_roas': 3.5,  # Realistic target
        'priority': 'high'
    },
    # Growth Tier: 50k/day each (100k total) — testing
    'growth': {
        'campaigns': [445311693, 452411592],
        'target_budget': 50000,  # 50k each (was 100k)
        'target_roas': 3.0,
        'priority': 'medium'
    },
    # Test Tier: Pause or minimal
    'test': {
        'campaigns': [445335702],
        'target_budget': 0,  # Pause — reallocate to heroes
        'target_roas': 2.5,
        'priority': 'low'
    }
}

print('\n🎯 STABLE MODE: Realistic Targets')
print('='*70)
print('Campaign Restructure for 400k Daily Spend:')
print('  HERO (2 campaigns): Rp 150k each = Rp 300k/day, ROAS 3.5x')
print('  GROWTH (2 campaigns): Rp 50k each = Rp 100k/day, ROAS 3.0x')
print('  TOTAL TARGET: Rp 400k/day with 3.5x ROAS')
print('='*70)
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

# Step 3: Get individual campaign details and RESTRUCTURE
print('\n🔍 STEP 3: Analyzing and restructuring campaigns...')
campaign_details = []
actions_taken = []  # FIX: Initialize before use

for tier_name, tier_config in CAMPAIGN_TIERS.items():
    print(f'\n   📋 {tier_name.upper()} TIER:')
    for camp_id in tier_config['campaigns']:
        # Get campaign details
        detail_data = make_request('/api/v2/ads/get_product_level_campaign_setting_info', {
            'campaign_id_list': str(camp_id), 'info_type_list': '1'
        })
        
        if 'response' in detail_data and 'campaign_list' in detail_data['response']:
            camp_detail = detail_data['response']['campaign_list'][0]
            common = camp_detail.get('common_info', {})
            current_budget = common.get('campaign_budget', 0)
            target_budget = tier_config['target_budget']
            
            print(f'     - ID {camp_id}: {common.get("ad_name", "Unnamed")[:35]}...')
            print(f'       Current: Rp {current_budget:,} → Target: Rp {target_budget:,}')
            
            # Auto-adjust budget if different
            if AUTO_ADJUST_ENABLED and abs(current_budget - target_budget) > 5000:
                result = restructure_campaign_budget(camp_id, target_budget)
                if result['success']:
                    actions_taken.append(f"Restructured campaign {camp_id} to Rp {target_budget:,}")
                    print(f'       ✅ Budget adjusted!')
                else:
                    print(f'       ⚠️ Adjustment failed: {result.get("error", "Unknown")}')
            
            campaign_details.append({
                'id': camp_id,
                'name': common.get('ad_name', 'Unnamed')[:40],
                'status': common.get('campaign_status', 'unknown'),
                'budget': current_budget,
                'target_budget': target_budget,
                'tier': tier_name,
                'target_roas': tier_config['target_roas'],
                'ad_type': common.get('ad_type', 'manual')
            })

# Step 4: Generate recommendations and auto-adjust
print('\n🎯 STEP 4: Generating recommendations and auto-adjusting...')
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
    
    # Increase budget for high-performers ONLY if ROAS is healthy
    elif camp['budget'] >= 50000 and camp['status'] == 'ongoing' and shop_roas >= TARGET_ROAS:
        new_budget = int(camp['budget'] * 1.05)  # Increase 5% (was 10%)
        # Safety cap: never exceed target budget + 20%
        max_allowed = int(camp['target_budget'] * 1.2)
        if new_budget > max_allowed:
            new_budget = max_allowed
            print(f"   ⛔ Budget cap hit for {camp['id']}: max Rp {max_allowed:,}")
        if AUTO_ADJUST_ENABLED and new_budget <= MAX_DAILY_BUDGET:
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
    
    # Decrease budget for low-performers when ROAS is below minimum
    elif camp['status'] == 'ongoing' and shop_roas < MIN_ROAS and camp['budget'] > 20000:
        new_budget = int(camp['budget'] * 0.9)  # Decrease 10%
        if new_budget < 20000:
            new_budget = 20000  # Floor
        if AUTO_ADJUST_ENABLED:
            print(f"   📉 Decreasing budget for {camp['id']} from Rp {camp['budget']:,} to Rp {new_budget:,} (low ROAS)")
            result = adjust_campaign_budget(camp['id'], new_budget)
            if result['success']:
                actions_taken.append(f"Decreased budget for campaign {camp['id']} to Rp {new_budget:,} (low ROAS)")
            else:
                recommendations.append({
                    'action': 'MANUAL_DECREASE',
                    'message': f"📉 Consider decreasing budget for {camp['id']} (ROAS {shop_roas:.2f}x < {MIN_ROAS}x)",
                    'priority': 'HIGH'
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
