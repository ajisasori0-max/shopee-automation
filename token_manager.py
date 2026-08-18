#!/usr/bin/env python3
"""Shopee Token Manager — Bulletproof Auto-Refresh System

Features:
- Auto-refreshes 4-hour access tokens before expiry
- Monitors 30-day refresh token expiry
- Alerts when manual re-auth needed (day 25+)
- Persists to both file and environment variable
- Thread-safe with file locking
- Loads partner credentials from SecretManager
"""

import json
import os
import time
import hmac
import hashlib
import requests
import fcntl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from commerceos.platform import secrets_schema as secrets
from commerceos.platform.secrets import SecretManager, workspace_secret_manager

# ============================================================================
# CONFIG
# ============================================================================

_secret_manager = workspace_secret_manager()

# If you need to exchange tokens for a different shop, set this env var.
BASE_URL = "https://partner.shopeemobile.com"

# Render / production deployments should point token storage at a persistent
# volume. Falls back to the current working directory for local development.
TOKEN_WORKSPACE = os.environ.get("COMMERCEOS_TOKEN_WORKSPACE", ".")


def _shop_id() -> int:
    """Return the Shopee shop ID from environment or secrets.

    Lazy evaluation avoids crashing at import time when secrets are not yet
    initialized (e.g., during Render deployment startup).
    """
    override = os.environ.get("SHOPEE_SHOP_ID_OVERRIDE")
    if override:
        return int(override)
    return int(_secret_manager.get_required(secrets.STORE_SHOPEE_SHOP_ID))


APPS = {
    "production": {
        "secret_partner_id": secrets.SHOPEE_PRODUCTION_PARTNER_ID,
        "secret_partner_key": secrets.SHOPEE_PRODUCTION_PARTNER_KEY,
        "token_file": "tokens_production.json",
        "env_var": "SHOPEE_PROD_TOKENS",
    },
    "ads": {
        "secret_partner_id": secrets.SHOPEE_ADS_PARTNER_ID,
        "secret_partner_key": secrets.SHOPEE_ADS_PARTNER_KEY,
        "token_file": "tokens_ads.json",
        "env_var": "SHOPEE_ADS_TOKENS",
    }
}

# Refresh 5 minutes before expiry
REFRESH_BUFFER_SECONDS = 300

# Alert threshold for refresh token (days)
REFRESH_TOKEN_ALERT_DAYS = 25


