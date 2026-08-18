"""Tests for OAT verification."""

import os

import pytest

from commerceos.platform.database.connection import create_all, get_session, reset_engine
from scripts.oat_verification import OATVerification


@pytest.fixture
def oat_session():
    reset_engine()
    db_path = "test_oat.db"
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


def test_oat_report_structure(oat_session):
    verifier = OATVerification(oat_session)
    report = verifier.run_all()
    assert "overall" in report
    assert "passed" in report
    assert "failed" in report
    assert "total" in report
    assert "findings" in report
    assert report["total"] > 0


def test_oat_data_health_checks(oat_session):
    verifier = OATVerification(oat_session)
    verifier.verify_data_health()
    names = [f["name"] for f in verifier.findings]
    assert "data_health.freshness" in names
    assert "data_health.kpi_availability" in names
    assert "data_health.missing_data" in names


def test_oat_knowledge_flow_checks(oat_session):
    verifier = OATVerification(oat_session)
    verifier.verify_knowledge_flow()
    names = [f["name"] for f in verifier.findings]
    assert "knowledge_flow.recent_notes" in names
    assert "knowledge_flow.retrieval_works" in names


def test_oat_operational_flow_checks(oat_session):
    verifier = OATVerification(oat_session)
    verifier.verify_operational_flow()
    names = [f["name"] for f in verifier.findings]
    assert "operational_flow.monitoring_active" in names
    assert "operational_flow.monitoring_healthy" in names
    assert "operational_flow.alerts_visible" in names
