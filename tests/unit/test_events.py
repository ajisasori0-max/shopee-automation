"""Unit tests for Event Bus and Workflow Orchestration."""

import pytest

from commerceos.events.bus import EventBus, publish_event
from commerceos.events.constants import EventStatus, EventType, Priority, WorkflowJobStatus, is_retryable_error
from commerceos.events.dashboard import EventsDashboard
from commerceos.events.dead_letter import DeadLetterManager
from commerceos.events.handlers import Handlers, log_handler
from commerceos.events.locking import LockManager
from commerceos.events.models import DistributedLock, Event, EventSubscription, WorkflowHistory, WorkflowJob
from commerceos.events.registry import HandlerRegistry
from commerceos.events.retry import RetryManager
from commerceos.events.scheduler import Scheduler
from commerceos.events.workflow import WorkflowEngine, register_default_workflows, step_refresh_kpis


class TestConstants:
    def test_is_retryable_transient(self):
        assert is_retryable_error("timeout") is True
        assert is_retryable_error("lock_conflict") is True

    def test_is_retryable_non_retryable(self):
        assert is_retryable_error("validation") is False
        assert is_retryable_error("auth") is False


class TestHandlerRegistry:
    def test_register_and_retrieve(self):
        registry = HandlerRegistry()
        handler = lambda e: None
        registry.register(EventType.ORDERS_SYNCED.value, handler)
        assert registry.handlers_for(EventType.ORDERS_SYNCED.value) == [handler]

    def test_unregister(self):
        registry = HandlerRegistry()
        handler = lambda e: None
        registry.register(EventType.ORDERS_SYNCED.value, handler)
        registry.unregister(EventType.ORDERS_SYNCED.value, handler)
        assert registry.handlers_for(EventType.ORDERS_SYNCED.value) == []


class TestEventBus:
    def test_publish_event(self, events_sqlite_uow):
        bus = EventBus(events_sqlite_uow.session, uow=events_sqlite_uow)
        bus.register(EventType.ORDERS_SYNCED.value, log_handler)
        event = bus.publish(
            EventType.ORDERS_SYNCED.value,
            aggregate_type="sync",
            aggregate_id="store-001",
            payload={"count": 5},
        )
        assert event.status == EventStatus.PROCESSED.value
        assert event.payload["count"] == 5

    def test_publish_no_handlers_becomes_processed(self, events_sqlite_uow):
        bus = EventBus(events_sqlite_uow.session, uow=events_sqlite_uow)
        event = bus.publish(
            EventType.PAYMENTS_SYNCED.value,
            aggregate_type="sync",
            aggregate_id="store-001",
            payload={},
        )
        assert event.status == EventStatus.PROCESSED.value

    def test_subscribe_and_unsubscribe(self, events_sqlite_uow):
        bus = EventBus(events_sqlite_uow.session, uow=events_sqlite_uow)
        sub = bus.subscribe(EventType.ORDERS_SYNCED.value, "log_handler")
        assert sub.enabled is True
        assert bus.unsubscribe(EventType.ORDERS_SYNCED.value, "log_handler") is True
        with events_sqlite_uow:
            s = events_sqlite_uow.subscriptions().get(EventType.ORDERS_SYNCED.value, "log_handler")
        assert s.enabled is False

    def test_multiple_handlers(self, events_sqlite_uow):
        calls = []

        def h1(e):
            calls.append("h1")

        def h2(e):
            calls.append("h2")

        bus = EventBus(events_sqlite_uow.session, uow=events_sqlite_uow)
        bus.register(EventType.ORDERS_SYNCED.value, h1)
        bus.register(EventType.ORDERS_SYNCED.value, h2)
        bus.publish(EventType.ORDERS_SYNCED.value, "sync", "store-001", {})
        assert calls == ["h1", "h2"]

    def test_failed_handler_marks_event_failed(self, events_sqlite_uow):
        def bad_handler(e):
            raise ValueError("boom")

        bus = EventBus(events_sqlite_uow.session, uow=events_sqlite_uow)
        bus.register(EventType.ORDERS_SYNCED.value, bad_handler)
        event = bus.publish(EventType.ORDERS_SYNCED.value, "sync", "store-001", {})
        assert event.status == EventStatus.FAILED.value

    def test_publish_event_convenience(self, events_sqlite_uow):
        event = publish_event(
            events_sqlite_uow.session,
            EventType.ORDERS_SYNCED.value,
            "sync",
            "store-001",
            {"count": 3},
        )
        assert event.event_type == EventType.ORDERS_SYNCED.value