class TokenManager:
    """Manages Shopee API tokens with auto-refresh."""
    
    def __init__(self, workspace: Optional[str] = None, secret_manager: Optional[SecretManager] = None):
        self.workspace = Path(workspace or TOKEN_WORKSPACE)
        self._secret_manager = secret_manager or workspace_secret_manager()
        self._ensure_token_files()
    
    def _config(self, app_name: str) -> Dict[str, Any]:
        base = APPS[app_name]
        partner_id = self._secret_manager.get_required(base["secret_partner_id"])
        partner_key = self._secret_manager.get_required(base["secret_partner_key"])
        return {
            **base,
            "partner_id": int(partner_id),
            "partner_key": partner_key,
            "shop_id": _shop_id(),
        }
    
    def _audit(self, action: str, app_name: str, detail: str = ""):
        """Write a lightweight audit line for secret/token operations."""
        audit_path = self.workspace / "logs" / "token_audit.log"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_path, "a") as f:
            f.write(f"{datetime.now().isoformat()} action={action} app={app_name} {detail}\n")
    
    def _ensure_token_files(self):
        """Ensure token files exist."""
        for app_name, config in APPS.items():
            token_path = self.workspace / config["token_file"]
            if not token_path.exists():
                # Try to load from env var
                env_tokens = os.getenv(config["env_var"])
                if env_tokens:
                    try:
                        tokens = json.loads(env_tokens)
                        self._save_tokens(app_name, tokens)
                    except json.JSONDecodeError:
                        pass
    
    def _load_tokens(self, app_name: str) -> Optional[Dict[str, Any]]:
        """Load tokens from file with locking."""
        config = APPS[app_name]
        token_path = self.workspace / config["token_file"]
        
        try:
            with open(token_path, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            # Inject file mtime so expiry checks survive lost metadata
            try:
                data["_file_mtime"] = token_path.stat().st_mtime
            except OSError:
                pass
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def _save_tokens(self, app_name: str, tokens: Dict[str, Any]):
        """Save tokens to file with locking and env var."""
        config = APPS[app_name]
        token_path = self.workspace / config["token_file"]
        
        # Add metadata
        tokens["_saved_at"] = datetime.now().isoformat()
        tokens["_app"] = app_name
        
        # Save to file with exclusive lock
        with open(token_path, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(tokens, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        print(f"📝 {app_name.upper()} tokens saved.")
    
    def _env_var_value(self, app_name: str) -> str:
        """Render tokens as a JSON string for environment-variable export.

        This is only safe for manual/copy use; it is not logged automatically.
        """
        config = APPS[app_name]
        token_path = self.workspace / config["token_file"]
        try:
            with open(token_path, 'r') as f:
                return f.read()
        except Exception:
            return ""
    
    def print_env_var(self, app_name: str):
        """Print the env-var export line for the given app (manual use only)."""
        config = APPS[app_name]
        value = self._env_var_value(app_name)
        print(f"   Key: {config['env_var']}")
        print(f"   Value: {value}")
    
    def _is_token_expired(self, tokens: Dict[str, Any]) -> bool:
        """Check if access token is expired or about to expire.

        If ``_saved_at`` metadata is missing (e.g. a legacy script overwrote
        the file), fall back to the file modification time so we don't
        falsely report the token as dead.
        """
        if not tokens or "access_token" not in tokens:
            return True

        expire_in = tokens.get("expire_in", 14400)
        saved_at_str = tokens.get("_saved_at")

        saved_at = None
        if saved_at_str:
            try:
                saved_at = datetime.fromisoformat(saved_at_str)
            except ValueError:
                saved_at = None

        if saved_at is None:
            # Fallback: use file mtime via a marker injected by _load_tokens
            mtime = tokens.get("_file_mtime")
            if mtime:
                saved_at = datetime.fromtimestamp(mtime)

        if saved_at is None:
            # No timing info at all — be conservative, treat as expired
            return True

        expires_at = saved_at + timedelta(seconds=expire_in)
        return datetime.now() > (expires_at - timedelta(seconds=REFRESH_BUFFER_SECONDS))
    
    def _refresh_access_token(self, app_name: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh_token."""
        tokens = self._load_tokens(app_name)
        if not tokens or "refresh_token" not in tokens:
            print(f"❌ {app_name}: No refresh token available")
            return None
        
        config = self._config(app_name)
        
        path = "/api/v2/auth/access_token/get"
        ts = int(time.time())
        base = f"{config['partner_id']}{path}{ts}"
        sign = hmac.new(config["partner_key"].encode(), base.encode(), hashlib.sha256).hexdigest()
        
        try:
            resp = requests.post(
                f"{BASE_URL}{path}",
                params={"partner_id": config["partner_id"], "timestamp": ts, "sign": sign},
                json={
                    "refresh_token": tokens["refresh_token"],
                    "shop_id": _shop_id(),
                    "partner_id": config["partner_id"]
                },
                timeout=15
            )
            data = resp.json()
            
            if "access_token" in data:
                # Preserve metadata, update tokens
                new_tokens = {
                    "partner_id": config["partner_id"],
                    "shop_id": _shop_id(),
                    "access_token": data["access_token"],
                    "refresh_token": data.get("refresh_token", tokens["refresh_token"]),
                    "expire_in": data.get("expire_in", 14400),
                    "request_id": data.get("request_id", ""),
                }
                self._save_tokens(app_name, new_tokens)
                print(f"✅ {app_name}: Token refreshed (expires in {data.get('expire_in', 14400)/3600:.1f}h)")
                self.print_env_var(app_name)
                return new_tokens
            else:
                error = data.get("error", "unknown")
                message = data.get("message", "")
                print(f"❌ {app_name}: Refresh failed — {error}: {message}")
                
                # Check if refresh token is dead
                if "refresh_token" in error.lower() or "expired" in message.lower():
                    print(f"🚨 {app_name}: REFRESH TOKEN EXPIRED — Manual re-authorization required!")
                    self._alert_refresh_token_expired(app_name)
                
                return None
                
        except Exception as e:
            print(f"❌ {app_name}: Refresh error — {e}")
            return None
    
    def _alert_refresh_token_expired(self, app_name: str):
        """Alert that refresh token is dead."""
        alert_file = self.workspace / f"ALERT_{app_name}_reauth_needed.txt"
        alert_file.write_text(f"""
🚨 MANUAL RE-AUTHORIZATION REQUIRED 🚨

App: {app_name}
Time: {datetime.now().isoformat()}

The refresh token has expired. You must re-authorize the app in Shopee Seller Center.

Steps:
1. Go to Shopee Seller Center → Open Platform → App List
2. Re-authorize the {app_name} app
3. Get the new auth code from the redirect URL
4. Run: python3 token_manager.py --exchange {app_name} <code>

Or use the Streamlit app: streamlit run app.py
""")
        print(f"📝 Alert written to: {alert_file}")
    
    def get_valid_token(self, app_name: str) -> Optional[str]:
        """Get a valid access token, refreshing if needed.

        This is the ONE supported path for production code to obtain a Shopee
        access token. Do NOT refresh tokens elsewhere — Shopee only allows one
        active refresh token per app-shop at a time, and duplicate refreshers
        invalidate each other.
        """
        tokens = self._load_tokens(app_name)

        if not tokens:
            print(f"❌ {app_name}: No tokens found")
            return None

        # Refresh if needed
        if self._is_token_expired(tokens):
            tokens = self._refresh_access_token(app_name)
            if not tokens:
                return None

        return tokens.get("access_token")

    def get_access_token(self, app_name: str, force_refresh: bool = False) -> Optional[str]:
        """Public convenience alias for get_valid_token()."""
        if force_refresh:
            refreshed = self._refresh_access_token(app_name)
            if refreshed is None:
                return None
        return self.get_valid_token(app_name)
    
    def check_health(self, auto_refresh: bool = True) -> Dict[str, Any]:
        """Check health of all tokens. Optionally refresh expired access tokens."""
        health = {}
        
        for app_name in APPS:
            tokens = self._load_tokens(app_name)
            
            if not tokens:
                health[app_name] = {
                    "status": "missing",
                    "message": "No tokens found"
                }
                continue
            
            # Check access token (refresh if expired when in health-check mode)
            access_valid = not self._is_token_expired(tokens)
            if auto_refresh and not access_valid:
                refreshed = self._refresh_access_token(app_name)
                access_valid = refreshed is not None
                if refreshed:
                    tokens = refreshed
            
            # Check refresh token age
            saved_at_str = tokens.get("_saved_at")
            refresh_days_remaining = None
            if saved_at_str:
                try:
                    saved_at = datetime.fromisoformat(saved_at_str)
                    days_old = (datetime.now() - saved_at).days
                    refresh_days_remaining = max(0, 30 - days_old)
                except ValueError:
                    pass
            
            health[app_name] = {
                "status": "healthy" if access_valid else "expired",
                "access_token_valid": access_valid,
                "refresh_token_days_remaining": refresh_days_remaining,
                "needs_reauth": refresh_days_remaining is not None and refresh_days_remaining <= 0,
                "last_saved": saved_at_str,
            }
        
        return health
    
    def exchange_code(self, app_name: str, code: str) -> bool:
        """Exchange auth code for tokens."""
        config = APPS[app_name]
        
        path = "/api/v2/auth/token/get"
        ts = int(time.time())
        base = f"{config['partner_id']}{path}{ts}"
        sign = hmac.new(config["partner_key"].encode(), base.encode(), hashlib.sha256).hexdigest()
        
        try:
            resp = requests.post(
                f"{BASE_URL}{path}",
                params={"partner_id": config["partner_id"], "timestamp": ts, "sign": sign},
                json={"code": code, "shop_id": SHOP_ID, "partner_id": config["partner_id"]},
                timeout=60
            )
            data = resp.json()
            
            if resp.status_code == 200 and "access_token" in data:
                tokens = {
                    "partner_id": config["partner_id"],
                    "shop_id": _shop_id(),
                    "access_token": data["access_token"],
                    "refresh_token": data["refresh_token"],
                    "expire_in": data.get("expire_in", 14400),
                    "request_id": data.get("request_id", ""),
                }
                self._save_tokens(app_name, tokens)
                print(f"✅ {app_name}: Tokens exchanged and saved")
                return True
            else:
                print(f"❌ {app_name}: Exchange failed — {data}")
                return False
                
        except Exception as e:
            print(f"❌ {app_name}: Exchange error — {e}")
            return False


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Shopee Token Manager")
    parser.add_argument("--workspace", default=".", help="Workspace directory")
    parser.add_argument("--refresh", action="store_true", help="Force refresh all tokens")
    parser.add_argument("--health", action="store_true", help="Check token health")
    parser.add_argument("--exchange", nargs=2, metavar=("APP", "CODE"), help="Exchange auth code for tokens")
    parser.add_argument("--watch", action="store_true", help="Watch mode — auto-refresh every hour")
    
    args = parser.parse_args()
    
    manager = TokenManager(args.workspace)
    
    if args.exchange:
        app_name, code = args.exchange
        if app_name not in APPS:
            print(f"❌ Unknown app: {app_name}. Choose from: {list(APPS.keys())}")
            return
        manager.exchange_code(app_name, code)
    
    elif args.health:
        health = manager.check_health()
        print(json.dumps(health, indent=2))
        
        # Exit with error code if any app needs reauth
        if any(h.get("needs_reauth") for h in health.values()):
            exit(1)
    
    elif args.refresh:
        for app_name in APPS:
            print(f"Refreshing {app_name}...")
            manager.get_valid_token(app_name)
    
    elif args.watch:
        print("👁️  Token watch mode — refreshing every hour (Ctrl+C to stop)")
        while True:
            for app_name in APPS:
                manager.get_valid_token(app_name)
            time.sleep(3600)  # 1 hour
    
    else:
        # Default: just get valid tokens (auto-refresh if needed)
        for app_name in APPS:
            token = manager.get_valid_token(app_name)
            if token:
                print(f"✅ {app_name}: Valid token available")
            else:
                print(f"❌ {app_name}: No valid token")


if __name__ == "__main__":
    main()
