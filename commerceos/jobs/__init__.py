"""Automation runtime for CommerceOS."""

from commerceos.jobs.registry import JobDefinition, JobRegistry
from commerceos.jobs.runner import JobRunner
from commerceos.jobs.health import JobHealthReporter

__all__ = [
    "JobDefinition",
    "JobRegistry",
    "JobRunner",
    "JobHealthReporter",
    "build_default_registry",
]


def build_default_registry(
    session=None,
    settings=None,
    monitoring_service=None,
    knowledge_reporter=None,
) -> JobRegistry:
    """Build the standard CommerceOS job registry with default handlers."""
    from commerceos.jobs.factory import register_default_jobs

    return register_default_jobs(
        session=session,
        settings=settings,
        monitoring_service=monitoring_service,
        knowledge_reporter=knowledge_reporter,
    )
