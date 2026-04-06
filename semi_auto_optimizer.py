#!/usr/bin/env python3
"""
Shopee Ads Semi-Auto Optimizer v2.1
6 Campaigns | 980k Daily | 7x ROAS Target | ASK BEFORE ADJUSTING
"""

import requests
import hmac
import hashlib
import time
import json
import os
import sys
from datetime import datetime, timedelta

# Config
PARTNER_ID = 2030650
PARTNER_KEY = 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69'
SHOP_ID = 1147948100
BASE_URL = "https://partner.shopeemobile.com"

# PHASE 1: 7x ROAS Target (Building trust)
# ALL 6 ACTIVE CAMPAIGNS - Total: 981k
CAMPAIGNS = [
    {'id': 445446513, 'name': 'Hero 1', 'target_budget': 250000, 'target_roas': 7.0, 'min_roas': 4.0},
    {'id': 447589870, 'name': 'Hero 2', 'target_budget': 230000, 'target_roas': 7.0, 'min_roas': 4.0},
    {'id': 445311693, 'name': 'Growth 1', 'target_budget': 150000, 'target_roas': 6.0, 'min_roas': 3.5},
    {'id': 452409640, 'name': 'Growth 2', 'target_budget': 150000, 'target_roas': 6.0, 'min_roas': 3.5},
    {'id': 452411592, 'name': 'Test 1', 'target_budget': 100000, 'target_roas': 5.0, 'min_roas': 3.0},
    {'id': 445335702, 'name': 'Test 2', 'target_budget': 100000, 'target_roas': 5.0, 'min_roas': 3.0},
]
TOTAL_TARGET_BUDGET = 980000
PHASE_TARGET_ROAS = 7.0  # Step toward 12x

# Semi-auto mode - recommendations saved, you approve via Telegram
AUTO_ADJUST_ENABLED = False  # Will change to True after approval system ready
APPROVAL_FILE = 'pending_approval.json'

