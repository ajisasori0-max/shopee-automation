#!/usr/bin/env python3
"""
Shopee API Token Exchange

Exchanges the authorization code for access_token and refresh_token.
Run this after getting the auth code from the OAuth callback.

Usage:
    python get_token.py --code YOUR_AUTH_CODE
    
Or:
    python get_token.py --shop-id 123456 --code YOUR_AUTH_CODE
"""

import os
import sys
import argparse
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from dotenv import load_dotenv

def load_config():
    """Load configuration from environment."""
    load_dotenv()
    
    partner_id = os.getenv('SHOPEE_PARTNER_ID')
    partner_key = os.getenv('SHOPEE_PARTNER_KEY')
    shop_id = os.getenv('SHOPEE_SHOP_ID')
    
    if not partner_id or partner_id == 'your_partner_id_here':
        print("❌ Error: SHOPEE_PARTNER_ID not set in .env")
        exit(1)
    
    if not partner_key or partner_key == 'your_partner_key_here':
        print("❌ Error: SHOPEE_PARTNER_KEY not set in .env")
        exit(1)
    
    return {
        'partner_id': int(partner_id),
        'partner_key': partner_key,
        'shop_id': shop_id if shop_id and shop_id != 'your_shop_id_here' else None
    }

def generate_signature(partner_key, base_string):
    """Generate HMAC-SHA256 signature."""
    return hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_token(partner_id, partner_key, code, shop_id=None):
    """Exchange auth code for access token."""
    timestamp = int(time.time())
    api_path = '/api/v2/auth/token/get'
    
    # Build base string for signature
    base_string = f"{partner_id}{api_path}{timestamp}"
    signature = generate_signature(partner_key, base_string)
    
    # Build URL with query params
    params = {
        'partner_id': partner_id,
        'timestamp': timestamp,
        'sign': signature
    }
    
    url = f"https://partner.shopeemobile.com/api/v2/auth/token/get?{urlencode(params)}"
    
    # Request body
    body = {
        'code': code
    }
    if shop_id:
        body['shop_id'] = int(shop_id)
    
    print(f"\n🔄 Exchanging code for tokens...")
    print(f"   URL: {url}")
    print(f"   Body: {body}")
    
    try:
        response = requests.post(url, json=body)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        return None

def update_env_file(access_token, refresh_token, shop_id=None):
    """Update .env file with new tokens."""
    env_path = '.env'
    
    # Read existing content
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # Update or add token lines
    new_lines = []
    found_access = False
    found_refresh = False
    found_shop = False
    
    for line in lines:
        if line.startswith('SHOPEE_ACCESS_TOKEN='):
            new_lines.append(f'SHOPEE_ACCESS_TOKEN={access_token}\n')
            found_access = True
        elif line.startswith('SHOPEE_REFRESH_TOKEN='):
            new_lines.append(f'SHOPEE_REFRESH_TOKEN={refresh_token}\n')
            found_refresh = True
        elif line.startswith('SHOPEE_SHOP_ID=') and shop_id:
            new_lines.append(f'SHOPEE_SHOP_ID={shop_id}\n')
            found_shop = True
        else:
            new_lines.append(line)
    
    # Add missing lines
    if not found_access:
        new_lines.append(f'SHOPEE_ACCESS_TOKEN={access_token}\n')
    if not found_refresh:
        new_lines.append(f'SHOPEE_REFRESH_TOKEN={refresh_token}\n')
    if not found_shop and shop_id:
        new_lines.append(f'SHOPEE_SHOP_ID={shop_id}\n')
    
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"\n📝 Updated {env_path} with new tokens")

def main():
    parser = argparse.ArgumentParser(description='Exchange auth code for Shopee API tokens')
    parser.add_argument('--code', required=True, help='Authorization code from OAuth callback')
    parser.add_argument('--shop-id', help='Shop ID (optional, will be auto-detected)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔑 Shopee API Token Exchange")
    print("=" * 60)
    
    config = load_config()
    shop_id = args.shop_id or config['shop_id']
    
    if not shop_id:
        print("\n⚠️  Warning: No shop_id provided, will attempt auto-detection")
    
    result = get_token(config['partner_id'], config['partner_key'], args.code, shop_id)
    
    if result and result.get('error') == '':
        data = result.get('data', {})
        access_token = data.get('access_token')
        refresh_token = data.get('refresh_token')
        returned_shop_id = data.get('shop_id')
        expire_in = data.get('expire_in', 14400)
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS! Tokens received:")
        print("=" * 60)
        print(f"   Access Token:  {access_token[:30]}...")
        print(f"   Refresh Token: {refresh_token[:30]}...")
        print(f"   Shop ID:       {returned_shop_id}")
        print(f"   Expires in:    {expire_in} seconds ({expire_in//3600} hours)")
        
        # Update .env file
        update_env_file(access_token, refresh_token, returned_shop_id)
        
        print("\n👆 NEXT STEP:")
        print("   Test your connection: python test_connection.py")
        
    else:
        print("\n" + "=" * 60)
        print("❌ FAILED to get tokens")
        print("=" * 60)
        print(f"Response: {result}")
        print("\nCommon issues:")
        print("   - Code expired (valid for 5 minutes only)")
        print("   - Code already used")
        print("   - Wrong Partner ID or Key")
        print("   - Code from different app")

if __name__ == '__main__':
    main()
