# Shopee Ads Simple Optimizer v1.0
# 2 campaigns, 500k total, 12x ROAS target - MANUAL CONTROL

import requests
import hmac
import hashlib
import time
import json
import os
from datetime import datetime, timedelta

from commerceos.platform.tokens import get_access_token
from commerceos.platform.shopee_config import get_ads_credentials

# Config
_ads = get_ads_credentials()
PARTNER_ID = _ads["partner_id"]
PARTNER_KEY = _ads["partner_key"]
SHOP_ID = _ads["shop_id"]
BASE_URL = "https://partner.shopeemobile.com"

# SIMPLE SETTINGS - 2 Campaigns, 500k total, 12x ROAS
CAMPAIGNS = [
    {'id': 445446513, 'name': 'Hero 1', 'budget': 250000, 'target_roas': 12.0},
    {'id': 447589870, 'name': 'Hero 2', 'budget': 250000, 'target_roas': 12.0},
]
TOTAL_DAILY_BUDGET = 500000
TARGET_ROAS = 12.0

# Manual mode - recommendations only, you decide
AUTO_ADJUST_ENABLED = False

print('='*70)
print('🎯 SHOPEE ADS SIMPLE OPTIMIZER')
print('2 Campaigns | 500k Daily | 12x ROAS Target')
print('='*70)

# Central token authority: get valid access token, never refresh/write here.
access_token = get_access_token('ads')
if not access_token:
    print('❌ Error: Cannot get valid access token')
    exit(1)

def refresh_tokens():
    """Refresh access token via central token authority."""
    global access_token
    access_token = get_access_token('ads', force_refresh=True)
    return {'access_token': access_token} if access_token else None

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

# Get 7-day performance
print('\n📊 Last 7 Days Performance')
print('='*70)

end_date = datetime.now()
start_date = end_date - timedelta(days=7)
start_date_str = start_date.strftime('%d-%m-%Y')
end_date_str = end_date.strftime('%d-%m-%Y')

perf_data = make_request('/api/v2/ads/get_all_cpc_ads_daily_performance', {
    'start_date': start_date_str, 'end_date': end_date_str
})

total_spend = 0
total_gmv = 0
total_orders = 0

if 'response' in perf_data:
    for day in perf_data['response']:
        total_spend += day.get('expense', 0)
        total_gmv += day.get('direct_gmv', 0)
        total_orders += day.get('direct_order', 0)

shop_roas = total_gmv / total_spend if total_spend > 0 else 0

print(f'Total Spend: Rp {total_spend:,.0f}')
print(f'Total GMV: Rp {total_gmv:,.0f}')
print(f'Total Orders: {total_orders}')
print(f'Overall ROAS: {shop_roas:.2f}x')
print(f'Target ROAS: {TARGET_ROAS}x')
print(f'Gap to Target: {((TARGET_ROAS - shop_roas) / shop_roas * 100) if shop_roas > 0 else 0:.1f}%')

# Check individual campaigns
print('\n📋 Your 2 Campaigns:')
print('='*70)

for camp in CAMPAIGNS:
    camp_id = camp['id']
    
    # Get campaign details
    detail = make_request('/api/v2/ads/get_product_level_campaign_setting_info', {
        'campaign_id_list': str(camp_id), 'info_type_list': '1'
    })
    
    if 'response' in detail and 'campaign_list' in detail['response']:
        info = detail['response']['campaign_list'][0].get('common_info', {})
        current_budget = info.get('campaign_budget', 0)
        status = info.get('campaign_status', 'unknown')
        
        print(f"\n{camp['name']} (ID: {camp_id})")
        print(f"  Current Budget: Rp {current_budget:,} / Target: Rp {camp['budget']:,}")
        print(f"  Status: {status}")
        print(f"  Target ROAS: {camp['target_roas']}x")
        
        # Recommendation
        if current_budget < camp['budget'] * 0.9:
            print(f"  ⚠️  RECOMMENDATION: Increase budget to Rp {camp['budget']:,}")
        elif current_budget > camp['budget'] * 1.1:
            print(f"  ⚠️  RECOMMENDATION: Decrease budget to Rp {camp['budget']:,}")
        else:
            print(f"  ✅ Budget on target")

print('\n' + '='*70)
print('📈 RECOMMENDATIONS:')
print('='*70)

if shop_roas < TARGET_ROAS * 0.8:
    print(f'🔴 ROAS too low ({shop_roas:.1f}x < {TARGET_ROAS * 0.8:.1f}x)')
    print('   → Lower ROAS target temporarily OR optimize product listings')
elif shop_roas < TARGET_ROAS:
    print(f'🟡 ROAS improving ({shop_roas:.1f}x, target {TARGET_ROAS}x)')
    print('   → Keep current settings, monitor daily')
else:
    print(f'🟢 ROAS on target ({shop_roas:.1f}x >= {TARGET_ROAS}x)')
    print('   → Scale budget if consistent for 3+ days')

print(f'\n💰 Total Daily Budget: Rp {sum(c["budget"] for c in CAMPAIGNS):,}')
print(f'🎯 Target: 12x ROAS with Rp 500k daily spend')

print('\n' + '='*70)
print('✅ Check complete. Manual adjustments recommended.')
print('='*70)
