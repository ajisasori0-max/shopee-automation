"""Telegram reporter for Event Bus."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from commerceos.events.constants import WorkflowJobStatus
from commerceos.shared.value_objects.primitives import utc_now


def _status_emoji(status: str) -> str:
    return {
        WorkflowJobStatus.QUEUED.value: "🟡",
        WorkflowJobStatus.RUNNING.value: "🔄",
        WorkflowJobStatus.SUCCEEDED.value: "✅",
        WorkflowJobStatus.FAILED.value: "❌",
        WorkflowJobStatus.RETRYING.value: "🔁",
        WorkflowJobStatus.CANCELLED.value: "🚫",
    }.get(status, "•")


def format_daily_workflow_summary(summary: Dict[str, Any]) -> str:
    lines = [
        "📡 *Daily Workflow Summary*",
        "",
        f"_{utc_now().isoformat()}_",
        "",
    ]
    events = summary.get("events", {})
    workflows = summary.get("workflows", {})
    dead_letters = summary.get("dead_letters", 0)
    lines.append(f"Events: {events.get('total', 0)}")
    for status, count in (events.get("by_status") or {}).items():
        lines.append(f"  {status}: {count}")
    lines.append("")
    lines.append(f"Workflows: {workflows.get('total', 0)}")
    for status, count in (workflows.get("by_status") or {}).items():
        emoji = _status_emoji(status)
        lines.append(f"  {emoji} {status}: {count}")
    lines.append("")
    if dead_letters:
        lines.append(f"🚨 Dead letters: {dead_letters}")
    else:
        lines.append("No dead letters.")
    return "\n".join(lines)


def format_failed_workflow(job: Dict[str, Any]) -> str:
    return (
        f"❌ *Workflow Failed*\n\n"
        f"Job: {job['id']}\n"
        f"Workflow: {job['workflow_name']}\n"
        f"Retries: {job['retry_count']}\n"
        f"Failed: {utc_now().isoformat()}"
    )


def format_dead_letter_notification(entry: Dict[str, Any]) -> str:
    return (
        f"🚨 *Dead Letter Event*\n\n"
        f"Event: {entry['event_id']}\n"
        f"Reason: {entry['reason']}\n"
        f"Retry allowed: {entry['retry_allowed']}\n"
        f"Failed: {entry['failed_at']}"
    )


def format_event_processed(event: Dict[str, Any]) -> str:
    return (
        f"📨 *Event Processed*\n\n"
        f"Type: {event['event_type']}\n"
        f"Aggregate: {event['aggregate_type']}:{event['aggregate_id']}\n"
        f"Status: {event['status']}\n"
        f"Attempts: {event['attempt_count']}"
    )
