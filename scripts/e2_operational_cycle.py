"""Epic 2 operational cycle — run all WP2.1–WP2.6 modules end-to-end.

This script executes one full daily loop:
  1. Monitoring snapshot (token, sync, KPI, commerce state, data quality)
  2. Intelligence refresh (trends, anomalies, explainers)
  3. Decision refresh (rule-based recommendations)
  4. Execution dry-run on the highest-priority pending decision
  5. Workflow orchestration smoke test
  6. Telegram morning brief
  7. Obsidian daily report write

All writes use dry-run / safe mode. No marketplace mutations occur.
"""
from commerceos.shared.value_objects.primitives import utc_now
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from commerceos.decision.engine import DecisionEngine
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.events.bus import EventBus
from commerceos.events.constants import Priority
from commerceos.events.locking import LockManager
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork
from commerceos.events.workflow import WorkflowEngine, register_default_workflows
from commerceos.execution.engine import ExecutionEngine
from commerceos.execution.sqlalchemy_repositories import SQLAlchemyExecutionUnitOfWork
from commerceos.intelligence.engine import IntelligenceEngine
from commerceos.intelligence.dashboard import IntelligenceDashboard, get_priority_insights, get_trend_summary
from commerceos.intelligence.reporters.obsidian import ObsidianIntelligenceReport
from commerceos.intelligence.reporters.telegram import TelegramBriefGenerator
from commerceos.intelligence.sqlalchemy_repositories import SQLAlchemyIntelligenceUnitOfWork
from commerceos.monitoring.dashboard import MonitoringDashboard
from commerceos.monitoring.job_log import log_job_execution
from commerceos.monitoring.notifiers.obsidian import ObsidianReporter
from commerceos.monitoring.service import MonitoringService
from commerceos.monitoring.sqlalchemy_repositories import SQLAlchemyMonitoringUnitOfWork
from commerceos.platform.database.connection import get_session

DB_URL = "sqlite:///commerceos.db"
DB_PATH = Path("commerceos.db").absolute()
STORE_ID = os.environ.get("STORE_ID", "store-ppm-001")
VAULT_DIR = Path("/Users/gerard/Documents/Obsidian Vault/Agents/Shopee Hermes")


