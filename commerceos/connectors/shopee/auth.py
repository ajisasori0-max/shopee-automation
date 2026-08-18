from typing import Any, Dict, Optional

from commerceos.connectors.core.interfaces import ConnectorAuth, ConnectorResult
from commerceos.platform.secrets import SecretManager, workspace_secret_manager
from commerceos.platform import secrets_schema as secrets
from commerceos.platform.tokens import get_access_token, app_name_for_partner_id


class ShopeeAuth(ConnectorAuth):
    """Shopee-specific authentication using SecretManager.

    Expected secrets are namespaced per store:
    - shopee/{store_id}/partner_id
    - shopee/{store_id}/partner_key

    As a fallback for the single production store, canonical app credentials are
    used when per-store secrets are not present.
    """

    def __init__(self, store_id: str, secret_manager: Optional[SecretManager] = None):
        self.store_id = store_id
        self.secret_manager = secret_manager or workspace_secret_manager()

    def _secret_name(self, key: str) -> str:
        return f"shopee/{self.store_id}/{key}"

    def _get(self, name: str) -> Optional[str]:
        return self.secret_manager.get(self._secret_name(name))

    def get_credentials(self) -> Dict[str, Any]:
        partner_id = self._get("partner_id") or self.secret_manager.get(secrets.SHOPEE_PRODUCTION_PARTNER_ID)
        partner_key = self._get("partner_key") or self.secret_manager.get(secrets.SHOPEE_PRODUCTION_PARTNER_KEY)
        access_token = None
        if partner_id:
            try:
                access_token = get_access_token(app_name_for_partner_id(partner_id))
            except Exception:
                pass
        return {
            "partner_id": partner_id,
            "partner_key": partner_key,
            "shop_id": self.store_id,
            "access_token": access_token,
            "refresh_token": None,
        }

    def refresh(self) -> ConnectorResult:
        # Token refresh will be implemented in E1.3
        return ConnectorResult.failed(
            "Shopee token refresh is not yet implemented",
            error_code="not_implemented",
        )

    @property
    def is_authenticated(self) -> bool:
        creds = self.get_credentials()
        return all(
            [
                creds.get("partner_id"),
                creds.get("partner_key"),
                creds.get("shop_id"),
            ]
        )

    def get_access_token(self) -> Optional[str]:
        return self._get("access_token")

    def get_partner_key(self) -> Optional[str]:
        return self._get("partner_key")

    def get_partner_id(self) -> Optional[str]:
        return self._get("partner_id")

    def get_refresh_token(self) -> Optional[str]:
        return self._get("refresh_token")
