#!/usr/bin/env python3
"""
Shopee Open API Client
Handles authentication, signatures, and token refresh automatically.
"""

import hmac
import hashlib
import time
import json
import requests
from pathlib import Path


class ShopeeClient:
    """Shopee Open API Client with automatic token refresh."""
    
    def __init__(self, partner_id, partner_key, shop_id, tokens_file="tokens.json", sandbox=True):
        """
        Initialize Shopee API client.
        
        Args:
            partner_id: Your Partner ID
            partner_key: Your Partner Key (Test or Live)
            shop_id: Your Shop ID
            tokens_file: Path to tokens JSON file
            sandbox: True for sandbox, False for production
        """
        self.partner_id = int(partner_id)
        self.partner_key = partner_key
        self.shop_id = int(shop_id)
        self.tokens_file = Path(tokens_file)
        self.sandbox = sandbox
        
        # Set base URL
        if sandbox:
            self.base_url = "https://openplatform.sandbox.test-stable.shopee.sg"
        else:
            self.base_url = "https://partner.shopeemobile.com"
        
        # Load tokens
        self._load_tokens()
    
    def _load_tokens(self):
        """Load tokens from file."""
        if self.tokens_file.exists():
            with open(self.tokens_file, 'r') as f:
                data = json.load(f)
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                self.token_expire_time = time.time() + data.get('expire_in', 14400)
        else:
            raise FileNotFoundError(f"Tokens file not found: {self.tokens_file}")
    
    def _save_tokens(self, data):
        """Save tokens to file."""
        with open(self.tokens_file, 'w') as f:
            json.dump(data, f, indent=2)
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.token_expire_time = time.time() + data.get('expire_in', 14400)
    
    def _generate_sign(self, path, timestamp, is_public_api=False):
        """
        Generate HMAC-SHA256 signature.
        
        Args:
            path: API path (e.g., /api/v2/shop/get_shop_info)
            timestamp: Unix timestamp
            is_public_api: True for auth/token APIs (no access_token/shop_id in base string)
        """
        if is_public_api:
            # Public API: partner_id + path + timestamp
            base_string = f"{self.partner_id}{path}{timestamp}"
        else:
            # Shop API: partner_id + path + timestamp + access_token + shop_id
            base_string = f"{self.partner_id}{path}{timestamp}{self.access_token}{self.shop_id}"
        
        sign = hmac.new(
            self.partner_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return sign
    
    def _refresh_access_token(self):
        """Refresh access token using refresh_token."""
        print("🔄 Refreshing access token...")
        
        path = "/api/v2/auth/access_token/get"
        timestamp = int(time.time())
        
        # Public API signature for refresh
        sign = self._generate_sign(path, timestamp, is_public_api=True)
        
        url = f"{self.base_url}{path}"
        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "sign": sign
        }
        
        body = {
            "refresh_token": self.refresh_token,
            "shop_id": self.shop_id,
            "partner_id": self.partner_id
        }
        
        resp = requests.post(url, params=params, json=body)
        data = resp.json()
        
        if resp.status_code == 200 and 'access_token' in data:
            self._save_tokens(data)
            print(f"✅ Token refreshed! Valid for {data.get('expire_in', 14400)} seconds")
            return True
        else:
            raise Exception(f"Token refresh failed: {data.get('message', 'Unknown error')}")
    
    def _ensure_valid_token(self):
        """Check token validity and refresh if needed."""
        # Refresh if less than 5 minutes remaining
        if time.time() > (self.token_expire_time - 300):
            self._refresh_access_token()
    
    def call_api(self, method, path, params=None, body=None, is_public_api=False):
        """
        Make API call with automatic signature and token handling.
        
        Args:
            method: 'GET' or 'POST'
            path: API path (e.g., /api/v2/shop/get_shop_info)
            params: Additional query parameters (dict)
            body: Request body for POST (dict)
            is_public_api: True for auth APIs, False for shop APIs
        """
        # Ensure token is valid (for shop APIs)
        if not is_public_api:
            self._ensure_valid_token()
        
        timestamp = int(time.time())
        sign = self._generate_sign(path, timestamp, is_public_api)
        
        # Build URL
        url = f"{self.base_url}{path}"
        
        # Build query params
        query_params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "sign": sign
        }
        
        if not is_public_api:
            query_params["access_token"] = self.access_token
            query_params["shop_id"] = self.shop_id
        
        # Add extra params
        if params:
            query_params.update(params)
        
        # Make request
        headers = {"Content-Type": "application/json"}
        
        if method.upper() == "GET":
            resp = requests.get(url, params=query_params, headers=headers)
        else:
            resp = requests.post(url, params=query_params, json=body or {}, headers=headers)
        
        # Parse response
        data = resp.json()
        
        return {
            "status_code": resp.status_code,
            "data": data,
            "ok": resp.status_code == 200 and not data.get('error')
        }
    
    # ===== SHOP APIs =====
    
    def get_shop_info(self):
        """Get shop information."""
        return self.call_api("GET", "/api/v2/shop/get_shop_info")
    
    # ===== PRODUCT APIs =====
    
    def get_product_list(self, page_size=10):
        """Get list of products."""
        return self.call_api("GET", "/api/v2/product/get_item_list", params={"page_size": page_size})
    
    def get_product_detail(self, item_id):
        """Get product details."""
        return self.call_api("GET", "/api/v2/product/get_item_base_info", params={"item_id_list": item_id})
    
    def update_stock(self, item_id, stock, model_id=None):
        """Update product stock."""
        body = {
            "item_id": int(item_id),
            "stock_list": [{
                "seller_stock": [{"stock": int(stock)}]
            }]
        }
        if model_id:
            body["stock_list"][0]["model_id"] = int(model_id)
        
        return self.call_api("POST", "/api/v2/product/update_stock", body=body)
    
    def update_price(self, item_id, price, model_id=None):
        """Update product price."""
        body = {
            "item_id": int(item_id),
            "price_list": [{"original_price": float(price)}]
        }
        if model_id:
            body["price_list"][0]["model_id"] = int(model_id)
        
        return self.call_api("POST", "/api/v2/product/update_price", body=body)
    
    # ===== ADS APIs =====
    
    def get_ad_balance(self):
        """Get total ad credit balance."""
        return self.call_api("GET", "/api/v2/ads/get_total_balance")
    
    def get_ad_settings(self):
        """Get shop ad settings (auto top-up, etc)."""
        return self.call_api("GET", "/api/v2/ads/get_shop_toggle_info")
    
    def get_ad_performance_daily(self, start_date, end_date):
        """
        Get daily ad performance.
        
        Args:
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
        """
        return self.call_api("GET", "/api/v2/ads/get_all_cpc_ads_daily_performance", 
                           params={"start_date": start_date, "end_date": end_date})
    
    def get_recommended_keywords(self, item_id):
        """Get recommended keywords for a product."""
        return self.call_api("GET", "/api/v2/ads/get_recommended_keyword_list",
                           params={"item_id": item_id})


# ===== USAGE EXAMPLE =====
if __name__ == "__main__":
    # Initialize client - PRODUCTION MODE
    client = ShopeeClient(
        partner_id=2030653,
        partner_key="YOUR_LIVE_PARTNER_KEY",  # Get from Shopee Open Platform
        shop_id=1147948100,
        tokens_file="tokens_production.json",
        sandbox=False  # PRODUCTION!
    )
    
    # Example: Get shop info
    print("🏪 Getting shop info...")
    result = client.get_shop_info()
    if result['ok']:
        print(f"✅ Shop: {result['data'].get('shop_name')}")
        print(f"   Region: {result['data'].get('region')}")
        print(f"   Status: {result['data'].get('status')}")
    else:
        print(f"❌ Error: {result['data']}")
    
    # Example: Get ad balance
    print("\n💰 Getting ad balance...")
    result = client.get_ad_balance()
    if result['ok']:
        balance = result['data'].get('response', {}).get('total_balance', 0)
        print(f"✅ Ad Balance: {balance}")
    else:
        print(f"❌ Error: {result['data']}")
