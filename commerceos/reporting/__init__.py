"""Reporting package for CommerceOS."""

from commerceos.reporting.consolidation import REPORT_INVENTORY, canonical_paths, deprecated_paths
from commerceos.reporting.router import get_latest_canonical_report, get_report_content

__all__ = [
    "REPORT_INVENTORY",
    "canonical_paths",
    "deprecated_paths",
    "get_latest_canonical_report",
    "get_report_content",
]
