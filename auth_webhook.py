#!/usr/bin/env python3
"""
Shopee Auth with webhook.site redirect
"""

import os
import time
import hmac
import hashlib
from urllib.parse import urlencode

def main():
    partner_id = "1221616"
    # Get this from Shopee app page (click eye icon)
    partner_key = input("Paste your Test API Partner Key from Shopee: ").strip()
    
    # Get webhook.site URL from user
    webhook_url = input("Paste your webhook.site URL (e.g., https://webhook.site/xxx): ").strip()
    
    timestamp = int(time.time())
    api_path = "/api/v2/shop/auth_partner"
    
    # Generate signature
    base_string = f"{partner_id}{api_path}{timestamp}"
    signature = hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Build URL
    params = {
        'partner_id': partner_id,
        'timestamp': timestamp,
        'sign': signature,
        'redirect': webhook_url
    }
    
    url = f"https://partner.test-stable.shopeemobile.com/api/v2/shop/auth_partner?{urlencode(params)}"
    
    print("\n" + "=" * 60)
    print("🔗 AUTHORIZATION URL")
    print("=" * 60)
    print(url)
    print("\n" + "=" * 60)
    print("📋 NEXT STEPS:")
    print("=" * 60)
    print("1. Copy the URL above")
    print("2. Paste in browser (you should already be logged into sandbox)")
    print("3. Click 'Authorize'")
    print("4. Check your webhook.site page - you'll see the callback")
    print("5. Look for 'code=' in the query parameters")
    print("6. Copy that code and tell me!")

if __name__ == '__main__':
    main()