def log_message(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def load_tokens():
    try:
        with open('tokens_ads.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        log_message(f"❌ Error loading tokens: {e}")
        return None

def refresh_tokens():
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
            log_message("✅ Tokens refreshed")
            return data
        return None
    except Exception as e:
        log_message(f"❌ Error refreshing tokens: {e}")
        return None

def make_request(path, params=None, method='GET', body=None):
    """Make signed request to Shopee API."""
    tokens = load_tokens()
    if not tokens:
        return {'error': 'No tokens'}
    
    access_token = tokens['access_token']
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
    
    try:
        if method == 'POST':
            resp = requests.post(url, params=default_params, json=body, timeout=10)
        else:
            resp = requests.get(url, params=default_params, timeout=10)
        return resp.json()
    except Exception as e:
        return {'error': str(e)}

def get_yesterday_performance():
    """Get yesterday's ad performance."""
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%d-%m-%Y')
    
    perf_data = make_request('/api/v2/ads/get_all_cpc_ads_daily_performance', {
        'start_date': date_str, 'end_date': date_str
    })
    
    if 'response' in perf_data and perf_data['response']:
        day = perf_data['response'][0]
        return {
            'spend': day.get('expense', 0),
            'gmv': day.get('direct_gmv', 0),
            'orders': day.get('direct_order', 0),
            'roas': day.get('direct_gmv', 0) / day.get('expense', 1) if day.get('expense', 0) > 0 else 0
        }
    return {'spend': 0, 'gmv': 0, 'orders': 0, 'roas': 0}

def get_campaign_info(campaign_id):
    """Get current campaign settings."""
    detail = make_request('/api/v2/ads/get_product_level_campaign_setting_info', {
        'campaign_id_list': str(campaign_id), 'info_type_list': '1'
    })
    
    if 'response' in detail and 'campaign_list' in detail['response']:
        info = detail['response']['campaign_list'][0].get('common_info', {})
        return {
            'budget': info.get('campaign_budget', 0),
            'status': info.get('campaign_status', 'unknown'),
            'name': info.get('campaign_name', f'Campaign {campaign_id}')
        }
    return {'budget': 0, 'status': 'unknown', 'name': f'Campaign {campaign_id}'}

def generate_recommendations(yesterday_perf, campaigns_info):
    """Generate budget/roas recommendations based on performance."""
    recommendations = []
    
    roas = yesterday_perf['roas']
    spend = yesterday_perf['spend']
    
    log_message(f"📊 Yesterday: ROAS {roas:.2f}x | Spend Rp {spend:,.0f}")
    
    # Overall strategy based on ROAS
    if roas >= PHASE_TARGET_ROAS:
        # Hitting target - can scale
        for camp in CAMPAIGNS:
            info = campaigns_info.get(camp['id'], {})
            current_budget = info.get('budget', 0)
            
            if current_budget < camp['target_budget']:
                recommendations.append({
                    'type': 'increase_budget',
                    'campaign_id': camp['id'],
                    'campaign_name': camp['name'],
                    'current': current_budget,
                    'proposed': min(current_budget + 50000, camp['target_budget']),
                    'reason': f"ROAS {roas:.1f}x >= target {PHASE_TARGET_ROAS}x. Scaling budget."
                })
    elif roas >= 4.0:
        # Good but below target - hold or slight adjustment
        recommendations.append({
            'type': 'hold',
            'message': f"ROAS {roas:.1f}x is solid (min 4x). Hold current settings."
        })
    else:
        # Below minimum - need attention
        recommendations.append({
            'type': 'warning',
            'message': f"ROAS {roas:.1f}x below minimum (4x). Check listings/audience."
        })
    
    return recommendations

def save_recommendations(recs):
    """Save recommendations for user approval."""
    data = {
        'timestamp': datetime.now().isoformat(),
        'recommendations': recs,
        'status': 'pending_approval'
    }
    with open(APPROVAL_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    log_message(f"💾 Saved {len(recs)} recommendations to {APPROVAL_FILE}")

def send_telegram_summary(yesterday_perf, recommendations):
    """Send summary to Telegram (placeholder - will integrate with message tool)."""
    roas = yesterday_perf['roas']
    spend = yesterday_perf['spend']
    
    msg = f"""🎯 Shopee Ads Daily Report

📊 Yesterday ({(datetime.now() - timedelta(days=1)).strftime('%d %b')}):
   ROAS: {roas:.2f}x {'🟢' if roas >= PHASE_TARGET_ROAS else '🟡' if roas >= 4.0 else '🔴'}
   Spend: Rp {spend:,.0f}
   Orders: {yesterday_perf['orders']}

🎯 Phase 1 Target: {PHASE_TARGET_ROAS}x ROAS
💰 Daily Budget Target: Rp {TOTAL_TARGET_BUDGET:,}

"""
    
    if recommendations:
        msg += "📋 Recommendations:\n"
        for i, rec in enumerate(recommendations, 1):
            if rec['type'] == 'increase_budget':
                msg += f"\n{i}. Increase {rec['campaign_name']} budget:\n"
                msg += f"   Rp {rec['current']:,} → Rp {rec['proposed']:,}\n"
                msg += f"   Reason: {rec['reason']}\n"
            elif rec['type'] == 'hold':
                msg += f"\n{i}. HOLD: {rec['message']}\n"
            elif rec['type'] == 'warning':
                msg += f"\n{i}. ⚠️ {rec['message']}\n"
        
        msg += f"\nReply 'APPLY' to apply changes.\n"
        msg += f"Reply 'SKIP' to keep current settings.\n"
    else:
        msg += "✅ All campaigns on target. No changes needed.\n"
    
    log_message("📱 Telegram message ready:")
    print("\n" + "="*60)
    print(msg)
    print("="*60)
    
    return msg

def main():
    log_message("🚀 Starting Semi-Auto Optimizer v2.0")
    log_message(f"🎯 Phase 1 Target: {PHASE_TARGET_ROAS}x ROAS")
    
    # Get yesterday's performance
    yesterday_perf = get_yesterday_performance()
    
    # Get current campaign info
    campaigns_info = {}
    for camp in CAMPAIGNS:
        campaigns_info[camp['id']] = get_campaign_info(camp['id'])
    
    # Generate recommendations
    recommendations = generate_recommendations(yesterday_perf, campaigns_info)
    
    # Save for approval
    save_recommendations(recommendations)
    
    # Send summary
    telegram_msg = send_telegram_summary(yesterday_perf, recommendations)
    
    log_message("✅ Daily check complete. Waiting for approval.")
    
    return telegram_msg

if __name__ == '__main__':
    main()
