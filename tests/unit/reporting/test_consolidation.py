"""Tests for reporting consolidation."""

from commerceos.reporting.consolidation import REPORT_INVENTORY, canonical_paths, deprecated_paths
from commerceos.reporting.router import get_latest_canonical_report


def test_inventory_has_canonical_and_deprecated():
    canonical = canonical_paths()
    deprecated = deprecated_paths()
    assert canonical
    assert deprecated
    assert len(canonical) + len(deprecated) == len(REPORT_INVENTORY)


def test_daily_report_is_canonical():
    daily = next(p for p in REPORT_INVENTORY if p["name"] == "Daily COO Brief")
    assert daily["status"].startswith("canonical")
    assert "knowledge" in daily["source"].lower()


def test_legacy_intelligence_report_is_deprecated():
    legacy = next(p for p in REPORT_INVENTORY if p["name"] == "Daily Business Intelligence")
    assert legacy["status"].startswith("deprecated")


def test_router_returns_none_for_empty_database(monkeypatch):
    # Ensure no real DB call is made; the router opens a new session.
    # Use a throwaway DB URL so the in-memory SQLite returns nothing quickly.
    import os

    from commerceos.config.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", "sqlite:///test_router_empty.db")
    if os.path.exists("test_router_empty.db"):
        os.remove("test_router_empty.db")
    result = get_latest_canonical_report("daily", settings=settings)
    assert result is None
    if os.path.exists("test_router_empty.db"):
        os.remove("test_router_empty.db")
