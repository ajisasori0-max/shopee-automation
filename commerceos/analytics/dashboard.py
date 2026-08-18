"""Analytics dashboard helpers for Streamlit pages."""

from typing import Any, Dict

from sqlalchemy.orm import Session

from commerceos.analytics.engine import AdvancedAnalyticsEngine
from commerceos.analytics.finance import FinancialForecastingEngine
from commerceos.analytics.forecasting import DemandForecastingEngine
from commerceos.analytics.inventory import InventoryIntelligenceEngine
from commerceos.analytics.scenarios import ScenarioEngine


class AnalyticsDashboard:
    """Stable read-only API for analytics dashboards."""

    def __init__(self, session: Session, store_id: str = "store-ppm-001"):
        self.session = session
        self.store_id = store_id
        self.advanced = AdvancedAnalyticsEngine(session, store_id)
        self.finance = FinancialForecastingEngine(session, store_id)
        self.forecasting = DemandForecastingEngine(session, store_id)
        self.inventory = InventoryIntelligenceEngine(session, store_id)
        self.scenarios = ScenarioEngine(session, store_id)

    def summary(self, days: int = 30) -> Dict[str, Any]:
        return self.advanced.summary(days=days)

    def financial_summary(self, days: int = 30, forecast_days: int = 30) -> Dict[str, Any]:
        return self.finance.summary(days=days, forecast_days=forecast_days)

    def inventory_recommendations(self) -> Dict[str, Any]:
        return self.inventory.recommend()

    def run_scenario(self, scenario_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        return self.scenarios.run(scenario_type, parameters)
