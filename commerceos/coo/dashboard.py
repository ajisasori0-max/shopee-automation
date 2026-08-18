"""COO Interface dashboard helpers for Streamlit pages.

Provides a thin wrapper so Mission Control can render COO answers without
duplicating context-engine wiring.
"""

from typing import Any, Dict

from sqlalchemy.orm import Session

from commerceos.config.settings import Settings, get_settings
from commerceos.coo.interface import COOInterface


class COODashboard:
    """Stable read-only API for the COO Interface in Streamlit dashboards."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.interface = COOInterface(session, settings)

    def ask(self, query: str) -> Dict[str, Any]:
        """Return the full structured COO response as a dict."""
        return self.interface.ask(query).to_dict()

    def what_matters_today(self) -> Dict[str, Any]:
        return self.interface.ask("What matters today?").to_dict()

    def what_changed_this_week(self) -> Dict[str, Any]:
        return self.interface.ask("What changed this week?").to_dict()

    def pending_approvals(self) -> Dict[str, Any]:
        return self.interface.ask("What should I approve?").to_dict()

    def unresolved_decisions(self) -> Dict[str, Any]:
        return self.interface.ask("What decisions are unresolved?").to_dict()
