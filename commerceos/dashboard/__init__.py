"""Dashboard read layer for CommerceOS.

This package provides the stable API that Streamlit pages consume.
Pages must not import SQLAlchemy models, legacy engines, or Shopee APIs directly.
"""

from commerceos.dashboard.query_service import DashboardQueryService

__all__ = ["DashboardQueryService"]
