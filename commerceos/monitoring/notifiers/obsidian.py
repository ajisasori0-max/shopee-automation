"""Obsidian reporter for the monitoring layer.

Writes a Daily Operations Health note to the configured Obsidian vault directory.
"""
from commerceos.shared.value_objects.primitives import utc_now

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from commerceos.monitoring.constants import AlertStatus, Severity
from commerceos.monitoring.models import Alert


DEFAULT_OBSIDIAN_DIR = Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "Gerard" / "Daily Operations"


class ObsidianReporter:
    """Write machine-generated operations health notes to Obsidian."""

    def __init__(self, vault_dir: Optional[Path] = None):
        self.vault_dir = vault_dir or DEFAULT_OBSIDIAN_DIR

    def _ensure_dir(self) -> None:
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    def write_daily_report(
        self,
        overall_status: str,
        open_alerts: List[Alert],
        failed_jobs: List[str],
        freshness: dict,
        data_quality_score: Optional[float],
        top_risks: List[str],
    ) -> Path:
        """Write Daily Operations Health.md and return the path."""
        self._ensure_dir()
        today = utc_now().strftime("%Y-%m-%d")
        filename = f"Daily Operations Health {today}.md"
        path = self.vault_dir / filename

        critical = [a for a in open_alerts if a.severity == Severity.CRITICAL.value]
        warnings = [a for a in open_alerts if a.severity == Severity.WARNING.value]

        lines = [
            f"# Daily Operations Health — {today}",
            "",
            f"**Overall Health:** {overall_status}",
            f"**Generated:** {utc_now().isoformat()}",
            "",
            "## Open Alerts",
            f"- Critical: {len(critical)}",
            f"- Warning: {len(warnings)}",
        ]
        if critical:
            lines.append("")
            lines.append("### Critical")
            for a in critical:
                lines.append(f"- {a.title}: {a.description}")
        if warnings:
            lines.append("")
            lines.append("### Warnings")
            for a in warnings:
                lines.append(f"- {a.title}: {a.description}")

        lines.extend([
            "",
            "## Failed Jobs",
        ])
        if failed_jobs:
            for job in failed_jobs:
                lines.append(f"- {job}")
        else:
            lines.append("- None")

        lines.extend([
            "",
            "## Freshness",
        ])
        for component, status in freshness.items():
            lines.append(f"- {component}: {status}")

        lines.extend([
            "",
            "## Data Quality",
            f"- Score: {data_quality_score:.2f}" if data_quality_score is not None else "- Score: N/A",
        ])

        lines.extend([
            "",
            "## Top Risks",
        ])
        if top_risks:
            for risk in top_risks:
                lines.append(f"- {risk}")
        else:
            lines.append("- No top risks identified")

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
