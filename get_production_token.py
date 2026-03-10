#!/usr/bin/env python3
"""
Production Token Generator for Shopee API
Run this to get production access_token and refresh_token
"""

import requests
import time
import hmac
import hashlib
import webbrowser
from urllib.parse import urlencode

# PRODUCTION CREDENTIALS
PARTNER_ID = 2030653
SHOP_ID = 1147948100

# YOU NEED TO GET THIS FROM SHOPEE OPEN PLATFORM
# Go to: https://open.shopee.com → My Apps → Your App → App Details
PARTNER_KEY = "YOUR_LIVE_PARTNER_KEY_HERE"  # ← FILL THIS IN

def generate_sign(partner_id, path, timestamp, partner_key):
    """Generate HMAC-SHA256 signature."""
    base_string = f"{partner_id}{path}{timestamp}"
    sign = hmac.new(
        partner_key.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return sign

def get_auth_url():
    """Generate authorization URL for shop."""
    path = "/api/v2/shop/auth_partner"
    timestamp = int(time.time())
    sign = generate_sign(PARTNER_ID, path, timestamp, PARTNER_KEY)
    
    params = {
        "partner_id": PARTNER_ID,
        "timestamp": timestamp,
        "sign": sign,
        "redirect": "https://shopee-automation-70ts.onrender.com/callback"
    }
    
    url = f"https://partner.shopeemobile.com{path}?{urlencode(params)}"
    return url

def get_token_by_code(code, shop_id):
    """Exchange auth code for access token."""
    path = "/api/v2/auth/token/get"
    timestamp = int(time.time())
    sign = generate_sign(PARTNER_ID, path, timestamp, PARTNER_KEY)
    
    url = f"https://partner.shopeemobile.com{path}"
    params = {
        "partner_id": PARTNER_ID,
        "timestamp": timestamp,
        "sign": sign
    }
    
    body = {
        "code": code,
        "shop_id": shop_id,
        "partner_id": PARTNER_ID
    }
    
    resp = requests.post(url, params=params, json=body)
    return resp.json()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 SHOPEE PRODUCTION TOKEN GENERATOR")
    print("=" * 60)
    print()
    print("⚠️  BEFORE YOU START:")
    print("1. Go to https://open.shopee.com")
    print("2. Click 'My Apps' → Your App")
    print("3. Find your LIVE Partner Key (not sandbox)")
    print("4. Edit this file and set PARTNER_KEY")
    print()
    
    if PARTNER_KEY == "YOUR_LIVE_PARTNER_KEY_HERE":
        print("❌ ERROR: Please edit this file and set your PARTNER_KEY first!")
        exit(1)
    
    print("🔧 Partner ID:", PARTNER_ID)
    print("🔧 Shop ID:", SHOP_ID)
    print()
    
    # Generate auth URL
    auth_url = get_auth_url()
    print("🔗 Authorization URL:")
    print(auth_url)
    print()
    
    # Open browser
    print("🌐 Opening browser for authorization...")
    webbrowser.open(auth_url)
    print()
    
    print("=" * 60)
    print("📋 NEXT STEPS:")
    print("=" * 60)
    print("1. Login with your MAIN Shopee seller account")
    print("2. Authorize the app")
    print("3. You'll be redirected to your Render URL")
    print("4. Copy the 'code' parameter from the URL")
    print("5. Run: python3 get_production_token.py --code YOUR_CODE")
    print()
