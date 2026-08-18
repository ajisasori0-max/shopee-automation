from commerceos.shared.value_objects.primitives import utc_now
"""Obsidian reporter for Execution Engine."""

from datetime import datetime, timezone
from typing import Any, Dict, List


def format_daily_report(plans: List[Dict[str, Any]]) -> str:
    """Generate Markdown for the Daily Execution Report."""
    now = utc_now().isoformat()
    lines = [
        "# Daily Execution Report",
        "",
        f"Generated: {now}",
        "",
    ]

    if not plans:
        lines.append("No executions today.")
        return "\n".join(lines)

    lines.append(f"## Executions ({len(plans)})")
    lines.append("")
    for p in plans:
        lines.append(f"### {p['status'].upper()}: {p['action_type']} ({p['id']})")
        lines.append("")
        lines.append(f"- **Decision ID:** {p['decision_id']}")
        lines.append(f"- **Status:** {p['status']}")
        lines.append(f"- **Checksum:** {p.get('checksum')}")
        lines.append(f"- **Created:** {p.get('created_at')}")
        lines.append(f"- **Started:** {p.get('started_at')}")
        lines.append(f"- **Completed:** {p.get('completed_at')}")
        lines.append(f"- **Expires:** {p.get('expires_at')}")
        if p.get("payload"):
            lines.append("")
            lines.append("#### Payload")
            payload = p["payload"]
            lines.append(f"- Target: {payload.get('target_entity')}")
            lines.append(f"- Parameters: {payload.get('parameters')}")
            lines.append(f"- Expected outcome: {payload.get('expected_outcome')}")
            lines.append(f"- Rollback strategy: {payload.get('rollback_strategy')}")
        if p.get("steps"):
            lines.append("")
            lines.append("#### Steps")
            for s in p["steps"]:
                emoji = "✅" if s["status"] == "succeeded" else "❌" if s["status"] == "failed" else "↩️"
                lines.append(f"- {emoji} Step {s['step_number']}: {s['action']} → {s['status']}")
                if s.get("result"):
                    lines.append(f"  - Result: {s['result']}")
                if s.get("error"):
                    lines.append(f"  - Error: {s['error']}")
        if p.get("audit"):
            lines.append("")
            lines.append("#### Audit Events")
            for a in p["audit"]:
                lines.append(f"- {a['timestamp']} — {a['event']} (actor: {a.get('actor', 'system')})")
        lines.append("")

    return "\n".join(lines)


def write_daily_report(path: str, plans: List[Dict[str, Any]]) -> str:
    content = format_daily_report(plans)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
