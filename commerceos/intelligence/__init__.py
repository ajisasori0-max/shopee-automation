"""Intelligence package public API."""

from commerceos.intelligence.dashboard import (
    IntelligenceDashboard,
    get_business_summary,
    get_daily_insights,
    get_priority_insights,
    get_trend_summary,
)
from commerceos.intelligence.engine import IntelligenceEngine
from commerceos.intelligence.models import Insight, TrendSnapshot
from commerceos.intelligence.reporters.obsidian import ObsidianIntelligenceReport
from commerceos.intelligence.reporters.telegram import TelegramBriefGenerator
from commerceos.intelligence.sqlalchemy_repositories import (
    SQLAlchemyIntelligenceUnitOfWork,
    sqlalchemy_intelligence_uow,
)

__all__ = [
    "Insight",
    "TrendSnapshot",
    "IntelligenceDashboard",
    "IntelligenceEngine",
    "ObsidianIntelligenceReport",
    "TelegramBriefGenerator",
    "SQLAlchemyIntelligenceUnitOfWork",
    "get_business_summary",
    "get_daily_insights",
    "get_priority_insights",
    "get_trend_summary",
    "sqlalchemy_intelligence_uow",
]
