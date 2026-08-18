"""Tests for knowledge memory collection and summarization."""

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from commerceos.knowledge.index import KnowledgeIndex
from commerceos.knowledge.memory import KnowledgeMemory
from commerceos.knowledge.summarizer import MemorySummarizer


@pytest.fixture
def mock_dashboards():
    qs = MagicMock()
    qs.get_commerce_state.return_value = {
        "data_quality_score": 0.95,
        "sources_fresh": ["orders", "payments"],
        "sources_stale": [],
    }
    qs.get_pl_summary.return_value = {
        "net_sales": 1_000_000,
        "gross_profit": 250_000,
        "orders": 42,
    }
    qs.get_ad_performance_summary.return_value = {
        "roas": 3.5,
        "spend": 200_000,
    }
    qs.get_freshness.return_value = {
        "orders": {"is_fresh": True, "hours_since_sync": 2.0, "last_sync": "2026-07-29T00:00:00+00:00"},
    }
    qs.get_daily_sales.return_value = [
        {"date": "2026-07-28", "revenue": 900_000, "orders": 40},
        {"date": "2026-07-29", "revenue": 1_000_000, "orders": 42},
    ]

    monitoring = MagicMock()
    monitoring.get_health_snapshot.return_value = {"overall_status": "healthy"}
    monitoring.get_open_alerts.return_value = [
        {"id": "a1", "title": "Inventory low", "severity": "warning", "category": "inventory", "description": "SKU-1 is low."},
    ]

    intelligence = MagicMock()
    intelligence.get_priority_insights.return_value = [
        {"id": "i1", "title": "Revenue up", "category": "revenue", "severity": "info", "explanation": "Revenue increased 10% due to ads."},
    ]

    decisions = MagicMock()
    decisions.get_open_decisions.return_value = [
        {"id": "d1", "title": "Raise ad budget", "category": "marketing", "severity": "high", "status": "proposed", "recommended_action": "Increase budget 10%"},
    ]
    decisions.get_decision_summary.return_value = {"counts_by_status": {"proposed": 1}}

    executions = MagicMock()
    executions.get_recent_executions.return_value = [
        {"id": "e1", "action_type": "adjust_budget", "status": "succeeded", "decision_id": "d1", "completed_at": "2026-07-29T10:00:00+00:00"},
    ]

    events = MagicMock()
    events.get_recent_events.return_value = [
        {"event_type": "workflow.completed", "status": "completed", "aggregate_type": "workflow", "aggregate_id": "wf-1"},
        {"event_type": "sync.failed", "status": "failed", "aggregate_type": "sync", "aggregate_id": "sync-1"},
        {"event_type": "noise", "status": "pending", "aggregate_type": "job", "aggregate_id": "job-1"},
    ]

    return qs, monitoring, intelligence, decisions, executions, events


def test_memory_collects_dashboard_data(mock_dashboards):
    qs, monitoring, intelligence, decisions, executions, events = mock_dashboards
    memory = KnowledgeMemory(qs, monitoring, intelligence, decisions, executions, events)
    result = memory.generate_daily(date(2026, 7, 29))

    assert result["note_id"] == "kn-2026-07-29"
    assert result["note_type"] == "daily"
    assert result["business_state"]["revenue"] == 1_000_000
    assert result["business_state"]["roas"] == 3.5
    assert result["business_state"]["overall_health"] == "healthy"
    assert len(result["insights"]) == 1
    assert len(result["decisions"]["open"]) == 1
    assert len(result["executions"]) == 1
    assert len(result["alerts"]) == 1
    assert len(result["events"]) == 2  # completed + failed, pending ignored


