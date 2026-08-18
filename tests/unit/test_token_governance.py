"""Regression tests for token governance.

Only token_manager.py is allowed to refresh or write tokens_*.json.
Any other module that does so is a regression.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent

FORBIDDEN_PATTERNS = [
    ("direct_token_write", re.compile(r"with open\([^)]*tokens_(production|ads)\.json['\"],\s*['\"]w")),
    ("direct_token_dump", re.compile(r"json\.dump\([^)]*tokens_(production|ads)\.json")),
    ("internal_save_tokens", re.compile(r"_save_tokens\(")),
    ("shopee_refresh_endpoint", re.compile(r"/api/v2/auth/access_token/get")),
]

ALLOWED_FILES = {"token_manager.py"}


def _iter_source_files():
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        parts = rel.parts
        if "archive" in parts or "tests" in parts or path.name in ALLOWED_FILES:
            continue
        yield path


@pytest.mark.parametrize("pattern_name,pattern", FORBIDDEN_PATTERNS)
def test_no_unauthorized_token_management(pattern_name, pattern):
    violations = []
    for path in _iter_source_files():
        text = path.read_text(errors="ignore")
        if pattern.search(text):
            violations.append(path.relative_to(ROOT))

    assert not violations, (
        f"Forbidden token-management pattern '{pattern_name}' found in: "
        f"{', '.join(str(v) for v in violations)}"
    )
