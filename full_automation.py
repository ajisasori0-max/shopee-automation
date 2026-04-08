#!/usr/bin/env python3
"""
Shopee Full Automation v3.0
- Auto token refresh
- Daily reports with BOTH direct and broad GMV
- Product boost every 4 hours
- Zero manual intervention
"""

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
TOKENS_FILE = 'tokens_ads.json'
BOOST_LOG = 'boost_log.json'

def refresh_tokens():
    """Refresh access token automatically."""
    try:
        with open(TOKENS_FILE, 'r') as f:
            tokens = json.load(f)
        
        refresh_token = tokens['refresh_token']
        ts = int(time.time())
        path = "/api/v2/auth/access_token/get"
        base = f"{PARTNER_ID}{path}{ts}"
        sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
        
        url = f"{BASE_URL}{path}"
        resp = requests.post(url, 
            params={"partner_id": PARTNER_ID, "timestamp": ts, "sign": sign},
            json={"refresh_token": refresh_token, "shop_id": SHOP_ID, "partner_id": PARTNER_ID},
            timeout=10)
        
        data = resp.json()
        
        if 'access_token' in data:
            with open(TOKENS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            return data['access_token']
        return None
    except Exception as e:
        print(f"Token refresh error: {e}")
        return None

def get_token():
    """Get valid access token (auto-refresh if needed)."""
    try:
        with open(TOKENS_FILE, 'r') as f:
            tokens = json.load(f)
        return tokens['access_token']
    except:
        return refresh_tokens()

def make_request(path, params=None, method='GET', body=None):
    """Make API request with auto token handling."""
    access_token = get_token()
    if not access_token:
        return {'error': 'No valid token'}
    
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
        
        # If token expired, refresh and retry once
        if resp.status_code == 403 or 'invalid' in resp.text.lower():
            access_token = refresh_tokens()
            if access_token:
                ts = int(time.time())
                base = f"{PARTNER_ID}{path}{ts}{access_token}{SHOP_ID}"
                sign = hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()
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
    """Get yesterday's performance with BOTH GMV numbers."""
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%d-%m-%Y')
    
    perf = make_request('/api/v2/ads/get_all_cpc_ads_daily_performance', {
        'start_date': date_str, 'end_date': date_str
    })
    
    if 'response' in perf and perf['response']:
        day = perf['response'][0]
        return {
            'date': yesterday.strftime('%a %d %b'),
            'spend': day.get('expense', 0),
            'direct_gmv': day.get('direct_gmv', 0),
            'broad_gmv': day.get('broad_gmv', 0),
            'direct_orders': day.get('direct_order', 0),
            'broad_orders': day.get('broad_order', 0),
            'clicks': day.get('clicks', 0),
            'impressions': day.get('impression', 0),
            'direct_roas': day.get('direct_gmv', 0) / day.get('expense', 1) if day.get('expense', 0) > 0 else 0,
            'broad_roas': day.get('broad_gmv', 0) / day.get('expense', 1) if day.get('expense', 0) > 0 else 0,
        }
    return None

def boost_products():
    """Boost top 5 products (if 4 hours passed since last boost)."""
    # Check last boost time
    last_boost = None
    if os.path.exists(BOOST_LOG):
        with open(BOOST_LOG, 'r') as f:
            log = json.load(f)
            last_boost = log.get('last_boost')
    
    if last_boost:
        last_time = datetime.fromisoformat(last_boost)
        if datetime.now() - last_time < timedelta(hours=4):
            print(f"Skipping boost - last boost was {datetime.now() - last_time} ago")
            return False
    
    # Get top products
    items = make_request('/api/v2/product/get_item_list', {
        'page_size': '5', 
        'item_status': 'NORMAL',
        'offset': '0'
    })
    
    if 'response' not in items or 'item' not in items['response']:
        print("No items to boost")
        return False
    
    item_ids = [item['item_id'] for item in items['response']['item'][:5]]
    
    # Boost items
    boost_result = make_request('/api/v2/product/boost_item', method='POST', body={
        'item_id_list': item_ids
    })
    
    # Log the boost
    with open(BOOST_LOG, 'w') as f:
        json.dump({
            'last_boost': datetime.now().isoformat(),
            'items_boosted': item_ids,
            'result': boost_result
        }, f, indent=2)
    
    return boost_result

def send_telegram_report(report):
    """Send formatted report."""
    msg = f"""🎯 Shopee Daily Report - {report['date']}

💰 Spend: Rp {report['spend']:,}
📦 Direct GMV: Rp {report['direct_gmv']:,} ({report['direct_roas']:.2f}x)
📊 Broad GMV: Rp {report['broad_gmv']:,} ({report['broad_roas']:.2f}x)
🛒 Orders: {report['direct_orders']} direct / {report['broad_orders']} broad
👆 Clicks: {report['clicks']:,} | 👁 Impressions: {report['impressions']:,}

🎯 Target ROAS: 5.0-5.4x
📈 Status: {'🟢' if report['broad_roas'] >= 5 else '🟡' if report['broad_roas'] >= 4 else '🔴'} {report['broad_roas']:.2f}x
"""
    print(msg)
    return msg

def main():
    print(f"[{datetime.now()}] Running Full Automation v3.0")
    
    # 1. Daily Report (09:00)
    hour = datetime.now().hour
    if hour == 9:
        report = get_daily_report()
        if report:
            send_telegram_report(report)
        else:
            print("No report data available")
    
    # 2. Product Boost (every 4 hours)
    boost_products()
    
    print(f"[{datetime.now()}] Automation complete")

if __name__ == '__main__':
    main()
