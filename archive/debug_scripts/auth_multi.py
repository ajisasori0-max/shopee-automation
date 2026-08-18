#!/usr/bin/env python3
"""
Shopee Auth - Multiple Signature Formats
Tries different base string formats that Shopee accepts.
"""

import os
import time
import hmac
import hashlib
from urllib.parse import urlencode

def generate_sign(partner_key, base_string):
    """Generate HMAC-SHA256 signature."""
    return hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def main():
    partner_id = "1221616"
    partner_key = "shpk4d6149704f516949617a70434a416a5a476e5349705473684b596a664c6f"
    shop_id = "226682118"
    
    timestamp = int(time.time())
    redirect_uri = "http://localhost:8080/callback"
    api_path = "/api/v2/shop/auth_partner"
    
    print(f"Timestamp: {timestamp}")
    print(f"Partner ID: {partner_id}")
    print(f"Shop ID: {shop_id}")
    print("=" * 60)
    
    # Try different base string formats
    formats = [
        # Format 1: partner_id + api_path + timestamp (standard)
        f"{partner_id}{api_path}{timestamp}",
        # Format 2: partner_id + api_path + timestamp + redirect
        f"{partner_id}{api_path}{timestamp}{redirect_uri}",
        # Format 3: without leading slash
        f"{partner_id}api/v2/shop/auth_partner{timestamp}",
        # Format 4: shop_id included
        f"{partner_id}{shop_id}{timestamp}",
        # Format 5: just partner_id + timestamp
        f"{partner_id}{timestamp}",
    ]
    
    for i, base_string in enumerate(formats, 1):
        signature = generate_sign(partner_key, base_string)
        params = {
            'partner_id': partner_id,
            'timestamp': timestamp,
            'sign': signature,
            'redirect': redirect_uri
        }
        url = f"https://partner.test-stable.shopeemobile.com/api/v2/shop/auth_partner?{urlencode(params)}"
        
        print(f"\n🔍 FORMAT {i}:")
        print(f"Base: {base_string}")
        print(f"Sign: {signature}")
        print(f"URL: {url}")
        print("-" * 60)
    
    print("\n⚠️  Try each URL above (Format 1 is most likely)")
    print("If all fail, the issue might be:")
    print("  - Partner Key is wrong (check in Shopee dev portal)")
    print("  - App not approved for sandbox")
    print("  - Need to use different endpoint")

if __name__ == '__main__':
    main()