def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def main() -> int:
    start_time = utc_now()
    print(f"Operational cycle started: {start_time.isoformat()}")
    print(f"Database: {DB_PATH}")
    print(f"Store: {STORE_ID}")

    session = get_session(f"sqlite:///{DB_PATH}")

    # 1. Monitoring snapshot
    _section("1. Monitoring snapshot")

    # Log token-health check for scheduler monitoring
    token_health_start = utc_now()
    from token_manager import TokenManager, APPS
    tm = TokenManager(".")
    for app_name in APPS:
        tm.get_access_token(app_name, force_refresh=False)
    token_health_end = utc_now()
    log_job_execution(
        session,
        job_name="shopee-token-health",
        status="completed",
        started_at=token_health_start,
        finished_at=token_health_end,
    )

    monitoring_uow = SQLAlchemyMonitoringUnitOfWork(session)
    monitoring_service = MonitoringService(uow=monitoring_uow, session=session)
    checks = monitoring_service.collect_and_persist(store_id=STORE_ID)
    print(f"Health checks collected: {len(checks)}")
    alerts = monitoring_service.evaluate_alerts(checks)
    print(f"Open alerts: {len(alerts)}")
    snapshot = monitoring_service.generate_snapshot(checks)
    print(f"Overall status: {snapshot.overall_status}")

    # 2. Intelligence
    _section("2. Intelligence refresh")
    intelligence_uow = SQLAlchemyIntelligenceUnitOfWork(session)
    intelligence_engine = IntelligenceEngine(session, uow=intelligence_uow)
    intel_result = intelligence_engine.refresh(store_id=STORE_ID, reference_date=date.today())
    print(json.dumps(intel_result, indent=2, default=str))

    # 3. Decisions
    _section("3. Decision refresh")
    decision_uow = SQLAlchemyDecisionUnitOfWork(session)
    decision_engine = DecisionEngine(session, uow=decision_uow)
    decision_result = decision_engine.refresh(store_id=STORE_ID)
    print(json.dumps(decision_result, indent=2, default=str))

    # 4. Execution dry-run on highest-priority pending decision
    _section("4. Execution dry-run")
    execution_uow = SQLAlchemyExecutionUnitOfWork(session)
    execution_engine = ExecutionEngine(session, execution_uow=execution_uow, decision_uow=decision_uow)
    pending = execution_uow.plans().list(status="planned", limit=10)
    if pending:
        plan = pending[0]
        dry_result = execution_engine.dry_run(plan.id, actor="e2-operational-cycle")
        print(f"Dry-run plan: {plan.id}")
        print(json.dumps(dry_result, indent=2, default=str))
    else:
        print("No pending execution plans; dry-run skipped.")

    # 5. Workflow orchestration smoke test
    _section("5. Workflow orchestration smoke test")
    events_uow = SQLAlchemyEventsUnitOfWork(session)
    bus = EventBus(session, uow=events_uow)
    wf_engine = WorkflowEngine(session, uow=events_uow)
    register_default_workflows(wf_engine)
    job = wf_engine.schedule(
        "orders_synced_pipeline",
        {"store_id": STORE_ID, "triggered_by": "e2-operational-cycle"},
        priority=Priority.NORMAL,
    )
    lm = LockManager(session, default_ttl_seconds=60)
    wf_result = wf_engine.run(job.id, lock_manager=lm)
    print(json.dumps(wf_result, indent=2, default=str))

    # 6. Telegram morning brief
    _section("6. Telegram morning brief")
    intel_dash = IntelligenceDashboard(intelligence_uow)
    priority_insights = intel_dash.get_priority_insights(limit=10)
    trend_summary = intel_dash.get_trend_summary()
    brief_gen = TelegramBriefGenerator()
    brief = brief_gen.generate(priority_insights, trend_summary, time_of_day="morning")
    print(brief)

    # 7. Obsidian daily report
    _section("7. Obsidian daily report")
    try:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = VAULT_DIR / f"Daily Brief — {date.today().isoformat()}.md"

        monitoring_report = ObsidianReporter(vault_dir=VAULT_DIR)
        intel_report = ObsidianIntelligenceReport(vault_dir=VAULT_DIR)
        intel_dash = IntelligenceDashboard(intelligence_uow)

        overall_severity = intel_dash.get_business_summary()["overall_severity"]
        priority_insights = intel_dash.get_priority_insights(limit=10)
        trend_summary = intel_dash.get_trend_summary()
        business_summary = intel_dash.get_business_summary()

        # Write intelligence-specific daily report
        intel_path = intel_report.write_daily_report(
            overall_severity=overall_severity,
            insights=priority_insights,
            trend_summary=trend_summary,
            business_summary=business_summary,
        )

        # Write operations health report
        open_alert_models = monitoring_uow.alerts().get_open()
        ops_path = monitoring_report.write_daily_report(
            overall_status=snapshot.overall_status,
            open_alerts=open_alert_models,
            failed_jobs=[],
            freshness={},
            data_quality_score=snapshot.data_quality_score,
            top_risks=[i["title"] for i in priority_insights if i["severity"] in ("high", "critical")],
        )

        # Combined brief
        lines = [
            f"# Daily Operational Brief — {date.today().isoformat()}\n",
            f"Generated: {utc_now().isoformat()}\n",
            f"Overall health: **{snapshot.overall_status}**\n",
            f"Overall severity: **{overall_severity}**\n",
            "## Priority Insights\n",
        ]
        for ins in priority_insights:
            lines.append(f"- [{ins['severity'].upper()}] {ins['title']}: {ins['explanation']}\n")

        lines.extend(["\n## Pending Decisions\n"])
        for dec in decision_result["decisions"][:5]:
            lines.append(f"- {dec['title']} ({dec['status']})\n")

        lines.extend(["\n## Workflow\n", f"Smoke test job: {job.id} → {wf_result['status']}\n"])

        report_path.write_text("".join(lines), encoding="utf-8")
        print(f"Wrote combined brief: {report_path}")
        print(f"Wrote intel report: {intel_path}")
        print(f"Wrote ops health report: {ops_path}")
    except Exception as exc:
        print(f"Obsidian report skipped: {exc}")

    session.close()
    # Log daily report generation for scheduler health monitoring
    end_time = utc_now()
    log_session = get_session(DB_URL)
    log_job_execution(
        log_session,
        job_name="daily-report",
        status="completed",
        started_at=start_time,
        finished_at=end_time,
    )
    log_session.close()

    print(f"Operational cycle finished: {end_time.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