def test_memory_handles_missing_data():
    qs = MagicMock()
    qs.get_commerce_state.side_effect = Exception("db down")
    qs.get_pl_summary.side_effect = Exception("db down")
    qs.get_ad_performance_summary.side_effect = Exception("db down")
    qs.get_freshness.side_effect = Exception("db down")
    qs.get_daily_sales.side_effect = Exception("db down")

    monitoring = MagicMock()
    monitoring.get_health_snapshot.side_effect = Exception("db down")
    monitoring.get_open_alerts.side_effect = Exception("db down")

    intelligence = MagicMock()
    intelligence.get_priority_insights.side_effect = Exception("db down")

    decisions = MagicMock()
    decisions.get_open_decisions.side_effect = Exception("db down")
    decisions.get_decision_summary.side_effect = Exception("db down")

    executions = MagicMock()
    executions.get_recent_executions.side_effect = Exception("db down")

    events = MagicMock()
    events.get_recent_events.side_effect = Exception("db down")

    memory = KnowledgeMemory(qs, monitoring, intelligence, decisions, executions, events)
    result = memory.generate_daily(date(2026, 7, 29))

    assert result["business_state"]["revenue"] is None
    assert result["kpis"] == []
    assert result["insights"] == []
    assert result["events"] == []
    assert result["alerts"] == []
    assert result["business_state"]["overall_health"] is None


def test_memory_ignores_irrelevant_events(mock_dashboards):
    qs, monitoring, intelligence, decisions, executions, events = mock_dashboards
    memory = KnowledgeMemory(qs, monitoring, intelligence, decisions, executions, events)
    result = memory.generate_daily(date(2026, 7, 29))
    event_statuses = {e["status"] for e in result["events"]}
    assert "pending" not in event_statuses


def test_summarizer_daily_body(mock_dashboards):
    qs, monitoring, intelligence, decisions, executions, events = mock_dashboards
    memory = KnowledgeMemory(qs, monitoring, intelligence, decisions, executions, events)
    data = memory.generate_daily(date(2026, 7, 29))

    summarizer = MemorySummarizer()
    body = summarizer.daily_body(data)
    assert "## Business State" in body
    assert "Rp 1,000,000" in body
    assert "## KPIs" in body
    assert "## Intelligence" in body
    assert "## Decisions" in body
    assert "Raise ad budget" in body
    assert "## Executions" in body
    assert "## Alerts" in body
    assert "Inventory low" in body
    assert "## Important Events" in body


def test_summarizer_weekly_synthesizes_not_concatenates():
    summarizer = MemorySummarizer()
    dailies = [
        {
            "note_id": "kn-2026-07-27",
            "business_state": {"revenue": 100, "overall_health": "healthy"},
            "events": [{"status": "completed", "event_type": "workflow.completed"}],
            "executions": [],
            "alerts": [{"title": "Inventory low", "severity": "warning", "category": "inventory"}],
            "decisions": {"open": []},
            "lessons": [],
            "follow_ups": [],
        },
        {
            "note_id": "kn-2026-07-28",
            "business_state": {"revenue": 110, "overall_health": "healthy"},
            "events": [{"status": "completed", "event_type": "workflow.completed"}],
            "executions": [],
            "alerts": [{"title": "Inventory low", "severity": "warning", "category": "inventory"}],
            "decisions": {"open": []},
            "lessons": [],
            "follow_ups": [],
        },
    ]

    weekly = summarizer.synthesize_weekly(dailies, date(2026, 7, 27))
    assert weekly["note_id"] == "kn-2026-W31"
    assert weekly["tags"] == ["weekly", "review", "business", "decisions", "lessons"]
    body = weekly["body"]
    assert "Revenue increased" in body or "Revenue remained flat" in body or "Revenue decreased" in body
    assert "Inventory low" in body  # recurring issue
    # Should not be a raw dump of the daily notes
    assert "kn-2026-07-27" not in body
    assert weekly["links"] == ["kn-2026-07-27", "kn-2026-07-28"]


def test_summarizer_preserves_decisions():
    summarizer = MemorySummarizer()
    dailies = [
        {
            "note_id": "kn-2026-07-27",
            "business_state": {"revenue": 100},
            "events": [],
            "executions": [],
            "alerts": [],
            "decisions": {"open": [{"id": "d1", "title": "Approve Budget", "status": "proposed"}]},
            "lessons": [],
            "follow_ups": [],
        },
        {
            "note_id": "kn-2026-07-28",
            "business_state": {"revenue": 100},
            "events": [],
            "executions": [],
            "alerts": [],
            "decisions": {"open": [{"id": "d1", "title": "Approve Budget", "status": "proposed"}]},
            "lessons": [],
            "follow_ups": [],
        },
    ]
    weekly = summarizer.synthesize_weekly(dailies, date(2026, 7, 27))
    assert "Approve Budget" in weekly["body"]
    assert weekly["body"].count("Approve Budget") == 1  # deduplicated


