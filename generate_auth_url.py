#!/usr/bin/env python3
"""Generate Shopee OAuth re-authorization URLs for both Seller and Ads apps."""
import hmac, hashlib, time, urllib.parse

from commerceos.platform.shopee_config import get_seller_credentials, get_ads_credentials

_seller = get_seller_credentials()
_ads = get_ads_credentials()
SHOP_ID = _seller["shop_id"]

APPS = [
    {
        "name": "SELLER APP (boost, stock, orders)",
        "partner_id": _seller["partner_id"],
        "partner_key": _seller["partner_key"],
    },
    {
        "name": "ADS APP (ads performance)",
        "partner_id": _ads["partner_id"],
        "partner_key": _ads["partner_key"],
    },
]

print("Shopee OAuth Re-Auth URLs")
print("=" * 60)
for app in APPS:
    partner_id = app["partner_id"]
    partner_key = app["partner_key"]
    path = "/api/v2/shop/auth_partner"
    timestamp = int(time.time())
    base = f"{partner_id}{path}{timestamp}"
    sign = hmac.new(partner_key.encode(), base.encode(), hashlib.sha256).hexdigest()
    redirect_url = "https://shopee-automation-70ts.onrender.com"
    params = {
        "partner_id": partner_id,
        "timestamp": timestamp,
        "sign": sign,
        "redirect": redirect_url,
    }
    url = f"https://partner.shopeemobile.com{path}?{urllib.parse.urlencode(params)}"
    print(f"\n{app['name']}")
    print(f"Partner ID: {partner_id}")
    print(f"URL:\n{url}")
