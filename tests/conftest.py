"""Shared test fixtures for Decision Engine, Execution Engine, and Event Bus tests."""

import os

import pytest

from commerceos.decision.sqlalchemy_repositories import SQLAlchemyDecisionUnitOfWork
from commerceos.events.sqlalchemy_repositories import SQLAlchemyEventsUnitOfWork
from commerceos.execution.sqlalchemy_repositories import SQLAlchemyExecutionUnitOfWork
from commerceos.platform.database.connection import create_all, get_session, reset_engine


class _BothUows:
    def __init__(self, session):
        self.session = session
        self.decision = SQLAlchemyDecisionUnitOfWork(session)
        self.execution = SQLAlchemyExecutionUnitOfWork(session)


@pytest.fixture
def sqlite_uow():
    db_url = "sqlite:///test_decision_unit.db"
    reset_engine()
    if os.path.exists("test_decision_unit.db"):
        os.remove("test_decision_unit.db")
    create_all(db_url)
    session = get_session(db_url)
    uow = SQLAlchemyDecisionUnitOfWork(session)
    try:
        yield uow
    finally:
        session.close()
        reset_engine()
        if os.path.exists("test_decision_unit.db"):
            os.remove("test_decision_unit.db")


@pytest.fixture
def sqlite_both_uows():
    db_url = "sqlite:///test_both_unit.db"
    reset_engine()
    if os.path.exists("test_both_unit.db"):
        os.remove("test_both_unit.db")
    create_all(db_url)
    session = get_session(db_url)
    both = _BothUows(session)
    try:
        yield both
    finally:
        session.close()
        reset_engine()
        if os.path.exists("test_both_unit.db"):
            os.remove("test_both_unit.db")


@pytest.fixture
def execution_sqlite_uow():
    db_url = "sqlite:///test_execution_unit.db"
    reset_engine()
    if os.path.exists("test_execution_unit.db"):
        os.remove("test_execution_unit.db")
    create_all(db_url)
    session = get_session(db_url)
    uow = SQLAlchemyExecutionUnitOfWork(session)
    try:
        yield uow
    finally:
        session.close()
        reset_engine()
        if os.path.exists("test_execution_unit.db"):
            os.remove("test_execution_unit.db")


@pytest.fixture
def events_sqlite_uow():
    db_url = "sqlite:///test_events_unit.db"
    reset_engine()
    if os.path.exists("test_events_unit.db"):
        os.remove("test_events_unit.db")
    create_all(db_url)
    session = get_session(db_url)
    uow = SQLAlchemyEventsUnitOfWork(session)
    try:
        yield uow
    finally:
        session.close()
        reset_engine()
        if os.path.exists("test_events_unit.db"):
            os.remove("test_events_unit.db")
