#!/usr/bin/env python3
"""
Apply approved recommendations from semi_auto_optimizer
Run this AFTER user replies 'APPLY' to Telegram message
"""

import requests
import hmac
import hashlib
import time
import json
import os
from datetime import datetime

from commerceos.platform.tokens import get_access_token
from commerceos.platform.shopee_config import get_ads_credentials

_ads = get_ads_credentials()
PARTNER_ID = _ads["partner_id"]
PARTNER_KEY = _ads["partner_key"]
SHOP_ID = _ads["shop_id"]
BASE_URL = "https://partner.shopeemobile.com"
APPROVAL_FILE = 'pending_approval.json'


def make_request(path, params=None, method='GET', body=None):
    access_token = get_access_token('ads')
    if not access_token:
        return {'error': 'No tokens'}

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


def update_campaign_budget(campaign_id, new_budget):
    """Update campaign budget via API."""
    body = {
        "campaign_id": campaign_id,
        "action": "change_budget",
        "campaign_budget": new_budget
    }

    result = make_request('/api/v2/ads/edit_manual_product_ads', body=body, method='POST')
    return result


def apply_recommendations():
    """Apply pending recommendations."""
    if not os.path.exists(APPROVAL_FILE):
        print("❌ No pending recommendations found.")
        return

    with open(APPROVAL_FILE, 'r') as f:
        data = json.load(f)

    if data.get('status') != 'pending_approval':
        print("ℹ️ No pending recommendations to apply.")
        return

    print("🚀 Applying approved recommendations...")
    print("="*60)

    applied = []
    failed = []

    for rec in data.get('recommendations', []):
        if rec['type'] == 'increase_budget':
            print(f"\n📈 Updating {rec['campaign_name']}:")
            print(f"   Budget: Rp {rec['current']:,} → Rp {rec['proposed']:,}")

            result = update_campaign_budget(rec['campaign_id'], rec['proposed'])

            if 'error' in result:
                print(f"   ❌ Failed: {result['error']}")
                failed.append(rec)
            else:
                print(f"   ✅ Success!")
                applied.append(rec)
        elif rec['type'] in ['hold', 'warning']:
            print(f"\nℹ️ {rec.get('message', 'No action needed')}")
            applied.append(rec)

    # Update status
    data['status'] = 'applied'
    data['applied_at'] = datetime.now().isoformat()
    data['applied_count'] = len(applied)
    data['failed_count'] = len(failed)

    with open(APPROVAL_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print("\n" + "="*60)
    print(f"✅ Applied: {len(applied)} | ❌ Failed: {len(failed)}")
    print(f"📝 Updated {APPROVAL_FILE} status to 'applied'")


if __name__ == '__main__':
    apply_recommendations()