class TestRetryManager:
    def test_should_retry(self):
        rm = RetryManager()
        assert rm.should_retry(1, "timeout") is True
        assert rm.should_retry(3, "timeout") is False
        assert rm.should_retry(1, "validation") is False

    def test_backoff_seconds(self):
        rm = RetryManager(base_backoff_seconds=2.0)
        assert rm.backoff_seconds(1) == 2.0
        assert rm.backoff_seconds(2) == 4.0


class TestDeadLetterManager:
    def test_move_to_dead_letter(self, events_sqlite_uow):
        event = Event(
            event_type=EventType.ORDERS_SYNCED.value,
            aggregate_type="sync",
            aggregate_id="store-001",
            payload={},
            status=EventStatus.FAILED.value,
            attempt_count=3,
        )
        with events_sqlite_uow:
            events_sqlite_uow.events().save(event)
        dl = DeadLetterManager(events_sqlite_uow.session, uow=events_sqlite_uow)
        entry = dl.move(event, reason="max retries exceeded")
        assert entry.event_id == event.id
        assert entry.retry_allowed is True
        with events_sqlite_uow:
            e = events_sqlite_uow.events().get(event.id)
        assert e.status == EventStatus.DEAD_LETTER.value

    def test_retry_dead_letter(self, events_sqlite_uow):
        event = Event(
            event_type=EventType.ORDERS_SYNCED.value,
            aggregate_type="sync",
            aggregate_id="store-001",
            payload={},
            status=EventStatus.DEAD_LETTER.value,
        )
        with events_sqlite_uow:
            events_sqlite_uow.events().save(event)
        dl = DeadLetterManager(events_sqlite_uow.session, uow=events_sqlite_uow)
        retried = dl.retry(event.id)
        assert retried is not None
        assert retried.status == EventStatus.FAILED.value


class TestLockManager:
    def test_acquire_and_release(self, events_sqlite_uow):
        lm = LockManager(events_sqlite_uow.session, default_ttl_seconds=60)
        assert lm.acquire("sync:store-001", "owner-1") is True
        assert lm.acquire("sync:store-001", "owner-2") is False
        assert lm.release("sync:store-001", "owner-1") is True
        assert lm.release("sync:store-001", "owner-1") is False

    def test_acquire_expired_lock(self, events_sqlite_uow):
        lm = LockManager(events_sqlite_uow.session, default_ttl_seconds=-1)
        assert lm.acquire("sync:store-002", "owner-1") is True
        lm2 = LockManager(events_sqlite_uow.session, default_ttl_seconds=60)
        assert lm2.acquire("sync:store-002", "owner-2") is True

    def test_is_locked(self, events_sqlite_uow):
        lm = LockManager(events_sqlite_uow.session, default_ttl_seconds=60)
        assert lm.is_locked("sync:store-003") is False
        lm.acquire("sync:store-003", "owner-1")
        assert lm.is_locked("sync:store-003") is True


