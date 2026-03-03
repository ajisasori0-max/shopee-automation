#!/usr/bin/env python3
"""
Shopee API Authorization Helper

Generates the authorization URL for shop OAuth flow.
Run this first to get the URL to authorize your shop.

Usage:
    python auth_helper.py
    
Output:
    Authorization URL to open in browser
"""

import os
import time
import hmac
import hashlib
from urllib.parse import urlencode
from dotenv import load_dotenv

def load_config():
    """Load configuration from environment."""
    load_dotenv()
    
    partner_id = os.getenv('SHOPEE_PARTNER_ID')
    partner_key = os.getenv('SHOPEE_PARTNER_KEY')
    redirect_uri = os.getenv('SHOPEE_REDIRECT_URI', 'http://localhost:8080/callback')
    
    if not partner_id or partner_id == 'your_partner_id_here':
        print("❌ Error: SHOPEE_PARTNER_ID not set")
        print("   Edit .env file and add your actual Partner ID")
        exit(1)
    
    if not partner_key or partner_key == 'your_partner_key_here':
        print("❌ Error: SHOPEE_PARTNER_KEY not set")
        print("   Edit .env file and add your actual Partner Key")
        exit(1)
    
    return {
        'partner_id': int(partner_id),
        'partner_key': partner_key,
        'redirect_uri': redirect_uri
    }

def generate_signature(partner_key, base_string):
    """Generate HMAC-SHA256 signature."""
    return hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def build_auth_url(config):
    """Build the authorization URL with signature."""
    partner_id = config['partner_id']
    partner_key = config['partner_key']
    redirect_uri = config['redirect_uri']
    timestamp = int(time.time())
    
    # Base string for signature: partner_id + api_path + timestamp
    api_path = '/api/v2/shop/auth_partner'
    base_string = f"{partner_id}{api_path}{timestamp}"
    
    signature = generate_signature(partner_key, base_string)
    
    params = {
        'partner_id': partner_id,
        'redirect': redirect_uri,
        'timestamp': timestamp,
        'sign': signature
    }
    
    base_url = 'https://partner.shopeemobile.com/api/v2/shop/auth_partner'
    auth_url = f"{base_url}?{urlencode(params)}"
    
    return auth_url

def main():
    print("=" * 60)
    print("🔐 Shopee API Authorization Helper")
    print("=" * 60)
    
    config = load_config()
    
    print(f"\n📋 Partner ID: {config['partner_id']}")
    print(f"🔗 Redirect URI: {config['redirect_uri']}")
    
    auth_url = build_auth_url(config)
    
    print("\n" + "=" * 60)
    print("🔗 AUTHORIZATION URL:")
    print("=" * 60)
    print(auth_url)
    print("=" * 60)
    
    print("\n👆 NEXT STEPS:")
    print("   1. Copy the URL above")
    print("   2. Paste into your browser")
    print("   3. Log in with your Shopee Seller account")
    print("   4. Click 'Authorize'")
    print("   5. You'll be redirected to your redirect URI")
    print("   6. Copy the 'code' parameter from the URL")
    print("   7. Run: python get_token.py --code YOUR_CODE")
    
    print("\n⚠️  NOTE: The auth code expires in 5 minutes!")
    
    # Also save to file for convenience
    with open('auth_url.txt', 'w') as f:
        f.write(auth_url)
    print("\n📝 URL also saved to: auth_url.txt")

if __name__ == '__main__':
    main()
