import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ingestion Health", page_icon="🔄", layout="wide")

st.markdown("""
<style>
.status-ok { color: #28a745; font-weight: bold; }
.status-warn { color: #ffc107; font-weight: bold; }
.status-fail { color: #dc3545; font-weight: bold; }
.temp-badge { background: #fff3cd; color: #856404; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

st.title("🔄 Ingestion Health")
st.caption("Sync status, data freshness, and data quality from CommerceOS.")

from commerceos.dashboard.query_service import DashboardQueryService

STORE_ID = st.secrets.get("COMMERCEOS_STORE_ID", "store-1")

@st.cache_resource
def get_query_service():
    return DashboardQueryService()

qs = get_query_service()

# --- Sync Health Overview ---
st.subheader("Sync Status by Entity")

with qs:
    freshness = qs.get_freshness(STORE_ID)
    sync_runs = qs.get_sync_health(STORE_ID)

if freshness:
    cols = st.columns(len(freshness))
    for i, (entity, info) in enumerate(freshness.items()):
        with cols[i]:
            hours = info["hours_since_sync"]
            if hours < 1:
                st.success(f"🟢 **{entity}**\n{hours*60:.0f}m ago")
            elif hours < 24:
                st.warning(f"🟡 **{entity}**\n{hours:.1f}h ago")
            else:
                st.error(f"🔴 **{entity}**\n{hours/24:.1f}d ago")
else:
    st.info("No sync checkpoints recorded. Run a sync to populate.")

st.divider()

# --- Recent Sync Runs ---
st.subheader("Recent Sync Runs")
if sync_runs:
    df = pd.DataFrame(sync_runs[:20])
    st.dataframe(
        df[["connector_code", "entity_type", "sync_mode", "status", "records_received", "records_persisted", "records_failed", "completed_at"]],
        width='stretch',
        hide_index=True,
    )
else:
    st.info("No sync runs recorded.")

st.divider()

# --- Data Quality ---
st.subheader("Data Quality")
with qs:
    dq = qs.get_data_quality_summary(STORE_ID)

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Missing Provenance**")
    if dq["missing_provenance"]:
        st.dataframe(pd.DataFrame(dq["missing_provenance"]), width='stretch', hide_index=True)
    else:
        st.success("✅ All records have provenance")

with col2:
    st.markdown("**Recent Failures**")
    if dq["recent_failures"]:
        st.dataframe(pd.DataFrame(dq["recent_failures"]), width='stretch', hide_index=True)
    else:
        st.success("✅ No recent failures")

st.divider()

# --- Raw Payload Inspector ---
st.subheader("Raw Payload Inspector")
st.caption('<span class="temp-badge">TEMPORARY</span> Search for a specific order/campaign/ad to see all raw versions.', unsafe_allow_html=True)

with st.expander("Inspect Payload History"):
    st.markdown("Enter an external entity ID to see all raw payload versions.")
    external_id = st.text_input("External Entity ID (e.g., order_sn)")
    if external_id:
        from commerceos.ingestion.audit import payload_diff
        # This would need a session — simplified for now
        st.info(f"Payload history for {external_id} would show here.")

st.divider()
st.caption("PPMJ Platform | Payung Murah Jakarta | CommerceOS Ingestion Health")
