"""WP2.6 end-to-end verification script against commerceos.db."""
import json
import os

from commerceos.events.bus import EventBus
from commerceos.events.constants import EventStatus, EventType, Priority
from commerceos.events.dashboard import EventsDashboard
from commerceos.events.locking import LockManager
from commerceos.events.models import Event
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork
from commerceos.events.workflow import WorkflowEngine, register_default_workflows
from commerceos.platform.database.connection import get_session

DB_PATH = os.path.abspath("commerceos.db")
print(f"Using database: {DB_PATH}")

session = get_session(f"sqlite:///{DB_PATH}")
uow = SQLAlchemyEventsUnitOfWork(session)

# 1. Publish an event with multiple handlers
print("\n>>> Publishing OrdersSynced event with subscribers...")
bus = EventBus(session, uow=uow)
calls = []

def kpi_handler(event: Event):
    calls.append(f"refresh_kpis for {event.aggregate_id}")

def monitoring_handler(event: Event):
    calls.append(f"monitoring_snapshot for {event.aggregate_id}")

bus.register(EventType.ORDERS_SYNCED.value, kpi_handler)
bus.register(EventType.ORDERS_SYNCED.value, monitoring_handler)
event = bus.publish(
    EventType.ORDERS_SYNCED.value,
    aggregate_type="sync",
    aggregate_id="store-001",
    payload={"order_count": 42, "store_id": "store-001"},
)
print(f"Event published: {event.id}")
print(f"Status: {event.status}")
print(f"Handlers called: {calls}")

# 2. Trigger default workflow from event
print("\n>>> Scheduling and running default orders_synced_pipeline...")
engine = WorkflowEngine(session, uow=uow)
register_default_workflows(engine)
job = engine.schedule(
    "orders_synced_pipeline",
    {"store_id": "store-001", "triggered_by": event.id},
    priority=Priority.HIGH,
    trigger_event=event,
)
print(f"Workflow job scheduled: {job.id}")

lm = LockManager(session, default_ttl_seconds=60)
result = engine.run(job.id, lock_manager=lm)
print(json.dumps(result, indent=2, default=str))

# 3. Dashboard API verification
print("\n>>> Dashboard API verification...")
dash = EventsDashboard(uow)
print("Recent events:")
print(json.dumps(dash.get_recent_events(hours=24, limit=5), indent=2, default=str))
print("\nRunning workflows:")
print(json.dumps(dash.get_running_workflows(limit=5), indent=2, default=str))
print("\nWorkflow detail:")
print(json.dumps(dash.get_workflow(job.id), indent=2, default=str))
print("\nEvent summary:")
print(json.dumps(dash.get_event_summary(), indent=2, default=str))

# 4. Dead letter demo: publish event with failing handler
print("\n>>> Publishing event with failing handler...")

def failing_handler(event: Event):
    raise RuntimeError("transient failure")

bus2 = EventBus(session, uow=uow)
bus2.register(EventType.INVENTORY_UPDATED.value, failing_handler)
failed_event = bus2.publish(EventType.INVENTORY_UPDATED.value, "inventory", "store-001", {"sku": "ABC"})
print(f"Failed event: {failed_event.id}, status: {failed_event.status}, attempts: {failed_event.attempt_count}")

# 5. Database state verification
print("\n>>> Database state verification...")
from sqlalchemy import create_engine, text
db_engine = create_engine(f"sqlite:///{DB_PATH}")
with db_engine.connect() as conn:
    for table in ["events", "event_subscriptions", "workflow_jobs", "workflow_history", "dead_letter_events", "distributed_locks"]:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"{table}: {count} rows")

session.close()
print("\n=== WP2.6 verification complete ===")
