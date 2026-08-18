#!/usr/bin/env python3
"""Generate Render environment variables from local secrets.

Run this on your Mac, then paste the output into the Render dashboard.
"""
import json
from pathlib import Path


def main() -> None:
    workspace = Path(__file__).parent.parent
    secrets_file = workspace / ".commerceos" / "secrets.json"
    prod_tokens_file = workspace / "tokens_production.json"
    ads_tokens_file = workspace / "tokens_ads.json"

    if not secrets_file.exists():
        print(f"❌ Secrets file not found: {secrets_file}")
        return

    secrets = json.loads(secrets_file.read_text())

    prod_tokens = None
    ads_tokens = None
    if prod_tokens_file.exists():
        prod_tokens = json.loads(prod_tokens_file.read_text())
    if ads_tokens_file.exists():
        ads_tokens = json.loads(ads_tokens_file.read_text())

    print("\n# Paste these into Render Dashboard → Environment")
    print("# Service: shopee-automation-70ts\n")

    print(f'SHOPEE_SHOP_ID={secrets.get("shopee/shop_id", "")}')
    print(f'SHOPEE_PRODUCTION_PARTNER_ID={secrets.get("shopee/production/partner_id", "")}')
    print(f'SHOPEE_PRODUCTION_PARTNER_KEY={secrets.get("shopee/production/partner_key", "")}')
    print(f'SHOPEE_ADS_PARTNER_ID={secrets.get("shopee/ads/partner_id", "")}')
    print(f'SHOPEE_ADS_PARTNER_KEY={secrets.get("shopee/ads/partner_key", "")}')

    if prod_tokens:
        print(f'SHOPEE_PROD_TOKENS={json.dumps(prod_tokens, separators=(",", ":"))}')
    if ads_tokens:
        print(f'SHOPEE_ADS_TOKENS={json.dumps(ads_tokens, separators=(",", ":"))}')

    if secrets.get("telegram/bot_token"):
        print(f'TELEGRAM_BOT_TOKEN={secrets["telegram/bot_token"]}')
    if secrets.get("telegram/chat_id"):
        print(f'TELEGRAM_CHAT_ID={secrets["telegram/chat_id"]}')

    print("\n# The following are already set as defaults in render.yaml")
    print("# DATABASE_URL=sqlite:///data/commerceos.db")
    print("# COMMERCEOS_STORE_ID=store-ppm-001")
    print("# COMMERCEOS_SECRET_FILE=/data/.commerceos/secrets.json")
    print("# COMMERCEOS_TOKEN_WORKSPACE=/data")
    print("# COMMERCEOS_BACKGROUND_SYNC=1")
    print("# FULL_RESYNC=0")


if __name__ == "__main__":
    main()