class TestWorkflowEngine:
    def test_define_and_run_workflow(self, events_sqlite_uow):
        engine = WorkflowEngine(events_sqlite_uow.session, uow=events_sqlite_uow)
        engine.define("test_workflow", [step_refresh_kpis])
        job = engine.schedule("test_workflow", {"store_id": "store-001"})
        result = engine.run(job.id)
        assert result["success"] is True
        assert result["status"] == WorkflowJobStatus.SUCCEEDED.value
        with events_sqlite_uow:
            history = events_sqlite_uow.workflows().get_history(job.id)
        assert len(history) == 2
    def test_define_and_run_workflow(self, events_sqlite_uow):
        engine = WorkflowEngine(events_sqlite_uow.session, uow=events_sqlite_uow)
        engine.define("test_workflow", [step_refresh_kpis])
        job = engine.schedule("test_workflow", {"store_id": "store-001"})
        result = engine.run(job.id)
        assert result["success"] is True
        assert result["status"] == WorkflowJobStatus.SUCCEEDED.value
        with events_sqlite_uow:
            history = events_sqlite_uow.workflows().get_history(job.id)
        assert len(history) >= 2

    def test_workflow_retry(self, events_sqlite_uow):
        engine = WorkflowEngine(events_sqlite_uow.session, uow=events_sqlite_uow)

        def failing_step(job, payload):
            raise RuntimeError("temporary")

        engine.define("failing", [failing_step])
        job = engine.schedule("failing", {})
        result = engine.run(job.id)
        assert result["success"] is False
        assert result["status"] == WorkflowJobStatus.FAILED.value

        # Retry should reset and run again
        result2 = engine.attempt_retry(job.id)
        assert result2["success"] is False
        with events_sqlite_uow:
            j = events_sqlite_uow.workflows().get(job.id)
        assert j.retry_count >= 1

    def test_cancel_workflow(self, events_sqlite_uow):
        engine = WorkflowEngine(events_sqlite_uow.session, uow=events_sqlite_uow)
        engine.define("test_workflow", [step_refresh_kpis])
        job = engine.schedule("test_workflow", {})
        result = engine.cancel(job.id)
        assert result["success"] is True
        assert result["status"] == WorkflowJobStatus.CANCELLED.value


class TestScheduler:
    def test_schedule_workflow(self, events_sqlite_uow):
        scheduler = Scheduler(events_sqlite_uow.session)
        job = scheduler.schedule_workflow("orders_synced_pipeline", {"store_id": "store-001"})
        assert job.workflow_name == "orders_synced_pipeline"
        assert job.status == WorkflowJobStatus.QUEUED.value

    def test_run_due(self, events_sqlite_uow):
        scheduler = Scheduler(events_sqlite_uow.session)
        scheduler.schedule_workflow("orders_synced_pipeline", {"store_id": "store-001"})
        results = scheduler.run_due()
        assert len(results) == 1
        assert results[0]["success"] is True


class TestDashboard:
    def test_get_event_summary(self, events_sqlite_uow):
        bus = EventBus(events_sqlite_uow.session, uow=events_sqlite_uow)
        bus.publish(EventType.ORDERS_SYNCED.value, "sync", "store-001", {})
        dash = EventsDashboard(events_sqlite_uow)
        summary = dash.get_event_summary()
        assert summary["events"]["total"] == 1
        assert summary["dead_letters"] == 0

    def test_get_workflow(self, events_sqlite_uow):
        engine = WorkflowEngine(events_sqlite_uow.session, uow=events_sqlite_uow)
        engine.define("test", [step_refresh_kpis])
        job = engine.schedule("test", {})
        engine.run(job.id)
        dash = EventsDashboard(events_sqlite_uow)
        data = dash.get_workflow(job.id)
        assert data["status"] == WorkflowJobStatus.SUCCEEDED.value
        assert data["history"]


class TestHandlers:
    def test_log_handler(self):
        event = Event(event_type=EventType.ORDERS_SYNCED.value, aggregate_type="sync", aggregate_id="s1", payload={})
        log_handler(event)
        assert event.metadata_.get("log_handler_seen") is True

    def test_handlers_registry(self):
        assert "log_handler" in Handlers.all()
