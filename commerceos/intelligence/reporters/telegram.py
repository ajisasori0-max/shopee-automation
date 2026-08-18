"""Telegram brief generator for the intelligence layer."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from commerceos.intelligence.constants import InsightSeverity
from commerceos.shared.value_objects.primitives import utc_now


class TelegramBriefGenerator:
    """Generate morning/evening intelligence briefs for Telegram."""

    def morning_brief(self, priority_insights: List[Dict[str, Any]], trend_summary: List[Dict[str, Any]]) -> str:
        return self._build_brief("Morning Brief", priority_insights, trend_summary)

    def evening_brief(self, priority_insights: List[Dict[str, Any]], trend_summary: List[Dict[str, Any]]) -> str:
        return self._build_brief("Evening Brief", priority_insights, trend_summary)

    def _build_brief(self, label: str, priority_insights: List[Dict[str, Any]], trend_summary: List[Dict[str, Any]]) -> str:
        lines = [f"🌅 <b>{label}</b>", f"Generated: {utc_now().isoformat()}", ""]
        critical = [i for i in priority_insights if i["severity"] == InsightSeverity.CRITICAL.value]
        high = [i for i in priority_insights if i["severity"] == InsightSeverity.HIGH.value]
        warnings = [i for i in priority_insights if i["severity"] == InsightSeverity.WARNING.value]

        if critical or high:
            lines.append("<b>⚠️ Needs Attention</b>")
            for i in critical + high:
                lines.append(f"• {i['title']}")
        else:
            lines.append("<b>Status: Stable</b>")

        if warnings:
            lines.append("")
            lines.append("<b>Watchlist</b>")
            for i in warnings:
                lines.append(f"• {i['title']}")

        lines.append("")
        lines.append("<b>Top Trends</b>")
        for t in trend_summary[:5]:
            delta = t.get("delta_pct")
            emoji = "📈" if delta and delta > 0 else "📉" if delta and delta < 0 else "➡️"
            lines.append(f"{emoji} {t['metric']} ({t['period']}): {delta:+.1f}%" if delta is not None else f"{emoji} {t['metric']}: N/A")

        return "\n".join(lines)

    def generate(self, priority_insights: List[Dict[str, Any]], trend_summary: List[Dict[str, Any]], time_of_day: str = "morning") -> str:
        if time_of_day == "morning":
            return self.morning_brief(priority_insights, trend_summary)
        return self.evening_brief(priority_insights, trend_summary)
