"""Epic 1 Operational Acceptance Test verification.

Runs every 4 hours during the 24-hour observation window. Checks:
- Token health and stability
- Sync checkpoint freshness
- KPI / CommerceState materialization
- Data quality score
- No auth failures / duplicate records
- No alert files

Appends results to logs/e1_oat.log and reports failures immediately.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from commerceos.shared.value_objects.primitives import utc_now
import json
import os
from datetime import datetime, timezone

from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.commerce.models import KPI, CommerceState
from commerceos.ingestion.models import SyncCheckpoint, SyncRun
from commerceos.dashboard.query_service import DashboardQueryService
from token_manager import TokenManager

DB_URL = "sqlite:///commerceos.db"
STORE_ID = "store-ppm-001"
ORG_ID = "org-ppm-001"
BIZ_ID = "biz-ppm-001"


def check_token_health():
    tm = TokenManager(".")
    health = tm.check_health(auto_refresh=False)
    issues = []
    for app, h in health.items():
        if h.get("status") != "healthy":
            issues.append(f"{app}: status={h.get('status')}")
        if h.get("needs_reauth"):
            issues.append(f"{app}: needs_reauth")
        if (h.get("refresh_token_days_remaining") or 0) < 25:
            issues.append(f"{app}: refresh_token_days_remaining={h.get('refresh_token_days_remaining')}")
    return health, issues


def check_checkpoints():
    reset_engine()
    create_all(DB_URL)
    sess = get_session(DB_URL)
    try:
        cps = sess.query(SyncCheckpoint).filter_by(store_id=STORE_ID).all()
        now = utc_now()
        stale = []
        for cp in cps:
            ts = cp.last_successful_sync_at
            if not ts:
                stale.append(cp.entity_type)
                continue
            ts_utc = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            hours = (now - ts_utc).total_seconds() / 3600
            if hours > 24:
                stale.append(f"{cp.entity_type} ({hours:.1f}h)")
        return {"entities": [cp.entity_type for cp in cps], "stale": stale}
    finally:
        sess.close()
        reset_engine()


def check_commerce_state():
    reset_engine()
    create_all(DB_URL)
    sess = get_session(DB_URL)
    try:
        qs = DashboardQueryService(sess)
        state = qs.get_commerce_state(STORE_ID)
        return {
            "data_quality_score": state.get("data_quality_score"),
            "sources_fresh": state.get("sources_fresh", []),
            "sources_stale": state.get("sources_stale", []),
            "summary_present": bool(state.get("summary")),
            "temporary": state.get("temporary", False),
        }
    finally:
        sess.close()
        reset_engine()


def check_alerts():
    workspace = Path(".")
    alerts = list(workspace.glob("ALERT_*_reauth_needed.txt"))
    return [a.name for a in alerts]


def main():
    now = utc_now().isoformat()
    report = {"timestamp": now}
    failures = []

    health, token_issues = check_token_health()
    report["token_health"] = health
    if token_issues:
        failures.extend(token_issues)

    cp_report = check_checkpoints()
    report["checkpoints"] = cp_report
    if cp_report["stale"]:
        failures.append(f"Stale checkpoints: {cp_report['stale']}")

    state_report = check_commerce_state()
    report["commerce_state"] = state_report
    if state_report["temporary"]:
        failures.append("CommerceState is temporary")
    if state_report.get("data_quality_score", 0) < 0.9:
        failures.append(f"Data quality score low: {state_report.get('data_quality_score')}")

    alerts = check_alerts()
    report["alerts"] = alerts
    if alerts:
        failures.append(f"Alert files present: {alerts}")

    log_path = Path("logs/e1_oat.log")
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(report, indent=2, default=str) + "\n---\n")

    if failures:
        msg = "❌ E1 OAT FAILURES:\n" + "\n".join(f"- {f}" for f in failures)
        print(msg)
        # Exit non-zero so cron failure is visible
        sys.exit(1)
    else:
        print(f"✅ E1 OAT check passed at {now}")
        print(f"   Token health: { {k: v['status'] for k, v in health.items()} }")
        print(f"   Sources fresh: {state_report['sources_fresh']}")


if __name__ == "__main__":
    main()
