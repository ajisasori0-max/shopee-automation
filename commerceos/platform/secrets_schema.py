"""Canonical secret names for CommerceOS.

All active code should reference these constants. No secret values should be
hardcoded outside the SecretManager-backed store.
"""

# Shopee store
STORE_SHOPEE_SHOP_ID = "shopee/shop_id"

# Production (Seller) app
SHOPEE_PRODUCTION_PARTNER_ID = "shopee/production/partner_id"
SHOPEE_PRODUCTION_PARTNER_KEY = "shopee/production/partner_key"
SHOPEE_PRODUCTION_TOKENS = "shopee/production/tokens_json"

# Ads app
SHOPEE_ADS_PARTNER_ID = "shopee/ads/partner_id"
SHOPEE_ADS_PARTNER_KEY = "shopee/ads/partner_key"
SHOPEE_ADS_TOKENS = "shopee/ads/tokens_json"

# Notifications
TELEGRAM_BOT_TOKEN = "telegram/bot_token"
TELEGRAM_CHAT_ID = "telegram/chat_id"

# OpenClaw / gateway
OPENCLAW_CONFIG_PATH = "openclaw/config_path"

REQUIRED_FOR_OPERATION = [
    STORE_SHOPEE_SHOP_ID,
    SHOPEE_PRODUCTION_PARTNER_ID,
    SHOPEE_PRODUCTION_PARTNER_KEY,
    SHOPEE_ADS_PARTNER_ID,
    SHOPEE_ADS_PARTNER_KEY,
]
