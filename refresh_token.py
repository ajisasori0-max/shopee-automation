#!/usr/bin/env python3
"""
Shopee API Token Refresh

Refreshes the access token using the refresh token.
Run this when your access token expires (every 4 hours).

Usage:
    python refresh_token.py
"""

import os
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
    refresh_token = os.getenv('SHOPEE_REFRESH_TOKEN')
    
    if not partner_id or partner_id == 'your_partner_id_here':
        print("❌ Error: SHOPEE_PARTNER_ID not set")
        exit(1)
    
    if not partner_key or partner_key == 'your_partner_key_here':
        print("❌ Error: SHOPEE_PARTNER_KEY not set")
        exit(1)
    
    if not refresh_token:
        print("❌ Error: SHOPEE_REFRESH_TOKEN not set")
        print("   Run get_token.py first to get initial tokens")
        exit(1)
    
    return {
        'partner_id': int(partner_id),
        'partner_key': partner_key,
        'shop_id': int(shop_id) if shop_id and shop_id != 'your_shop_id_here' else None,
        'refresh_token': refresh_token
    }

def refresh_access_token(config):
    """Refresh the access token."""
    partner_id = config['partner_id']
    partner_key = config['partner_key']
    shop_id = config['shop_id']
    refresh_token = config['refresh_token']
    
    timestamp = int(time.time())
    api_path = '/api/v2/auth/access_token/get'
    
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
        'sign': signature
    }
    url = f"https://partner.shopeemobile.com/api/v2/auth/access_token/get?{urlencode(params)}"
    
    # Request body
    body = {
        'refresh_token': refresh_token,
        'shop_id': shop_id,
        'partner_id': partner_id
    }
    
    print(f"\n🔄 Refreshing access token...")
    
    try:
        response = requests.post(url, json=body)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        return None

def update_env_file(access_token, refresh_token):
    """Update .env file with new tokens."""
    env_path = '.env'
    
    if not os.path.exists(env_path):
        print(f"❌ {env_path} not found")
        return
    
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    found_access = False
    found_refresh = False
    
    for line in lines:
        if line.startswith('SHOPEE_ACCESS_TOKEN='):
            new_lines.append(f'SHOPEE_ACCESS_TOKEN={access_token}\n')
            found_access = True
        elif line.startswith('SHOPEE_REFRESH_TOKEN='):
            new_lines.append(f'SHOPEE_REFRESH_TOKEN={refresh_token}\n')
            found_refresh = True
        else:
            new_lines.append(line)
    
    if not found_access:
        new_lines.append(f'SHOPEE_ACCESS_TOKEN={access_token}\n')
    if not found_refresh:
        new_lines.append(f'SHOPEE_REFRESH_TOKEN={refresh_token}\n')
    
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"📝 Updated {env_path}")

def main():
    print("=" * 60)
    print("🔄 Shopee API Token Refresh")
    print("=" * 60)
    
    config = load_config()
    
    result = refresh_access_token(config)
    
    if result and result.get('error') == '':
        data = result.get('data', {})
        access_token = data.get('access_token')
        refresh_token = data.get('refresh_token')
        expire_in = data.get('expire_in', 14400)
        
        print("\n" + "=" * 60)
        print("✅ Token refreshed successfully!")
        print("=" * 60)
        print(f"   New Access Token:  {access_token[:30]}...")
        print(f"   New Refresh Token: {refresh_token[:30]}...")
        print(f"   Expires in:        {expire_in} seconds ({expire_in//3600} hours)")
        
        update_env_file(access_token, refresh_token)
        
        print("\n👆 You can now run API calls again!")
        print("   Test with: python test_connection.py")
        
    else:
        print("\n" + "=" * 60)
        print("❌ Failed to refresh token")
        print("=" * 60)
        print(f"Response: {result}")
        print("\nCommon issues:")
        print("   - Refresh token expired (30 days)")
        print("   - Shop authorization revoked")
        print("   - Wrong Partner ID or Key")
        print("\nSolution: Re-run the OAuth flow from the beginning")
        print("   python auth_helper.py")

if __name__ == '__main__':
    main()
