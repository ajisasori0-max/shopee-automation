from commerceos.shared.value_objects.primitives import utc_now
"""Obsidian reporter for Event Bus."""

from datetime import datetime, timezone
from typing import Any, Dict, List


def format_daily_report(events: List[Dict[str, Any]], workflows: List[Dict[str, Any]], dead_letters: List[Dict[str, Any]]) -> str:
    now = utc_now().isoformat()
    lines = [
        "# Daily Workflow Report",
        "",
        f"Generated: {now}",
        "",
        f"## Events ({len(events)})",
    ]
    for e in events:
        lines.append(f"- {e['status']}: {e['event_type']} ({e['aggregate_type']}:{e['aggregate_id']}) — attempts {e['attempt_count']}")
    lines.append("")
    lines.append(f"## Workflows ({len(workflows)})")
    for w in workflows:
        duration = ""
        if w.get("started_at") and w.get("completed_at"):
            try:
                start = datetime.fromisoformat(w["started_at"])
                end = datetime.fromisoformat(w["completed_at"])
                duration = f" — duration {(end - start).total_seconds():.1f}s"
            except Exception:
                pass
        lines.append(f"- {w['status']}: {w['workflow_name']} ({w['id']}) — retries {w['retry_count']}{duration}")
    lines.append("")
    lines.append(f"## Dead Letters ({len(dead_letters)})")
    for d in dead_letters:
        lines.append(f"- {d['event_id']}: {d['reason']} (retry_allowed={d['retry_allowed']})")
    return "\n".join(lines)


def write_daily_report(path: str, events: List[Dict[str, Any]], workflows: List[Dict[str, Any]], dead_letters: List[Dict[str, Any]]) -> str:
    content = format_daily_report(events, workflows, dead_letters)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