def test_summarizer_monthly_and_yearly():
    summarizer = MemorySummarizer()
    weekly = summarizer.synthesize_weekly([], date(2026, 7, 27))
    monthly = summarizer.synthesize_monthly([weekly], date(2026, 7, 1))
    assert monthly["note_id"] == "kn-2026-07"
    assert "monthly" in monthly["tags"]
    yearly = summarizer.synthesize_yearly([monthly], 2026)
    assert yearly["note_id"] == "kn-2026"
    assert "yearly" in yearly["tags"]


def test_index_generates_categories_and_no_duplicates():
    index = KnowledgeIndex(Path("/tmp/test_vault"))
    notes = [
        {"note_id": "n1", "note_type": "daily", "note_date": "2026-07-29", "title": "Daily 1", "path": "10 COO/Daily/1.md", "tags": ["business"]},
        {"note_id": "n2", "note_type": "decision", "note_date": "2026-07-28", "title": "Decision 1", "path": "20 Decisions/1.md", "tags": ["decision"]},
        {"note_id": "n3", "note_type": "daily", "note_date": "2026-07-28", "title": "Daily 2", "path": "10 COO/Daily/2.md", "tags": ["lesson"]},
        {"note_id": "n1", "note_type": "daily", "note_date": "2026-07-29", "title": "Daily 1 duplicate", "path": "10 COO/Daily/1.md", "tags": ["business"]},
    ]
    path = index.generate(notes)
    content = path.read_text(encoding="utf-8")
    assert "# CommerceOS Knowledge Index" in content
    assert "Total notes: 4" in content
    assert "## Business" in content
    assert "## Decisions" in content
    assert "## Lessons Learned" in content
    assert "Daily 1" in content
    # Categorized sections deduplicate by note_id; All Notes keeps every record.
    business_section = content.split("## Projects")[0]
    assert business_section.count("- [[10 COO/Daily/1.md|Daily 1]]") == 1
    all_notes_section = content.split("## All Notes")[1]
    assert all_notes_section.count("`daily` (business)") == 2
    assert all_notes_section.count("`decision` (decision)") == 1
    assert all_notes_section.count("`daily` (lesson)") == 1


def test_index_idempotent(tmp_path: Path):
    index = KnowledgeIndex(tmp_path)
    notes = [{"note_id": "n1", "note_type": "daily", "note_date": "2026-07-29", "title": "Daily", "path": "x.md", "tags": []}]
    path1 = index.generate(notes)
    content1 = path1.read_text(encoding="utf-8")
    path2 = index.generate(notes)
    content2 = path2.read_text(encoding="utf-8")
    # Same input produces same structure. Timestamps differ.
    assert content1.splitlines()[4:] == content2.splitlines()[4:]


def test_index_empty_skeleton():
    index = KnowledgeIndex(Path("/tmp/empty_vault"))
    path = index.generate([])
    content = path.read_text(encoding="utf-8")
    assert "Total notes: 0" in content
    assert "No entries yet" in content


def test_summarizer_deterministic_output():
    summarizer = MemorySummarizer()
    dailies = [
        {
            "note_id": "kn-2026-07-27",
            "business_state": {"revenue": 100, "overall_health": "healthy"},
            "events": [],
            "executions": [],
            "alerts": [],
            "decisions": {"open": []},
            "lessons": [],
            "follow_ups": [],
        },
    ]
    weekly1 = summarizer.synthesize_weekly(dailies, date(2026, 7, 27))
    weekly2 = summarizer.synthesize_weekly(dailies, date(2026, 7, 27))
    assert weekly1["body"] == weekly2["body"]


def test_summarizer_money_and_int_formatting():
    summarizer = MemorySummarizer()
    assert summarizer._money(1_500_000) == "Rp 1,500,000"
    assert summarizer._money(None) == "—"
    assert summarizer._int(1_234) == "1,234"
    assert summarizer._int(None) == "—"
