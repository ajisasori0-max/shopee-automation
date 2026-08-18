"""WP2.1 secret-governance regression test.

Only token_manager.py and scripts/migrate_secrets.py are allowed to:
- handle raw partner keys / numeric partner/shop/chat IDs,
- refresh Shopee OAuth tokens,
- write tokens_*.json, or
- load secrets from JSON files.

Any other active production file doing these things is a regression.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent

# Active production scope as defined by WP2.1.
# Root files listed explicitly; commerceos/ and scripts/ recursively.
ACTIVE_ROOT_FILES = {
    "token_manager.py",
    "automation.py",
    "shopee_monitor.py",
    "app.py",
    "streamlit_app.py",
    "generate_auth_url.py",
    "pause_non_hero_campaigns.py",
    "update_roas_targets.py",
}

LEGACY_ROOT_FILES = {
    "apply_approved.py",
    "auto_optimizer.py",
    "daily_monitor.py",
    "evening_check.py",
    "financial_engine.py",
    "full_automation.py",
    "growth_engine.py",
    "midday_check.py",
    "monthly_report.py",
    "semi_auto_optimizer.py",
    "send_evening_check.py",
    "send_growth_report.py",
    "send_midday_check.py",
    "shopee_client.py",
    "simple_optimizer.py",
}

ALLOWED_SECRET_HANDLERS = {
    "token_manager.py",
    "scripts/migrate_secrets.py",
}

FORBIDDEN_PATTERNS = [
    ("hardcoded_partner_key", re.compile(r"shpk[0-9a-fA-F]{32,}")),
    ("hardcoded_partner_id", re.compile(r"partner_id\s*=\s*[\"']?\d+[\"']?")),
    ("hardcoded_shop_id", re.compile(r"shop_id\s*=\s*[\"']?\d+[\"']?")),
    ("hardcoded_chat_id", re.compile(r"chat_id\s*=\s*[\"']?\d+[\"']?")),
    (
        "direct_token_file_write",
        re.compile(r"open\([^)]*tokens_(production|ads)\.json['\"],\s*['\"]w"),
    ),
    ("shopee_refresh_endpoint", re.compile(r"/api/v2/auth/access_token/get")),
    ("json_load_secrets", re.compile(r"json\.load\(.*(?:openclaw|tokens_|secrets)"),),
]


def _is_excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts

    if "__pycache__" in parts or ".pytest_cache" in parts:
        return True

    if "tests" in parts or "archive" in parts:
        return True

    name = path.name
    if name.startswith(("debug_", "check_", "test_", "auth_", "demo_", "send_")):
        return True

    if str(rel) in ALLOWED_SECRET_HANDLERS:
        return True

    return False


def _iter_active_source_files():
    for path in ROOT.rglob("*.py"):
        if _is_excluded(path):
            continue

        rel = path.relative_to(ROOT)
        parts = rel.parts

        if parts[0] == "commerceos":
            yield path
        elif parts[0] == "scripts":
            # scripts/migrate_secrets.py already excluded above
            yield path
        elif path.name in ACTIVE_ROOT_FILES:
            yield path


@pytest.mark.parametrize("pattern_name,pattern", FORBIDDEN_PATTERNS)
def test_no_forbidden_secret_patterns_in_active_code(pattern_name, pattern):
    violations = []
    for path in _iter_active_source_files():
        text = path.read_text(errors="ignore")
        if pattern.search(text):
            violations.append(path.relative_to(ROOT))

    assert not violations, (
        f"Forbidden WP2.1 pattern '{pattern_name}' found in active production code: "
        f"{', '.join(str(v) for v in violations)}"
    )


def test_allowed_secret_handlers_explicitly_exempt():
    """Sanity check: the two allowed files are still present and not accidentally scanned."""
    for handler in ALLOWED_SECRET_HANDLERS:
        assert (ROOT / handler).exists(), f"Allowed secret handler missing: {handler}"
