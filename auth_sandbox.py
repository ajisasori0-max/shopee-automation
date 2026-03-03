#!/usr/bin/env python3
"""
Shopee Sandbox Auth Helper
Generates authorization URL for sandbox testing.
"""

import os
import time
import hmac
import hashlib
from urllib.parse import urlencode
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    partner_id = os.getenv('SHOPEE_PARTNER_ID')
    partner_key = os.getenv('SHOPEE_PARTNER_KEY')
    
    if not partner_id or not partner_key:
        print("❌ Error: Missing PARTNER_ID or PARTNER_KEY in .env")
        return
    
    timestamp = int(time.time())
    redirect_uri = "http://localhost:8080/callback"  # Sandbox accepts any localhost
    api_path = "/api/v2/shop/auth_partner"
    
    # Generate signature
    base_string = f"{partner_id}{api_path}{timestamp}"
    signature = hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Build URL (SANDBOX)
    params = {
        'partner_id': partner_id,
        'timestamp': timestamp,
        'sign': signature,
        'redirect': redirect_uri
    }
    
    url = f"https://partner.test-stable.shopeemobile.com/api/v2/shop/auth_partner?{urlencode(params)}"
    
    print("=" * 60)
    print("🔗 SHOPEE SANDBOX AUTHORIZATION URL")
    print("=" * 60)
    print(f"\n{url}\n")
    print("=" * 60)
    print("📋 NEXT STEPS:")
    print("=" * 60)
    print("1. Copy the URL above")
    print("2. Paste it into your browser")
    print("3. Log in with your Shopee seller account")
    print("4. Click 'Authorize'")
    print("5. You'll be redirected to localhost (404 error is OK!)")
    print("6. Copy the 'code=' parameter from the URL")
    print("   Example: http://localhost:8080/callback?code=ABC123")
    print("7. Run: python get_token.py --code ABC123")

if __name__ == '__main__':
    main()
