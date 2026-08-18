"""Telegram notifier for the CommerceOS COO channel.

Delivers concise summaries to Telegram. Full knowledge remains in Obsidian.
Delivery status is persisted via JobExecution metadata (do not create a separate
status table). Supports no-token / disabled mode so scripts can run in CI without
a real chat_id.
"""
from __future__ import annotations
from commerceos.shared.value_objects.primitives import utc_now


from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from commerceos.config.settings import Settings, get_settings


@dataclass
class TelegramDelivery:
    """Result of one Telegram message delivery attempt."""

    ok: bool
    status_code: Optional[int] = None
    telegram_message_id: Optional[int] = None
    error: Optional[str] = None
    sent_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "status_code": self.status_code,
            "telegram_message_id": self.telegram_message_id,
            "error": self.error,
            "sent_at": self.sent_at,
        }


class TelegramNotifier:
    """Send Telegram messages. Disabled if bot_token or chat_id is missing."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self._disabled = not (self.bot_token and self.chat_id)

    @classmethod
    def from_settings(cls, settings: Optional[Settings] = None) -> "TelegramNotifier":
        settings = settings or get_settings()
        return cls(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        )

    def is_enabled(self) -> bool:
        return not self._disabled

    def send(self, text: str, parse_mode: str = "HTML") -> TelegramDelivery:
        """Send a message. Returns a delivery record whether enabled or not."""
        sent_at = utc_now().isoformat()
        if self._disabled:
            return TelegramDelivery(
                ok=False,
                error="Telegram notifier disabled: missing bot_token or chat_id",
                sent_at=sent_at,
            )

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            data = resp.json()
            if resp.ok and data.get("ok"):
                return TelegramDelivery(
                    ok=True,
                    status_code=resp.status_code,
                    telegram_message_id=data.get("result", {}).get("message_id"),
                    sent_at=sent_at,
                )
            return TelegramDelivery(
                ok=False,
                status_code=resp.status_code,
                error=data.get("description") or resp.text,
                sent_at=sent_at,
            )
        except Exception as exc:  # noqa: BLE001
            return TelegramDelivery(
                ok=False,
                error=f"{exc.__class__.__name__}: {exc}",
                sent_at=sent_at,
            )


class COOReporter:
    """Build and send morning/evening COO briefs to Telegram."""

    def __init__(
        self,
        notifier: Optional[TelegramNotifier] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.notifier = notifier or TelegramNotifier.from_settings(self.settings)

    def morning_brief(
        self,
        business_state: Dict[str, Any],
        open_alerts: List[Dict[str, Any]],
        open_decisions: List[Dict[str, Any]],
    ) -> TelegramDelivery:
        """Send a concise morning brief."""
        lines = [
            "🌅 <b>Morning Brief</b>",
            f"<i>{utc_now().strftime('%Y-%m-%d %H:%M UTC')}</i>",
            "",
            f"Revenue: <b>Rp {business_state.get('revenue', 0):,.0f}</b>",
            f"Profit: <b>Rp {business_state.get('gross_profit', 0):,.0f}</b>",
            f"ROAS: <b>{business_state.get('roas', 0):.2f}x</b>",
            f"Health: <b>{business_state.get('overall_health', '—')}</b>",
        ]
        if open_alerts:
            lines.append("")
            lines.append(f"⚠️ {len(open_alerts)} alert(s)")
            for a in open_alerts[:3]:
                lines.append(f"• {a.get('severity', '—')} — {a.get('message', '—')}")
        if open_decisions:
            lines.append("")
            lines.append(f"🚨 {len(open_decisions)} decision(s) pending")
            for d in open_decisions[:3]:
                lines.append(f"• {d.get('title', '—')}")
        lines.append("")
        lines.append("See Obsidian for full details.")
        return self.notifier.send("\n".join(lines))

    def evening_review(
        self,
        wins: List[str],
        issues: List[str],
        completed_actions: List[str],
        unresolved_items: List[str],
    ) -> TelegramDelivery:
        """Send a concise evening review."""
        lines = [
            "🌙 <b>Evening Review</b>",
            f"<i>{utc_now().strftime('%Y-%m-%d %H:%M UTC')}</i>",
        ]
        if wins:
            lines.extend(["", "✅ Wins"])
            for w in wins[:5]:
                lines.append(f"• {w}")
        if completed_actions:
            lines.extend(["", "🎯 Completed"])
            for c in completed_actions[:5]:
                lines.append(f"• {c}")
        if issues:
            lines.extend(["", "⚠️ Issues"])
            for i in issues[:5]:
                lines.append(f"• {i}")
        if unresolved_items:
            lines.extend(["", "⏳ Unresolved"])
            for u in unresolved_items[:5]:
                lines.append(f"• {u}")
        lines.append("")
        lines.append("See Obsidian for full details.")
        return self.notifier.send("\n".join(lines))
