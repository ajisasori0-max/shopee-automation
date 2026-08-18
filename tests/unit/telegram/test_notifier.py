"""Tests for the Telegram COO channel."""

import pytest

from commerceos.telegram.notifier import COOReporter, TelegramDelivery, TelegramNotifier


class FakeTelegramNotifier(TelegramNotifier):
    def __init__(self, enabled: bool = True, fail: bool = False):
        super().__init__(bot_token="token" if enabled else None, chat_id="chat" if enabled else None)
        self._forced_fail = fail
        self.sent_messages: list = []

    def send(self, text: str, parse_mode: str = "HTML") -> TelegramDelivery:
        if not self.is_enabled():
            return TelegramDelivery(ok=False, error="disabled: missing credentials")
        self.sent_messages.append(text)
        if self._forced_fail:
            return TelegramDelivery(ok=False, error="forced failure")
        return TelegramDelivery(ok=True, status_code=200, telegram_message_id=123)


def test_notifier_disabled_without_credentials():
    notifier = TelegramNotifier(bot_token=None, chat_id=None)
    assert not notifier.is_enabled()
    delivery = notifier.send("hello")
    assert not delivery.ok
    assert "disabled" in delivery.error.lower()


def test_notifier_send_failure_graceful():
    # Using real HTTP with invalid token will fail; verify graceful handling.
    notifier = TelegramNotifier(bot_token="invalid", chat_id="123")
    assert notifier.is_enabled()
    delivery = notifier.send("hello")
    assert not delivery.ok


def test_coo_reporter_morning_brief():
    notifier = FakeTelegramNotifier()
    reporter = COOReporter(notifier=notifier)
    delivery = reporter.morning_brief(
        business_state={"revenue": 1_000_000, "gross_profit": 200_000, "roas": 2.5, "overall_health": "healthy"},
        open_alerts=[{"severity": "high", "message": "ROAS dropped"}],
        open_decisions=[{"title": "Increase budget"}],
    )
    assert delivery.ok
    assert "Morning Brief" in notifier.sent_messages[0]
    assert "ROAS" in notifier.sent_messages[0]


def test_coo_reporter_evening_review():
    notifier = FakeTelegramNotifier()
    reporter = COOReporter(notifier=notifier)
    delivery = reporter.evening_review(
        wins=["Revenue target met"],
        issues=["Token refresh warning"],
        completed_actions=["Approved budget increase"],
        unresolved_items=["Pending re-auth"],
    )
    assert delivery.ok
    assert "Evening Review" in notifier.sent_messages[0]
    assert "Revenue target met" in notifier.sent_messages[0]


def test_coo_reporter_disabled_notifier():
    notifier = FakeTelegramNotifier(enabled=False)
    reporter = COOReporter(notifier=notifier)
    delivery = reporter.morning_brief(
        business_state={"revenue": 0, "gross_profit": 0, "roas": 0, "overall_health": "unknown"},
        open_alerts=[],
        open_decisions=[],
    )
    assert not delivery.ok
    assert not notifier.sent_messages
    assert "disabled" in delivery.error.lower()
