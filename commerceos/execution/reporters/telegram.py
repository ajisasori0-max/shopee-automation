"""Telegram reporter for Execution Engine."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from commerceos.execution.constants import ExecutionStatus
from commerceos.shared.value_objects.primitives import utc_now


def _status_emoji(status: str) -> str:
    return {
        ExecutionStatus.PLANNED.value: "📋",
        ExecutionStatus.READY.value: "🟡",
        ExecutionStatus.RUNNING.value: "🔄",
        ExecutionStatus.SUCCEEDED.value: "✅",
        ExecutionStatus.FAILED.value: "❌",
        ExecutionStatus.PARTIAL.value: "⚠️",
        ExecutionStatus.ROLLED_BACK.value: "↩️",
        ExecutionStatus.CANCELLED.value: "🚫",
        ExecutionStatus.EXPIRED.value: "⏰",
    }.get(status, "•")


def format_execution_started(plan: Dict[str, Any]) -> str:
    return (
        f"🚀 *Execution Started*\n\n"
        f"Plan: {plan['id']}\n"
        f"Action: {plan['action_type']}\n"
        f"Decision: {plan['decision_id']}\n"
        f"Started: {utc_now().isoformat()}"
    )


def format_execution_finished(plan: Dict[str, Any]) -> str:
    emoji = _status_emoji(plan["status"])
    duration = ""
    if plan.get("started_at") and plan.get("completed_at"):
        try:
            start = datetime.fromisoformat(plan["started_at"])
            end = datetime.fromisoformat(plan["completed_at"])
            duration = f"Duration: {(end - start).total_seconds():.1f}s\n"
        except Exception:
            pass
    return (
        f"{emoji} *Execution Finished: {plan['status'].upper()}*\n\n"
        f"Plan: {plan['id']}\n"
        f"Action: {plan['action_type']}\n"
        f"{duration}"
        f"Completed: {utc_now().isoformat()}"
    )


def format_rollback_executed(plan: Dict[str, Any]) -> str:
    return (
        f"↩️ *Rollback Executed*\n\n"
        f"Plan: {plan['id']}\n"
        f"Action: {plan['action_type']}\n"
        f"Timestamp: {utc_now().isoformat()}"
    )


def format_daily_execution_summary(plans: List[Dict[str, Any]]) -> str:
    lines = [
        "📊 *Daily Execution Summary*",
        "",
        f"_{utc_now().isoformat()}_",
        "",
    ]
    if not plans:
        lines.append("No executions today.")
        return "\n".join(lines)

    counts: Dict[str, int] = {}
    for p in plans:
        counts[p["status"]] = counts.get(p["status"], 0) + 1

    lines.append("*Status counts*")
    for status, count in sorted(counts.items()):
        lines.append(f"{_status_emoji(status)} {status}: {count}")
    lines.append("")
    lines.append(f"Total: {len(plans)}")
    return "\n".join(lines)
