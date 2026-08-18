"""Centralized Shopee credential loader.

All active production code should obtain Shopee partner IDs, partner keys,
shop ID, and Telegram credentials through this module. No hardcoded secrets.
"""
from commerceos.platform import secrets_schema as secrets
from commerceos.platform.secrets import workspace_secret_manager

_sm = workspace_secret_manager()


def _int(name: str) -> int:
    return int(_sm.get_required(name))


def get_seller_credentials() -> dict:
    """Return production (Seller) app credentials."""
    return {
        "partner_id": _int(secrets.SHOPEE_PRODUCTION_PARTNER_ID),
        "partner_key": _sm.get_required(secrets.SHOPEE_PRODUCTION_PARTNER_KEY),
        "shop_id": _int(secrets.STORE_SHOPEE_SHOP_ID),
        "app_name": "production",
    }


def get_ads_credentials() -> dict:
    """Return Ads app credentials."""
    return {
        "partner_id": _int(secrets.SHOPEE_ADS_PARTNER_ID),
        "partner_key": _sm.get_required(secrets.SHOPEE_ADS_PARTNER_KEY),
        "shop_id": _int(secrets.STORE_SHOPEE_SHOP_ID),
        "app_name": "ads",
    }


def get_telegram_credentials() -> dict:
    """Return Telegram bot token and chat ID."""
    return {
        "bot_token": _sm.get_required(secrets.TELEGRAM_BOT_TOKEN),
        "chat_id": _sm.get_required(secrets.TELEGRAM_CHAT_ID),
    }


def get_all_credentials() -> dict:
    """Return seller, ads, and Telegram credentials in one dict."""
    return {
        "seller": get_seller_credentials(),
        "ads": get_ads_credentials(),
        "telegram": get_telegram_credentials(),
    }
