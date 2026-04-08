#!/usr/bin/env python3
"""
Shopee Full Automation v3.1 - PROPER VERSION
- Ads App (2030650): Reports & campaign data
- Seller In-House (2030653): Product boost
- Real ROAS vs targets
- 7-day stabilization rule
"""

import requests
import hmac
import hashlib
import time
import json
import os
from datetime import datetime, timedelta

# ADS APP Config (for ads data)
ADS_PARTNER_ID = 2030650
ADS_PARTNER_KEY = 'shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69'

# SELLER APP Config (for product boost)
SELLER_PARTNER_ID = 2030653
SELLER_PARTNER_KEY = 'shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453'

SHOP_ID = 1147948100
BASE_URL = "https://partner.shopeemobile.com"

BOOST_LOG = 'boost_log.json'

def get_token(token_file, partner_id, partner_key):
    """Get valid token (auto-refresh if needed)."""
    try:
        with open(token_file, 'r') as f:
            tokens = json.load(f)
        return tokens['access_token'], tokens.get('refresh_token')
    except:
        return None, None

def refresh_token(token_file, partner_id, partner_key):
    """Refresh access token."""
    try:
        with open(token_file, 'r') as f:
            tokens = json.load(f)
        
        refresh_token = tokens['refresh_token']
        ts = int(time.time())
        path = "/api/v2/auth/access_token/get"
        base = f"{partner_id}{path}{ts}"
        sign = hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()
        
        url = f"{BASE_URL}{path}"
        resp = requests.post(url, 
            params={"partner_id": partner_id, "timestamp": ts, "sign": sign},
            json={"refresh_token": refresh_token, "shop_id": SHOP_ID, "partner_id": partner_id},
            timeout=10)
        
        data = resp.json()
        
        if 'access_token' in data:
            with open(token_file, 'w') as f:
                json.dump(data, f, indent=2)
            return data['access_token']
        return None
    except Exception as e:
        print(f"Token refresh error: {e}")
        return None

