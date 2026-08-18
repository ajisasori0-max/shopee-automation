"""Knowledge page for the Web COO Dashboard."""
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(BASE_DIR))

from commerceos.config.settings import get_settings
from commerceos.coo.web_service import WebCOODashboardService
from commerceos.platform.database.connection import get_session

st.set_page_config(page_title="Knowledge — CommerceOS", page_icon="🧠", layout="wide")

SETTINGS = get_settings()
STORE_ID = st.secrets.get("COMMERCEOS_STORE_ID", "store-ppm-001")


@st.cache_resource(show_spinner=False)
def _get_session():
    return get_session(SETTINGS.database_url)


st.title("🧠 Knowledge")
st.caption("What CommerceOS remembers and what it has learned.")

session = _get_session()
service = WebCOODashboardService(session, store_id=STORE_ID)

days = st.sidebar.slider("Window (days)", 1, 90, 30)
query = st.sidebar.text_input("Search knowledge")

data = service.get_knowledge(days=days)
if query:
    search = service.search_knowledge(query, days=days)
else:
    search = None

if data.get("errors"):
    with st.expander("Warnings"):
        for error in data["errors"]:
            st.caption(f"⚠️ {error}")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Latest Weekly Summary")
    weekly = data.get("latest_weekly")
    if weekly:
        st.markdown(f"**{weekly.get('title', '—')}**")
        st.caption(f"{weekly.get('note_date', '—')} | {', '.join(weekly.get('tags', []))}")
        if st.button("Read weekly summary", key="weekly"):
            content = service.read_note(weekly["note_id"])
            if content:
                st.markdown(content.get("content", "—"))
            else:
                st.info("Summary file not available.")
    else:
        st.info("No weekly summary available.")

with col2:
    st.subheader("Latest Daily Note")
    daily = data.get("latest_daily")
    if daily:
        st.markdown(f"**{daily.get('title', '—')}**")
        st.caption(f"{daily.get('note_date', '—')} | {', '.join(daily.get('tags', []))}")
    else:
        st.info("No daily note available.")

st.divider()

if search:
    st.subheader(f"Search Results for \"{query}\"")
    results = search.get("results", [])
    if results:
        st.dataframe(pd.DataFrame(results), width='stretch', hide_index=True)
    else:
        st.info("No matching knowledge.")

st.divider()

st.subheader("Recent Lessons")
lessons = data.get("recent_lessons", [])
if lessons:
    for lesson in lessons[:10]:
        st.markdown(f"- **{lesson.get('title', '—')}** `{lesson.get('note_date', '—')}`")
else:
    st.info("No recent lessons.")

st.divider()

st.subheader("Timeline")
timeline = data.get("timeline", [])
if timeline:
    df = pd.DataFrame(timeline)
    display_cols = ["note_date", "note_type", "title", "tags"]
    st.dataframe(df[[c for c in display_cols if c in df.columns]], width='stretch', hide_index=True)
else:
    st.info("No knowledge timeline entries.")

st.divider()
st.caption("CommerceOS Web COO Dashboard | Knowledge")
