"""Telegram reporter for Decision Engine briefings."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from commerceos.decision.constants import DecisionSeverity, severity_rank
from commerceos.shared.value_objects.primitives import utc_now


def _severity_emoji(severity: str) -> str:
    return {
        DecisionSeverity.INFO.value: "ℹ️",
        DecisionSeverity.NOTICE.value: "📝",
        DecisionSeverity.WARNING.value: "⚠️",
        DecisionSeverity.HIGH.value: "🔴",
        DecisionSeverity.CRITICAL.value: "🚨",
    }.get(severity, "•")


def format_morning_summary(decisions: List[Dict[str, Any]]) -> str:
    """Morning summary: top proposed decisions with impact and placeholders."""
    if not decisions:
        return "📋 *Morning Decision Brief*\n\nNo open recommendations today."

    lines = ["📋 *Morning Decision Brief*\n", f"_{utc_now().isoformat()}_\n"]
    lines.append(f"*Top {len(decisions)} recommendations*\n")
    for d in decisions:
        emoji = _severity_emoji(d["severity"])
        impact = d.get("expected_impact", {})
        revenue = impact.get("expected_revenue_change")
        profit = impact.get("expected_profit_change")
        cash = impact.get("expected_cash_change")
        impact_text = []
        if revenue is not None:
            impact_text.append(f"rev {revenue:+.0%}" if isinstance(revenue, float) else f"rev {revenue}")
        if profit is not None:
            impact_text.append(f"profit {profit:+.0%}" if isinstance(profit, float) else f"profit {profit}")
        if cash is not None:
            impact_text.append(f"cash {cash:+.0%}" if isinstance(cash, float) else f"cash {cash}")
        impact_str = " | ".join(impact_text) if impact_text else "impact TBD"
        lines.append(
            f"{emoji} *{d['severity'].upper()}* — {d['title']}\n"
            f"  {d['recommended_action']}\n"
            f"  Impact: {impact_str} (confidence: {d.get('confidence', 'medium')})\n"
            f"  [Approve / Reject / Review]\n"
        )
    return "\n".join(lines)


def format_evening_summary(
    approved: List[Dict[str, Any]],
    rejected: List[Dict[str, Any]],
    expired: List[Dict[str, Any]],
) -> str:
    """Evening summary: decisions that changed status today."""
    lines = ["🌙 *Evening Decision Brief*\n", f"_{utc_now().isoformat()}_\n"]
    if approved:
        lines.append(f"*Approved ({len(approved)})*\n")
        for d in approved:
            lines.append(f"✅ {d['title']}\n")
    if rejected:
        lines.append(f"*Rejected ({len(rejected)})*\n")
        for d in rejected:
            lines.append(f"❌ {d['title']}\n")
    if expired:
        lines.append(f"*Expired ({len(expired)})*\n")
        for d in expired:
            lines.append(f"⏰ {d['title']}\n")
    if not (approved or rejected or expired):
        lines.append("No decision status changes today.\n")
    return "\n".join(lines)


def format_decision_report(decision: Dict[str, Any]) -> str:
    """Full report for a single decision."""
    impact = decision.get("expected_impact", {})
    lines = [
        f"*Decision: {decision['title']}*\n",
        f"Category: {decision['category']}",
        f"Severity: {decision['severity']}",
        f"Status: {decision['status']}",
        f"Confidence: {decision.get('confidence', 'medium')}",
        "",
        f"Description: {decision['description']}",
        "",
        f"Rationale: {decision['rationale']}",
        "",
        f"Recommended action: {decision['recommended_action']}",
        "",
        "Expected impact:",
        f"  Revenue: {impact.get('expected_revenue_change')}",
        f"  Profit: {impact.get('expected_profit_change')}",
        f"  Cash: {impact.get('expected_cash_change')}",
    ]
    if decision.get("evidence"):
        lines.extend(["", "Evidence:"])
        for e in decision["evidence"]:
            lines.append(f"  • {e['source_type']}: {e['description']}")
    return "\n".join(lines)
