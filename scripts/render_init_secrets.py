#!/usr/bin/env python3
"""Initialize CommerceOS secrets from environment variables for Render deploys.

This is safe to run at every startup: it only creates the secrets file if it
does not already exist. Secrets are read from standard env vars and never
logged or printed.
"""
import json
import os
from pathlib import Path


def main() -> None:
    secret_file = Path(os.environ.get("COMMERCEOS_SECRET_FILE", ".commerceos/secrets.json"))
    if secret_file.exists():
        return

    secret_file.parent.mkdir(parents=True, exist_ok=True)

    secrets = {}
    for env_var, secret_name in {
        "SHOPEE_SHOP_ID": "shopee/shop_id",
        "SHOPEE_PRODUCTION_PARTNER_ID": "shopee/production/partner_id",
        "SHOPEE_PRODUCTION_PARTNER_KEY": "shopee/production/partner_key",
        "SHOPEE_ADS_PARTNER_ID": "shopee/ads/partner_id",
        "SHOPEE_ADS_PARTNER_KEY": "shopee/ads/partner_key",
        "TELEGRAM_BOT_TOKEN": "telegram/bot_token",
        "TELEGRAM_CHAT_ID": "telegram/chat_id",
    }.items():
        value = os.environ.get(env_var)
        if value:
            secrets[secret_name] = value

    # Optional JSON-encoded token payloads for initial seeding.
    for env_var, secret_name in {
        "SHOPEE_PROD_TOKENS": "shopee/production/tokens_json",
        "SHOPEE_ADS_TOKENS": "shopee/ads/tokens_json",
    }.items():
        value = os.environ.get(env_var)
        if value:
            # Validate JSON before storing.
            json.loads(value)
            secrets[secret_name] = value

    if not secrets:
        return

    with open(secret_file, "w", encoding="utf-8") as f:
        json.dump(secrets, f, indent=2)


if __name__ == "__main__":
    main()
