"""Central token provider for CommerceOS.

This module is the SINGLE supported path for obtaining Shopee access tokens.
Only ``token_manager.py`` is allowed to refresh or write token files. Every
other module/script should call ``get_access_token()`` here.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from token_manager import TokenManager, APPS  # noqa: E402
from commerceos.platform import secrets_schema as secrets
from commerceos.platform.secrets import workspace_secret_manager

_TOKEN_MANAGER: Optional[TokenManager] = None


def _manager() -> TokenManager:
    global _TOKEN_MANAGER
    if _TOKEN_MANAGER is None:
        _TOKEN_MANAGER = TokenManager(str(WORKSPACE))
    return _TOKEN_MANAGER


def get_access_token(app_name: str, force_refresh: bool = False) -> Optional[str]:
    """Return a valid access token for ``app_name`` (production or ads).

    This delegates to ``token_manager.py`` — the only component that refreshes
    or writes token files.
    """
    if app_name not in APPS:
        raise ValueError(f"Unknown app: {app_name}. Valid: {list(APPS.keys())}")
    return _manager().get_access_token(app_name, force_refresh=force_refresh)


def _app_partner_ids() -> dict[str, int]:
    sm = workspace_secret_manager()
    return {
        "production": int(sm.get_required(secrets.SHOPEE_PRODUCTION_PARTNER_ID)),
        "ads": int(sm.get_required(secrets.SHOPEE_ADS_PARTNER_ID)),
    }


def app_name_for_partner_id(partner_id: int | str) -> str:
    pid = int(partner_id)
    for app_name, app_pid in _app_partner_ids().items():
        if app_pid == pid:
            return app_name
    raise ValueError(f"Unknown partner_id: {partner_id}")


def refresh_all() -> dict:
    """Force-refresh both token sets. Used by orchestrators before a sync run."""
    return {
        app_name: _manager().get_access_token(app_name, force_refresh=True)
        for app_name in APPS
    }
