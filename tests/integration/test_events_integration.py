"""Integration tests for Event Bus and Workflow Orchestration."""

import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from commerceos.commerce.models import KPI
from commerceos.events.bus import EventBus
from commerceos.events.constants import EventStatus, EventType, Priority, WorkflowJobStatus
from commerceos.events.dashboard import EventsDashboard
from commerceos.events.locking import LockManager
from commerceos.events.models import Event, WorkflowJob
from commerceos.events.scheduler import Scheduler
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork, sqlalchemy_events_uow
from commerceos.events.workflow import WorkflowEngine, step_refresh_kpis, step_refresh_commerce_state, step_generate_monitoring_snapshot, step_generate_intelligence, step_generate_decisions, register_default_workflows
from commerceos.platform.database.connection import create_all, get_session, reset_engine
from commerceos.platform.database.models import new_uuid


DB_URL = "sqlite:///test_events_integration.db"


@pytest.fixture
def sess():
    reset_engine()
    if os.path.exists("test_events_integration.db"):
        os.remove("test_events_integration.db")
    create_all(DB_URL)
    session = get_session(DB_URL)
    yield session
    session.close()
    reset_engine()


@pytest.fixture
def uow(sess):
    return SQLAlchemyEventsUnitOfWork(sess)


class TestEventBusIntegration:
    def test_full_event_lifecycle(self, uow, sess):
        bus = EventBus(sess, uow=uow)
        calls = []

        def handler(event):
            calls.append(event.event_type)

        bus.register(EventType.ORDERS_SYNCED.value, handler)
        event = bus.publish(EventType.ORDERS_SYNCED.value, "sync", "store-001", {"count": 10})
        assert event.status == EventStatus.PROCESSED.value
        assert len(calls) == 1

        # Verify dashboard
        dash = EventsDashboard(uow)
        summary = dash.get_event_summary()
        assert summary["events"]["total"] == 1
        assert summary["events"]["by_status"][EventStatus.PROCESSED.value] == 1

    def test_failed_event_dead_letter(self, uow, sess):
        bus = EventBus(sess, uow=uow)

        def bad_handler(event):
            raise RuntimeError("transient failure")

        bus.register(EventType.ORDERS_SYNCED.value, bad_handler)
        event = bus.publish(EventType.ORDERS_SYNCED.value, "sync", "store-001", {})
        assert event.status == EventStatus.FAILED.value

        # Dispatcher should move to dead letter after retries (not tested here because bus already ran)
        # But we can manually verify failure is recorded
        with uow:
            e = uow.events().get(event.id)
        assert e.status == EventStatus.FAILED.value

    def test_multiple_subscribers(self, uow, sess):
        bus = EventBus(sess, uow=uow)
        calls = []

        def h1(e):
            calls.append("h1")

        def h2(e):
            calls.append("h2")

        def h3(e):
            calls.append("h3")

        bus.register(EventType.ORDERS_SYNCED.value, h1)
        bus.register(EventType.ORDERS_SYNCED.value, h2)
        bus.register(EventType.ORDERS_SYNCED.value, h3)
        event = bus.publish(EventType.ORDERS_SYNCED.value, "sync", "store-001", {})
        assert event.status == EventStatus.PROCESSED.value
        assert sorted(calls) == ["h1", "h2", "h3"]


class TestWorkflowIntegration:
    def test_default_orders_synced_pipeline(self, uow, sess):
        engine = WorkflowEngine(sess, uow=uow)
        register_default_workflows(engine)
        job = engine.schedule("orders_synced_pipeline", {"store_id": "store-001"})
        result = engine.run(job.id)
        assert result["success"] is True
        assert result["status"] == WorkflowJobStatus.SUCCEEDED.value
        assert len(result["step_results"]) == 5

    def test_workflow_with_locking(self, uow, sess):
        engine = WorkflowEngine(sess, uow=uow)
        register_default_workflows(engine)
        job = engine.schedule("orders_synced_pipeline", {"store_id": "store-001"})
        lm = LockManager(sess, default_ttl_seconds=60)
        result = engine.run(job.id, lock_manager=lm)
        assert result["success"] is True
        assert lm.is_locked(f"workflow:orders_synced_pipeline:{job.id}") is False

    def test_workflow_queue_processing(self, uow, sess):
        engine = WorkflowEngine(sess, uow=uow)
        register_default_workflows(engine)
        for i in range(3):
            engine.schedule("orders_synced_pipeline", {"store_id": f"store-{i}"})
        results = engine.process_queue(limit=10)
        assert len(results) == 3
        assert all(r["success"] for r in results)

    def test_duplicate_prevention(self, uow, sess):
        engine = WorkflowEngine(sess, uow=uow)
        register_default_workflows(engine)
        job1 = engine.schedule("orders_synced_pipeline", {"store_id": "store-001"})
        lm = LockManager(sess, default_ttl_seconds=60)
        lm.acquire(f"workflow:orders_synced_pipeline:{job1.id}", f"workflow-{job1.id}", job_id=job1.id)
        # Second job cannot run under the same lock if it uses the same lock name; but each job has unique lock name
        # So test that a single job cannot be run twice concurrently
        result1 = engine.run(job1.id, lock_manager=lm)
        assert result1["success"] is False
        assert result1["error"] == "could not acquire lock"
        lm.release(f"workflow:orders_synced_pipeline:{job1.id}", f"workflow-{job1.id}")
        result2 = engine.run(job1.id, lock_manager=lm)
        assert result2["success"] is True


class TestSchedulerIntegration:
    def test_scheduler_runs_default_workflow(self, sess):
        scheduler = Scheduler(sess)
        scheduler.schedule_workflow("orders_synced_pipeline", {"store_id": "store-001"})
        results = scheduler.run_due()
        assert len(results) == 1
        assert results[0]["success"] is True
