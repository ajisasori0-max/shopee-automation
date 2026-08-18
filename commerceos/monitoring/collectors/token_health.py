"""Token / secret health collector.

Checks token expiry, refresh window, and missing required secrets.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from commerceos.monitoring.constants import Component, HealthStatus, Severity
from commerceos.monitoring.evaluators.freshness import hours_since
from commerceos.monitoring.models import HealthCheck
from commerceos.platform.secrets import SecretManager, workspace_secret_manager
from commerceos.platform import secrets_schema as secrets


REQUIRED_SECRET_NAMES = [
    secrets.STORE_SHOPEE_SHOP_ID,
    secrets.SHOPEE_PRODUCTION_PARTNER_ID,
    secrets.SHOPEE_PRODUCTION_PARTNER_KEY,
    secrets.SHOPEE_ADS_PARTNER_ID,
    secrets.SHOPEE_ADS_PARTNER_KEY,
]

TOKEN_SECRET_NAMES = [
    secrets.SHOPEE_PRODUCTION_TOKENS,
    secrets.SHOPEE_ADS_TOKENS,
]


def _parse_token_data(token_json: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse token JSON and compute both access and refresh token expiries."""
    if not token_json:
        return None
    try:
        import json
        data = json.loads(token_json)
        saved_at = data.get("_saved_at")
        refresh_token = data.get("refresh_token")
        expire_in = data.get("expire_in")
        if not saved_at or not refresh_token:
            return None
        saved = datetime.fromisoformat(saved_at)
        if saved.tzinfo is None:
            saved = saved.replace(tzinfo=timezone.utc)

        # Access token expiry: saved_at + expire_in (typically 4 hours)
        access_expiry = saved + timedelta(seconds=expire_in) if expire_in else None

        # Refresh token expiry: Shopee refresh tokens last 30 days from auth time.
        # If we have refresh_token_expiry saved, use it; otherwise assume 30 days from saved_at.
        refresh_expiry = data.get("refresh_token_expiry")
        if refresh_expiry:
            refresh_expiry_dt = datetime.fromisoformat(refresh_expiry)
            if refresh_expiry_dt.tzinfo is None:
                refresh_expiry_dt = refresh_expiry_dt.replace(tzinfo=timezone.utc)
        else:
            refresh_expiry_dt = saved + timedelta(days=30)

        return {
            "access_expiry": access_expiry,
            "refresh_expiry": refresh_expiry_dt,
        }
    except Exception:
        return None


def collect_token_health(
    secret_manager: Optional[SecretManager] = None,
    now: Optional[datetime] = None,
) -> List[HealthCheck]:
    """Collect secret/token health checks."""
    now = now or utc_now()
    checks: List[HealthCheck] = []
    sm = secret_manager or workspace_secret_manager()

    # Missing required secrets
    missing = [name for name in REQUIRED_SECRET_NAMES if not sm.exists(name)]
    checks.append(
        HealthCheck(
            component=Component.TOKEN_MANAGER.value,
            component_instance="global",
            check_type="missing_secrets",
            status=HealthStatus.HEALTHY.value if not missing else HealthStatus.UNHEALTHY.value,
            severity=Severity.INFO.value if not missing else Severity.CRITICAL.value,
            message=f"Missing required secrets: {missing}" if missing else "All required secrets present",
            checked_at=now,
            metadata_={"missing_secrets": missing, "required_count": len(REQUIRED_SECRET_NAMES)},
        )
    )

    # Token expiry for each token secret
    for token_name in TOKEN_SECRET_NAMES:
        token_type = token_name.split("/")[1]  # e.g. shopee/production/tokens_json -> production
        token_json = sm.get(token_name)
        parsed = _parse_token_data(token_json)

        if parsed is None:
            checks.append(
                HealthCheck(
                    component=Component.TOKEN_MANAGER.value,
                    component_instance=token_type,
                    check_type="token_expiry",
                    status=HealthStatus.UNHEALTHY.value,
                    severity=Severity.CRITICAL.value,
                    message=f"No valid token data for {token_type}",
                    checked_at=now,
                    metadata_={"token_type": token_type},
                )
            )
            continue

        refresh_expiry = parsed["refresh_expiry"]
        refresh_hours = hours_since(refresh_expiry, now)
        refresh_days = refresh_hours / 24 if refresh_hours is not None else None

        # Access token freshness is informational; auto-refresh handles it.
        access_expiry = parsed["access_expiry"]
        access_hours = hours_since(access_expiry, now) if access_expiry else None

        if refresh_hours is not None and refresh_hours >= 0:
            status = HealthStatus.UNHEALTHY
            severity = Severity.CRITICAL
            message = f"{token_type} refresh token expired {refresh_hours:.1f}h ago — re-authorize required"
        elif refresh_days is not None and refresh_days >= -7:
            status = HealthStatus.DEGRADED
            severity = Severity.WARNING
            message = f"{token_type} refresh token expires in {-refresh_days:.1f} days"
        else:
            status = HealthStatus.HEALTHY
            severity = Severity.INFO
            message = f"{token_type} refresh token valid for {-refresh_days:.1f} days" if refresh_days is not None else f"{token_type} token expiry unknown"

        checks.append(
            HealthCheck(
                component=Component.TOKEN_MANAGER.value,
                component_instance=token_type,
                check_type="token_expiry",
                status=status.value,
                severity=severity.value,
                message=message,
                checked_at=now,
                metadata_={
                    "token_type": token_type,
                    "refresh_expiry": refresh_expiry.isoformat() if refresh_expiry else None,
                    "refresh_days_remaining": -refresh_days if refresh_days is not None and refresh_days < 0 else 0,
                    "access_expiry": access_expiry.isoformat() if access_expiry else None,
                    "access_hours_remaining": -access_hours if access_hours is not None and access_hours < 0 else 0,
                },
            )
        )

    return checks
