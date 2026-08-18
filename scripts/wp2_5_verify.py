"""WP2.5 end-to-end verification script against commerceos.db."""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from commerceos.commerce.models import KPI, CommerceState
from commerceos.decision.constants import DecisionCategory, DecisionSeverity, DecisionStatus
from commerceos.decision.engine import DecisionEngine, DecisionLifecycleService
from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.execution.audit import ExecutionAuditLogger
from commerceos.execution.constants import ExecutionStatus, AuditEvent
from commerceos.execution.dashboard import ExecutionDashboard, get_execution_queue, get_running, get_recent_executions, get_execution, get_execution_summary
from commerceos.execution.engine import ExecutionEngine
from commerceos.execution.executors.base import get_executor
from commerceos.execution.models import ExecutionPlan
from commerceos.execution.reporters.telegram import format_execution_started, format_execution_finished, format_daily_execution_summary
from commerceos.execution.reporters.obsidian import format_daily_report
from commerceos.execution.sqlalchemy_repositories import SQLAlchemyExecutionUnitOfWork
from commerceos.execution.validators import ExecutionValidator
from commerceos.platform.database.connection import get_session
from commerceos.platform.database.models import new_uuid
from commerceos.shared.value_objects.primitives import utc_now

DB_PATH = os.path.abspath("commerceos.db")
print(f"Using database: {DB_PATH}")

session = get_session(f"sqlite:///{DB_PATH}")

decision_uow = SQLAlchemyDecisionUnitOfWork(session)
execution_uow = SQLAlchemyExecutionUnitOfWork(session)

# 1. Ensure an approved decision exists. If not, generate one from a ROAS insight.
store_id = "1147948100"
existing_decisions = decision_uow.decisions().list(status=DecisionStatus.APPROVED.value, limit=10)
approved_decision = existing_decisions[0] if existing_decisions else None

if approved_decision is None:
    print("\n>>> No approved decision found. Generating one from a ROAS insight...")
    # Ensure a KPI exists for the rule to trigger
    roas_kpi = session.query(KPI).filter_by(store_id=store_id, code="roas").order_by(KPI.freshness.desc()).first()
    if roas_kpi is None:
        kpi = KPI(
            id=new_uuid(),
            code="roas",
            name="ROAS",
            value=Decimal("1.2"),
            confidence=Decimal("1.0"),
            freshness=utc_now(),
            organization_id="org-001",
            business_id="biz-001",
            store_id=store_id,
        )
        session.add(kpi)
        session.commit()

    decision_engine = DecisionEngine(session, uow=decision_uow)
    insights = [{
        "id": new_uuid(),
        "category": "advertising",
        "title": "ROAS fell below threshold",
        "explanation": "ROAS is 1.2, below the 2.0 target.",
        "severity": "high",
    }]
    result = decision_engine.refresh(store_id, insights=insights)
    if not result["decisions"]:
        raise RuntimeError("No decisions generated")
    decision_id = result["decisions"][0]["id"]
    lifecycle = DecisionLifecycleService(decision_uow)
    approved_decision = lifecycle.approve(decision_id, changed_by="wp2.5-verification")
    print(f"Approved decision: {approved_decision.id}")
else:
    print(f"\n>>> Using existing approved decision: {approved_decision.id}")

# 2. Generate immutable ExecutionPlan
print("\n>>> Creating ExecutionPlan...")
execution_engine = ExecutionEngine(
    session,
    execution_uow=execution_uow,
    decision_uow=decision_uow,
)
plan = execution_engine.create_plan(approved_decision.id, actor="wp2.5-verification")
print(f"Plan created: {plan.id}")
print(f"Action type: {plan.action_type}")
print(f"Initial status: {plan.status}")
print(f"Checksum: {plan.checksum}")
print(f"Steps: {[(s.step_number, s.action, s.status) for s in plan.steps]}")

# 3. DRY RUN
print("\n>>> Performing DRY RUN...")
dry_result = execution_engine.dry_run(plan.id, actor="wp2.5-verification")
print(json.dumps(dry_result, indent=2, default=str))

