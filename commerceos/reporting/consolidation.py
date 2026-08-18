"""Reporting consolidation inventory.

Lists duplicate reporting paths and marks the canonical path. This file is not
loaded by code; it is documentation for WP4.4.
"""

from typing import Dict, List


REPORT_INVENTORY: List[Dict[str, str]] = [
    {
        "name": "Daily COO Brief",
        "source": "Knowledge layer",
        "path": "commerceos/knowledge/reporters/coo_brief_generator.py",
        "output": "Obsidian vault: 10 COO/Daily/",
        "telegram": "scripts/send_morning_brief.py",
        "status": "canonical",
    },
    {
        "name": "Weekly Business Review",
        "source": "Knowledge layer",
        "path": "commerceos/knowledge/reporters/coo_brief_generator.py",
        "output": "Obsidian vault: 10 COO/Weekly/",
        "telegram": "scripts/send_morning_brief.py (uses latest weekly if available)",
        "status": "canonical",
    },
    {
        "name": "Daily Business Intelligence",
        "source": "Intelligence layer (legacy)",
        "path": "commerceos/intelligence/reporters/obsidian.py",
        "output": "Obsidian: Business Intelligence/ (legacy vault)",
        "telegram": "commerceos/intelligence/reporters/telegram.py",
        "status": "deprecated - superseded by Knowledge layer daily brief",
    },
    {
        "name": "Daily Operations Health",
        "source": "Monitoring layer (legacy)",
        "path": "commerceos/monitoring/notifiers/obsidian.py",
        "output": "Obsidian: Daily Operations/ (legacy vault)",
        "telegram": "commerceos/monitoring/reporters/telegram.py (if exists)",
        "status": "deprecated - superseded by Knowledge layer daily brief",
    },
    {
        "name": "Morning Decision Brief",
        "source": "Decision layer (legacy)",
        "path": "commerceos/decision/reporters/telegram.py",
        "output": "Telegram only",
        "telegram": "commerceos/decision/reporters/telegram.py",
        "status": "deprecated - superseded by send_morning_brief.py",
    },
    {
        "name": "Daily Execution Summary",
        "source": "Execution layer (legacy)",
        "path": "commerceos/execution/reporters/telegram.py",
        "output": "Telegram only",
        "telegram": "commerceos/execution/reporters/telegram.py",
        "status": "deprecated - superseded by send_evening_review.py",
    },
    {
        "name": "Daily Workflow Summary",
        "source": "Events layer (legacy)",
        "path": "commerceos/events/reporters/telegram.py",
        "output": "Telegram only",
        "telegram": "commerceos/events/reporters/telegram.py",
        "status": "deprecated - superseded by send_evening_review.py",
    },
    {
        "name": "Midday / Evening / Growth checks",
        "source": "Legacy scripts",
        "path": "archive/legacy_scripts/daily_monitor.py, evening_check.py, midday_check.py, growth_engine.py, send_*.py",
        "output": "various files, Telegram",
        "telegram": "legacy send_*.py scripts (archived)",
        "status": "deprecated - migrate to operational jobs",
    },
    {
        "name": "Monthly Financial Report",
        "source": "Financial engine (legacy)",
        "path": "archive/legacy_scripts/financial_engine.py, monthly_report.py",
        "output": "Excel / JSON",
        "telegram": "archive/legacy_scripts/send_growth_report.py",
        "status": "deprecated - migrate to Knowledge layer monthly executive review",
    },
]


def deprecated_paths() -> List[str]:
    """Return deprecated reporting paths."""
    return [
        p["path"]
        for p in REPORT_INVENTORY
        if p["status"].startswith("deprecated")
    ]


def canonical_paths() -> List[str]:
    """Return canonical reporting paths."""
    return [
        p["path"]
        for p in REPORT_INVENTORY
        if p["status"].startswith("canonical")
    ]
