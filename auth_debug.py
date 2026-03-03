#!/usr/bin/env python3
"""
Shopee Sandbox Auth Helper - DEBUG VERSION
Shows exactly what's being signed.
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
    
    print(f"Partner ID: {partner_id}")
    print(f"Partner Key: {partner_key[:20]}...")
    
    timestamp = int(time.time())
    redirect_uri = "http://localhost:8080/callback"
    api_path = "/api/v2/shop/auth_partner"
    
    # Generate signature (Shopee format: partner_id + api_path + timestamp)
    base_string = f"{partner_id}{api_path}{timestamp}"
    
    print(f"\n🔍 DEBUG INFO:")
    print(f"Base string: {base_string}")
    print(f"Timestamp: {timestamp}")
    
    signature = hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    print(f"Signature: {signature}")
    
    # Build URL (SANDBOX)
    params = {
        'partner_id': partner_id,
        'timestamp': timestamp,
        'sign': signature,
        'redirect': redirect_uri
    }
    
    url = f"https://partner.test-stable.shopeemobile.com/api/v2/shop/auth_partner?{urlencode(params)}"
    
    print(f"\n🔗 URL:")
    print(url)
    
    print("\n⚠️  If 'Wrong sign' error:")
    print("1. Check partner_key is complete (no extra spaces)")
    print("2. Verify you're using SANDBOX URL (test-stable)")
    print("3. Try regenerating with fresh timestamp")

if __name__ == '__main__':
    main()
