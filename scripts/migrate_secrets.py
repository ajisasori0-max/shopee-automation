"""One-time migration: seed SecretManager with current Shopee credentials.

This reads the existing hardcoded values and token files, then writes them to
the configured SecretManager store (env var or local secrets.json). After this
runs, token_manager.py and all active scripts will obtain credentials through
SecretManager instead of hardcoded values.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from commerceos.platform.secrets import workspace_secret_manager
from commerceos.platform import secrets_schema as secrets

# Current known values (these were previously hardcoded across the codebase).
# Keeping them in this single one-time migration script is acceptable because
# the script is run once and then the values live in the secret store.
LEGACY = {
    secrets.STORE_SHOPEE_SHOP_ID: "1147948100",
    secrets.SHOPEE_PRODUCTION_PARTNER_ID: "2030653",
    secrets.SHOPEE_PRODUCTION_PARTNER_KEY: "shpk44444e634d6668466c5073776b45646454774a7975706d47497063526453",
    secrets.SHOPEE_ADS_PARTNER_ID: "2030650",
    secrets.SHOPEE_ADS_PARTNER_KEY: "shpk596a6556535573774b4e7742454a4f566e42794c7549736c4c59594c6a69",
    secrets.TELEGRAM_CHAT_ID: "6910422824",
}


def _load_token_json(path: Path) -> str:
    if path.exists():
        return path.read_text()
    return ""


def main():
    sm = workspace_secret_manager()
    workspace = Path(".")

    file_provider_index = 1  # write to LocalFileProvider, not ephemeral EnvVarProvider

    # Seed partner credentials and shop ID.
    for name, value in LEGACY.items():
        if not sm.providers[file_provider_index].exists(name):
            sm.set(name, value, provider_index=file_provider_index)
            print(f"Set {name}")
        else:
            print(f"Already exists: {name}")

    # Seed token JSON blobs if present.
    prod_tokens = _load_token_json(workspace / "tokens_production.json")
    ads_tokens = _load_token_json(workspace / "tokens_ads.json")
    if prod_tokens and not sm.providers[file_provider_index].exists(secrets.SHOPEE_PRODUCTION_TOKENS):
        sm.set(secrets.SHOPEE_PRODUCTION_TOKENS, prod_tokens, provider_index=file_provider_index)
        print(f"Set {secrets.SHOPEE_PRODUCTION_TOKENS}")
    if ads_tokens and not sm.providers[file_provider_index].exists(secrets.SHOPEE_ADS_TOKENS):
        sm.set(secrets.SHOPEE_ADS_TOKENS, ads_tokens, provider_index=file_provider_index)
        print(f"Set {secrets.SHOPEE_ADS_TOKENS}")

    # Telegram bot token is read from OpenClaw config if available.
    openclaw_path = Path("/Users/gerard/.openclaw/openclaw.json")
    if openclaw_path.exists():
        cfg = json.loads(openclaw_path.read_text())
        bot_token = cfg.get("channels", {}).get("telegram", {}).get("botToken")
        if bot_token and not sm.providers[file_provider_index].exists(secrets.TELEGRAM_BOT_TOKEN):
            sm.set(secrets.TELEGRAM_BOT_TOKEN, bot_token, provider_index=file_provider_index)
            print(f"Set {secrets.TELEGRAM_BOT_TOKEN}")

    print("\nMigration complete. Verify with:")
    print("  python3 -m pytest tests/unit/test_secrets.py -v")


if __name__ == "__main__":
    main()
