"""Tests for the automation runtime."""

import os

import pytest

from commerceos.jobs.factory import register_default_jobs
from commerceos.jobs.health import JobHealthReporter
from commerceos.jobs.runner import JobRunner
from commerceos.platform.database.connection import create_all, get_session, reset_engine


@pytest.fixture
def runtime_session():
    reset_engine()
    db_path = "test_jobs_runtime.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    db_url = f"sqlite:///{db_path}"
    create_all(db_url)
    session = get_session(db_url)
    yield session
    session.close()
    reset_engine()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def runtime_registry(runtime_session):
    return register_default_jobs(session=runtime_session)


@pytest.fixture
def runner(runtime_session, runtime_registry):
    return JobRunner(session=runtime_session, registry=runtime_registry)


def test_job_runner_logs_executions(runner, runtime_registry):
    results = runner.run_many(runtime_registry.names())
    assert len(results) == len(runtime_registry.names())
    assert all(r["execution_id"] for r in results)
    assert all(r["started_at"] for r in results)
    assert all(r["finished_at"] for r in results)


def test_job_runner_failed_job_is_recorded(runtime_session):
    registry = register_default_jobs(session=runtime_session)
    registry.register(
        name="always_fails",
        handler=lambda session, settings=None: (_ for _ in ()).throw(ValueError("boom")),
        group="test",
    )
    runner = JobRunner(session=runtime_session, registry=registry)
    result = runner.run("always_fails")
    assert result["status"] == "failed"
    assert "boom" in result["error"]
    assert result["execution_id"]


def test_job_runner_idempotent_key(runner, runtime_registry):
    definitions = runtime_registry.list_jobs()
    daily = definitions.get("daily_coo_brief")
    assert daily is not None
    assert daily.idempotency_key() is not None


def test_health_reporter_summary(runner, runtime_registry, runtime_session):
    runner.run_many(runtime_registry.names())
    reporter = JobHealthReporter(session=runtime_session, registry=runtime_registry)
    summary = reporter.summary()
    assert summary["total_executions"] >= len(runtime_registry.names())
    assert summary["failed_executions"] == 0
    assert summary["healthy"]


def test_health_reporter_overdue(runtime_session, runtime_registry):
    reporter = JobHealthReporter(session=runtime_session, registry=runtime_registry)
    overdue = reporter.overdue_jobs({"daily_coo_brief": 1})
    assert overdue  # never run, so overdue
    assert overdue[0]["name"] == "daily_coo_brief"


def test_health_reporter_recent_failures(runtime_session, runtime_registry):
    registry = register_default_jobs(session=runtime_session)
    registry.register(
        name="always_fails",
        handler=lambda session, settings=None: (_ for _ in ()).throw(ValueError("boom")),
        group="test",
    )
    runner = JobRunner(session=runtime_session, registry=registry)
    runner.run("always_fails")
    reporter = JobHealthReporter(session=runtime_session, registry=registry)
    failures = reporter.recent_failures(hours=24)
    assert len(failures) == 1
    assert failures[0]["job_name"] == "always_fails"