def make_request(path, params=None, method='GET', body=None, token_file=None, partner_id=None, partner_key=None):
    """Make API request with auto token handling."""
    access_token, refresh_tok = get_token(token_file, partner_id, partner_key)
    if not access_token:
        access_token = refresh_token(token_file, partner_id, partner_key)
    
    if not access_token:
        return {'error': 'No valid token'}
    
    ts = int(time.time())
    base = f"{partner_id}{path}{ts}{access_token}{SHOP_ID}"
    sign = hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()
    
    url = f"{BASE_URL}{path}"
    default_params = {
        'partner_id': partner_id,
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
        
        # If token expired, refresh and retry
        if resp.status_code == 403 or 'invalid' in resp.text.lower():
            access_token = refresh_token(token_file, partner_id, partner_key)
            if access_token:
                ts = int(time.time())
                base = f"{partner_id}{path}{ts}{access_token}{SHOP_ID}"
                sign = hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()
                default_params['access_token'] = access_token
                default_params['timestamp'] = ts
                default_params['sign'] = sign
                
                if method == 'POST':
                    resp = requests.post(url, params=default_params, json=body, timeout=10)
                else:
                    resp = requests.get(url, params=default_params, timeout=10)
        
        return resp.json()
    except Exception as e:
        return {'error': str(e)}

def get_daily_report():
    """Get yesterday's performance with REAL ROAS."""
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%d-%m-%Y')
    
    perf = make_request('/api/v2/ads/get_all_cpc_ads_daily_performance', {
        'start_date': date_str, 'end_date': date_str
    }, token_file='tokens_ads.json', partner_id=ADS_PARTNER_ID, partner_key=ADS_PARTNER_KEY)
    
    if 'response' in perf and perf['response']:
        day = perf['response'][0]
        return {
            'date': yesterday.strftime('%a %d %b'),
            'spend': day.get('expense', 0),
            'gmv': day.get('broad_gmv', 0),  # Use broad GMV (what you care about)
            'orders': day.get('broad_order', 0),
            'roas': day.get('broad_gmv', 0) / day.get('expense', 1) if day.get('expense', 0) > 0 else 0,
        }
    return None

def get_campaign_targets():
    """Get actual ROAS targets from campaigns."""
    campaigns = [
        {'id': 445446513, 'name': 'Hero 1'},
        {'id': 447589870, 'name': 'Hero 2'},
        {'id': 445311693, 'name': 'Growth 1'},
        {'id': 452409640, 'name': 'Growth 2'},
        {'id': 452411592, 'name': 'Test 1'},
        {'id': 445335702, 'name': 'Test 2'},
    ]
    
    targets = []
    for camp in campaigns:
        detail = make_request('/api/v2/ads/get_product_level_campaign_setting_info', {
            'campaign_id_list': str(camp['id']), 'info_type_list': '3'
        }, token_file='tokens_ads.json', partner_id=ADS_PARTNER_ID, partner_key=ADS_PARTNER_KEY)
        
        if 'response' in detail and 'campaign_list' in detail['response']:
            info = detail['response']['campaign_list'][0].get('auto_bidding_info', {})
            roas_target = info.get('roas_target', 5.0) if info else 5.0
            targets.append({'name': camp['name'], 'target': roas_target})
    
    return targets

def generate_recommendations(report, targets, last_change_date=None):
    """Generate smart recommendations based on ROAS vs targets."""
    current_roas = report['roas']
    avg_target = sum(t['target'] for t in targets) / len(targets) if targets else 5.0
    
    recs = []
    
    # Check if we recently made changes
    days_since_change = 0
    if last_change_date:
        last = datetime.fromisoformat(last_change_date)
        days_since_change = (datetime.now() - last).days
    
    # The 7-day rule
    if days_since_change < 7:
        recs.append(f"⏳ STABILIZATION: {7 - days_since_change} days left before changes allowed")
        recs.append("   (Algorithm training in progress - NO CHANGES)")
        action = "HOLD"
    else:
        # After 7 days, evaluate performance
        if current_roas >= avg_target * 0.9:
            recs.append("🟢 PERFORMANCE: ROAS near target - can maintain or scale")
            action = "HOLD or SCALE"
        elif current_roas >= avg_target * 0.7:
            recs.append("🟡 PERFORMANCE: ROAS below target - optimize before scaling")
            action = "OPTIMIZE"
        else:
            recs.append("🔴 PERFORMANCE: ROAS critical - reduce budgets")
            action = "REDUCE"
    
    return recs, action

def boost_products():
    """Boost top 5 products using SELLER app."""
    # Check last boost time
    last_boost = None
    if os.path.exists(BOOST_LOG):
        with open(BOOST_LOG, 'r') as f:
            log = json.load(f)
            last_boost = log.get('last_boost')
    
    if last_boost:
        last_time = datetime.fromisoformat(last_boost)
        hours_since = (datetime.now() - last_time).total_seconds() / 3600
        if hours_since < 4:
            print(f"⏳ Boost skipped - {4 - hours_since:.1f} hours until next boost")
            return False
    
    # Get valid token for seller app
    access_token = refresh_token('tokens_production.json', SELLER_PARTNER_ID, SELLER_PARTNER_KEY)
    if not access_token:
        print("❌ Could not get valid token")
        return False
    
    # Step 1: Get item list
    ts = int(time.time())
    path = '/api/v2/product/get_item_list'
    base = f'{SELLER_PARTNER_ID}{path}{ts}{access_token}{SHOP_ID}'
    sign = hmac.new(SELLER_PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
    
    url = f'{BASE_URL}{path}'
    params = {
        'partner_id': SELLER_PARTNER_ID,
        'timestamp': ts,
        'sign': sign,
        'access_token': access_token,
        'shop_id': SHOP_ID,
        'offset': '0',
        'page_size': '5',
        'item_status': 'NORMAL'
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        items_data = resp.json()
    except Exception as e:
        print(f"❌ Error getting items: {e}")
        return False
    
    if 'response' not in items_data or 'item' not in items_data['response']:
        print(f"❌ No items found: {items_data.get('error', 'Unknown error')}")
        return False
    
    item_list = items_data['response']['item'][:5]
    item_ids = [item['item_id'] for item in item_list]
    print(f"Found {len(item_ids)} items to boost: {item_ids}")
    
    # Step 2: Boost items
    ts2 = int(time.time())
    path2 = '/api/v2/product/boost_item'
    base2 = f'{SELLER_PARTNER_ID}{path2}{ts2}{access_token}{SHOP_ID}'
    sign2 = hmac.new(SELLER_PARTNER_KEY.encode(), base2.encode(), hashlib.sha256).hexdigest()
    
    url2 = f'{BASE_URL}{path2}'
    params2 = {
        'partner_id': SELLER_PARTNER_ID,
        'timestamp': ts2,
        'sign': sign2,
        'access_token': access_token,
        'shop_id': SHOP_ID
    }
    
    body = {'item_id_list': item_ids}
    
    try:
        resp2 = requests.post(url2, params=params2, json=body, timeout=10)
        boost_result = resp2.json()
    except Exception as e:
        print(f"❌ Error boosting: {e}")
        return False
    
    # Log the boost
    with open(BOOST_LOG, 'w') as f:
        json.dump({
            'last_boost': datetime.now().isoformat(),
            'items_boosted': item_ids,
            'result': boost_result
        }, f, indent=2)
    
    if boost_result.get('error'):
        print(f"❌ Boost failed: {boost_result.get('message', 'Unknown error')}")
        return False
    
    success_count = len(boost_result.get('response', {}).get('success_list', {}).get('item_id_list', []))
    print(f"✅ Successfully boosted {success_count} products")
    return True

def send_report(report, targets, recommendations, action):
    """Send formatted report."""
    target_str = f"{min(t['target'] for t in targets):.1f}-{max(t['target'] for t in targets):.1f}" if targets else "5.0-5.4"
    
    msg = f"""🎯 Shopee Daily Report - {report['date']}

💰 Spend: Rp {report['spend']:,}
📊 GMV: Rp {report['gmv']:,}
📈 ROAS: {report['roas']:.2f}x
🎯 Target: {target_str}x
🛒 Orders: {report['orders']}

📋 RECOMMENDATION: {action}
"""
    
    for rec in recommendations:
        msg += f"\n{rec}"
    
    msg += """

⚡ NEXT STEPS:
• Monitor daily
• No changes for 7 days after adjustments
• Product boost runs every 4 hours automatically
"""
    
    print(msg)
    return msg

def main():
    print(f"[{datetime.now()}] Starting Full Automation v3.1")
    
    # 1. Daily Report (09:00 only)
    hour = datetime.now().hour
    if hour == 9:
        print("📊 Generating 09:00 report...")
        
        report = get_daily_report()
        targets = get_campaign_targets()
        
        if report:
            # Check last change date
            last_change = None
            if os.path.exists('last_change.json'):
                with open('last_change.json', 'r') as f:
                    last_change = json.load(f).get('date')
            
            recommendations, action = generate_recommendations(report, targets, last_change)
            send_report(report, targets, recommendations, action)
        else:
            print("❌ No report data available")
    
    # 2. Product Boost (every 4 hours)
    print("🚀 Checking product boost...")
    boost_products()
    
    print(f"[{datetime.now()}] Complete")

if __name__ == '__main__':
    main()
