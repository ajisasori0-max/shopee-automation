"""Timeline page for the Web COO Dashboard."""
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.coo.web_service import WebCOODashboardService
from commerceos.platform.database.connection import get_session

st.set_page_config(page_title="Timeline — CommerceOS", page_icon="📅", layout="wide")

SETTINGS = get_settings()
STORE_ID = st.secrets.get("COMMERCEOS_STORE_ID", "store-ppm-001")


@st.cache_resource(show_spinner=False)
def _get_session():
    return get_session(SETTINGS.database_url)


st.title("📅 Business Timeline")
st.caption("What happened across sync, events, decisions, executions, experiments, and knowledge.")

session = _get_session()
service = WebCOODashboardService(session, store_id=STORE_ID)

hours = st.sidebar.slider("Window (hours)", 1, 168, 24)
data = service.get_timeline(hours=hours)

if data.get("errors"):
    with st.expander("Warnings"):
        for error in data["errors"]:
            st.caption(f"⚠️ {error}")

items = data.get("items", [])
if not items:
    st.info("No timeline events in the selected window.")
else:
    type_filter = st.multiselect("Filter by type", sorted({i.get("type") for i in items}), default=sorted({i.get("type") for i in items}))
    filtered = [i for i in items if i.get("type") in type_filter]

    st.markdown(f"Showing **{len(filtered)}** events")
    df = pd.DataFrame(filtered)
    display = [c for c in ["timestamp", "type", "title", "status", "id"] if c in df.columns]
    st.dataframe(df[display], width='stretch', hide_index=True)

    for item in filtered[:20]:
        with st.expander(f"[{item.get('type', '—').upper()}] {item.get('title', '—')} @ {item.get('timestamp', '—')}", expanded=False):
            st.json(item.get("details", {}))

st.divider()
st.caption("CommerceOS Web COO Dashboard | Timeline")
