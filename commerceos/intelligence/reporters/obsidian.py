"""Obsidian intelligence report generator."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from commerceos.intelligence.constants import InsightCategory
from commerceos.shared.value_objects.primitives import utc_now


DEFAULT_OBSIDIAN_DIR = Path.home() / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "Gerard" / "Business Intelligence"


class ObsidianIntelligenceReport:
    """Write Daily Business Intelligence.md to Obsidian."""

    def __init__(self, vault_dir: Optional[Path] = None):
        self.vault_dir = vault_dir or DEFAULT_OBSIDIAN_DIR

    def _ensure_dir(self) -> None:
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    def write_daily_report(
        self,
        overall_severity: str,
        insights: List[Dict[str, Any]],
        trend_summary: List[Dict[str, Any]],
        business_summary: Dict[str, Any],
    ) -> Path:
        self._ensure_dir()
        today = utc_now().strftime("%Y-%m-%d")
        filename = f"Daily Business Intelligence {today}.md"
        path = self.vault_dir / filename

        by_category = {}
        for i in insights:
            by_category.setdefault(i["category"], []).append(i)

        lines = [
            f"# Daily Business Intelligence — {today}",
            "",
            f"**Overall Severity:** {overall_severity}",
            f"**Generated:** {utc_now().isoformat()}",
            f"**Total Insights:** {len(insights)}",
            "",
            "## Priority Insights",
        ]
        for i in insights[:10]:
            lines.append(f"- **[{i['severity']}] {i['title']}**")
            lines.append(f"  {i['explanation']}")

        lines.extend(["", "## Revenue"])
        for i in by_category.get(InsightCategory.REVENUE.value, []):
            lines.append(f"- {i['title']}: {i['explanation']}")

        lines.extend(["", "## Profit"])
        for i in by_category.get(InsightCategory.PROFIT.value, []):
            lines.append(f"- {i['title']}: {i['explanation']}")

        lines.extend(["", "## Advertising"])
        for i in by_category.get(InsightCategory.ADVERTISING.value, []):
            lines.append(f"- {i['title']}: {i['explanation']}")

        lines.extend(["", "## Inventory"])
        for i in by_category.get(InsightCategory.INVENTORY.value, []):
            lines.append(f"- {i['title']}: {i['explanation']}")
        if InsightCategory.INVENTORY.value not in by_category:
            lines.append("- No inventory insights today.")

        lines.extend(["", "## Operations"])
        for i in by_category.get(InsightCategory.OPERATIONS.value, []):
            lines.append(f"- {i['title']}: {i['explanation']}")

        lines.extend(["", "## Key Changes"])
        for t in trend_summary[:10]:
            delta = t.get("delta_pct")
            if delta is not None:
                lines.append(f"- {t['metric']} ({t['period']}): {delta:+.1f}%")

        lines.extend(["", "## Trend Summary"])
        for t in trend_summary:
            lines.append(f"- {t['metric']} ({t['period']}): current={t['value']}, baseline={t['baseline']}, delta={t['delta_pct']:.1f}%" if t.get('delta_pct') is not None else f"- {t['metric']} ({t['period']}): N/A")

        lines.extend(["", "## Open Risks"])
        risks = [i for i in insights if i["severity"] in ("high", "critical")]
        if risks:
            for i in risks:
                lines.append(f"- {i['title']}: {i['explanation']}")
        else:
            lines.append("- No high/critical risks identified.")

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
