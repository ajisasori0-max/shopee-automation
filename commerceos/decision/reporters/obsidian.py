from commerceos.shared.value_objects.primitives import utc_now
"""Obsidian reporter for daily decision reports."""

from datetime import datetime, timezone
from typing import Any, Dict, List


def format_daily_report(decisions: List[Dict[str, Any]]) -> str:
    """Generate Markdown for the Daily Decision Report."""
    now = utc_now().isoformat()
    lines = [
        "# Daily Decision Report",
        "",
        f"Generated: {now}",
        "",
    ]

    if not decisions:
        lines.append("No open recommendations today.")
        return "\n".join(lines)

    lines.append(f"## Open Recommendations ({len(decisions)})")
    lines.append("")
    for d in decisions:
        impact = d.get("expected_impact", {})
        lines.append(f"### {d['severity'].upper()}: {d['title']}")
        lines.append("")
        lines.append(f"- **Category:** {d['category']}")
        lines.append(f"- **Status:** {d['status']}")
        lines.append(f"- **Confidence:** {d.get('confidence', 'medium')}")
        lines.append(f"- **Description:** {d['description']}")
        lines.append(f"- **Rationale:** {d['rationale']}")
        lines.append(f"- **Recommended Action:** {d['recommended_action']}")
        lines.append("")
        lines.append("#### Expected Impact")
        lines.append(f"- Revenue: {impact.get('expected_revenue_change')}")
        lines.append(f"- Profit: {impact.get('expected_profit_change')}")
        lines.append(f"- Cash: {impact.get('expected_cash_change')}")
        if impact.get("explanation"):
            lines.append(f"- Explanation: {impact['explanation']}")
        lines.append("")
        if d.get("evidence"):
            lines.append("#### Evidence")
            for e in d["evidence"]:
                lines.append(f"- {e['source_type']}: {e['description']}")
            lines.append("")

    return "\n".join(lines)


def write_daily_report(path: str, decisions: List[Dict[str, Any]]) -> str:
    """Write the daily report to a file and return the path."""
    content = format_daily_report(decisions)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