# Verify plan status unchanged after dry run
with execution_uow:
    plan_after_dry = execution_uow.plans().get(plan.id)
    print(f"\nPlan status after dry run: {plan_after_dry.status}")
    assert plan_after_dry.status == ExecutionStatus.PLANNED.value, "Dry run must not change plan status"

# 4. VALIDATION
print("\n>>> Validating plan...")
validator = ExecutionValidator(auth_valid=True, marketplace_available=True)
with decision_uow:
    decision = decision_uow.decisions().get(approved_decision.id)
with execution_uow:
    plan_for_validation = execution_uow.plans().get(plan.id)
    existing = execution_uow.plans().list(decision_id=plan.decision_id, limit=1000)
validation = validator.validate(decision, plan_for_validation, existing_plans=existing)
print(json.dumps(validation.to_dict(), indent=2, default=str))
assert validation.ok, "Validation should pass"

# 5. EXECUTE (simulated - no real marketplace changes)
print("\n>>> EXECUTING plan (simulated)...")
# Simulated marketplace function: records the call but does nothing
marketplace_calls = []
def simulated_marketplace_fn(entity_id, action_value):
    marketplace_calls.append({"entity_id": entity_id, "action_value": action_value, "timestamp": utc_now().isoformat()})
    return {"ok": True}

exec_result = execution_engine.execute(plan.id, actor="wp2.5-verification", marketplace_fn=simulated_marketplace_fn)
print(json.dumps(exec_result, indent=2, default=str))
assert exec_result["success"] is True, f"Execution failed: {exec_result}"

# 6. Verify final state
print("\n>>> Verifying final state...")
with execution_uow:
    final_plan = execution_uow.plans().get(plan.id)
    print(f"Final status: {final_plan.status}")
    print(f"Checksum unchanged: {final_plan.checksum == plan.checksum}")
    print(f"Started at: {final_plan.started_at}")
    print(f"Completed at: {final_plan.completed_at}")
    steps = execution_uow.steps().list_for_plan(plan.id)
    for s in steps:
        print(f"  Step {s.step_number}: {s.action} -> {s.status} (started {s.started_at}, completed {s.completed_at})")
    history = execution_uow.history().list_for_plan(plan.id)
    print(f"\nHistory entries ({len(history)}):")
    for h in history:
        print(f"  {h.changed_at}: {h.old_status} -> {h.new_status}")
    audit = execution_uow.audit().list_for_plan(plan.id)
    print(f"\nAudit events ({len(audit)}):")
    for a in audit:
        print(f"  {a.timestamp}: {a.event} (actor={a.actor}, details={json.dumps(a.details, default=str)[:120]})")

# 7. Verify no duplicate executions
with execution_uow:
    plans_for_decision = execution_uow.plans().list(decision_id=plan.decision_id, limit=1000)
    print(f"\nPlans for decision {plan.decision_id}: {len(plans_for_decision)}")
    running = [p for p in plans_for_decision if p.status == ExecutionStatus.RUNNING.value]
    print(f"Running plans for this decision: {len(running)}")

# 8. Dashboard API verification
print("\n>>> Dashboard API verification...")
dash = ExecutionDashboard(execution_uow)
print("get_execution_queue:")
print(json.dumps(dash.get_execution_queue(limit=5), indent=2, default=str))
print("\nget_running:")
print(json.dumps(dash.get_running(limit=5), indent=2, default=str))
print("\nget_recent_executions:")
print(json.dumps(dash.get_recent_executions(hours=24, limit=5), indent=2, default=str))
print("\nget_execution(plan_id):")
full_plan = dash.get_execution(plan.id)
print(json.dumps(full_plan, indent=2, default=str))
print("\nget_execution_summary:")
print(json.dumps(dash.get_execution_summary(), indent=2, default=str))

# 9. Sample outputs
print("\n>>> Sample Telegram notifications...")
plan_dict = get_execution(execution_uow, plan.id)
print(format_execution_started(plan_dict))
print("\n---\n")
print(format_execution_finished(plan_dict))
print("\n---\n")
print(format_daily_execution_summary([plan_dict]))

print("\n>>> Sample Obsidian Daily Execution Report...")
print(format_daily_report([plan_dict]))

session.close()
print("\n=== WP2.5 verification complete ===")
