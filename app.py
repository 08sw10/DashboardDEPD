"""
DEPD Sindh — Live Organization & Funding Management Dashboard
Main Streamlit Application Entrypoint.
Department of Empowerment of Persons with Disabilities, Government of Sindh.
"""

import os
import time
import datetime
import logging
from typing import Tuple, List
import streamlit as st
import pandas as pd
from streamlit_folium import st_folium

from src.config import Config
from src.kobo_client import fetch_kobo_submissions
from src.sheets_client import fetch_google_sheets_records, write_records_to_google_sheets
from src.data_processor import (
    process_kobo_submissions,
    process_google_sheets_records,
    merge_kobo_and_financial_data,
    format_currency_pkr
)
from src.map_builder import build_sindh_gis_map
from src.data_quality import (
    compute_data_quality_metrics,
    get_missing_gis_records,
    get_missing_registration_records,
    get_missing_financial_records,
    get_duplicate_id_records
)
from src.ui import (
    inject_custom_css,
    render_header,
    render_status_bar,
    render_kpi_cards,
    render_sidebar_filters,
    render_overview_charts,
    render_organizations_table
)
from data.sample_data import get_sample_kobo_submissions, get_sample_google_sheets_records

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="DEPD Sindh — Organization & Funding Dashboard",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS
inject_custom_css()

# ── Automatic refresh ─────────────────────────────────────────────────────────
# Data itself is cached with @st.cache_data(ttl=300), so live APIs are re-read at
# most every 5 minutes. The guarded fragment below additionally pushes a visible
# full-app refresh on the same cadence.
#
# SAFETY: an st.fragment(run_every=...) executes its body immediately on render.
# An unguarded st.rerun() there causes an infinite rerun loop (blank page). The
# timestamp guard makes the FIRST invocation a no-op, so a rerun only happens
# once the interval has genuinely elapsed.
AUTO_REFRESH_MINUTES = getattr(Config, "AUTO_REFRESH_MINUTES", 5) or 0


def _auto_refresh_ticker():
    interval_seconds = AUTO_REFRESH_MINUTES * 60
    now = time.time()
    last = st.session_state.get("_depd_last_autorefresh")

    if last is None:                        # first render — arm the timer only
        st.session_state["_depd_last_autorefresh"] = now
        return

    if now - last >= interval_seconds - 5:  # interval elapsed — refresh data
        st.session_state["_depd_last_autorefresh"] = now
        st.cache_data.clear()
        st.rerun(scope="app")


if AUTO_REFRESH_MINUTES > 0:
    _auto_refresh_ticker = st.fragment(run_every=f"{AUTO_REFRESH_MINUTES}m")(_auto_refresh_ticker)

@st.cache_data(ttl=300, show_spinner=False)
def load_all_dashboard_data() -> Tuple[pd.DataFrame, bool, datetime.datetime, List[str]]:
    """
    Fetches, cleans, and merges live data from KoboToolbox and Google Sheets.
    Falls back gracefully to high-fidelity schema-matched data if credentials are not configured.
    Returns (merged_df, is_live, last_updated_time, info_messages).
    """
    info_messages = []
    last_updated = datetime.datetime.now()

    force_cache = os.getenv("DEPD_FORCE_CACHE") == "1"

    kobo_data = []
    sheets_data = []
    kobo_from_api = False
    sheets_from_api = False

    # 1. Fetch Kobo Data.
    #    fetch_kobo_submissions() already tries the live API first and transparently
    #    falls back to its on-disk snapshot on failure, returning (rows, notice).
    #    We must USE those cached rows instead of discarding them.
    if Config.is_kobo_configured() or force_cache:
        raw_kobo, kobo_err = fetch_kobo_submissions()
        if raw_kobo:
            kobo_data = raw_kobo
            kobo_from_api = True
            if kobo_err:  # cached snapshot served with a fallback notice
                info_messages.append(f"Kobo API Notice: {kobo_err}")
        elif kobo_err:
            info_messages.append(f"Kobo API Notice: {kobo_err}")
    else:
        info_messages.append("KoboToolbox API credentials not set. Using built-in verified sample dataset.")

    # 2. Fetch Google Sheets Data (same live -> disk-cache fallback contract).
    if Config.is_sheets_configured() or force_cache:
        raw_sheets, sheets_err = fetch_google_sheets_records()
        if raw_sheets:
            sheets_data = raw_sheets
            sheets_from_api = True
            if sheets_err:  # cached snapshot served with a fallback notice
                info_messages.append(f"Google Sheets Notice: {sheets_err}")
        elif sheets_err:
            info_messages.append(f"Google Sheets Notice: {sheets_err}")
    else:
        info_messages.append("Google Sheets credentials not set. Using built-in verified budget dataset.")

    # Fallback to sample data only when a source yielded nothing at all
    # (i.e. credentials missing AND no cached snapshot available) — never leaves the dashboard blank.
    if not kobo_data:
        kobo_data = get_sample_kobo_submissions()
    if not sheets_data:
        sheets_data = get_sample_google_sheets_records()

    # Treat the data as "live" when BOTH sources are API-backed (live or cached snapshot).
    # When a cached snapshot is in play, render_status_bar() still forces the yellow
    # "Cached Snapshot" badge via cache_notice, so the green badge implies true live data.
    is_live = kobo_from_api and sheets_from_api

    # 3. Process and Merge
    org_df = process_kobo_submissions(kobo_data)
    fin_df = process_google_sheets_records(sheets_data)
    merged_df = merge_kobo_and_financial_data(org_df, fin_df)

    logger.info(
        "Data load: kobo_rows=%d sheets_rows=%d live=%s",
        len(kobo_data), len(sheets_data), is_live
    )

    return merged_df, is_live, last_updated, info_messages

def main():
    # Start the guarded auto-refresh ticker (no-op on its first invocation)
    if AUTO_REFRESH_MINUTES > 0:
        _auto_refresh_ticker()

    # --- Developer-only toggle to test offline fallback ---
    if st.sidebar.checkbox("🧪 Simulate API offline (dev)", value=False):
        os.environ["DEPD_FORCE_CACHE"] = "1"
    else:
        os.environ.pop("DEPD_FORCE_CACHE", None)

    # Sidebar data refresh button
    st.sidebar.markdown("### 🔄 Data Controls")
    if st.sidebar.button("Refresh Live Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    if AUTO_REFRESH_MINUTES > 0:
        st.sidebar.caption(f"⏱️ Auto-refresh every {AUTO_REFRESH_MINUTES} min (cache TTL 5 min)")
    else:
        st.sidebar.caption("🖱️ Click above to pull the latest live data")

    # --- Optional Google Sheets sync (feature-flagged) ---
    with st.sidebar.expander("⬆️ Sync Kobo → Google Sheets", expanded=False):
        enable_sync = st.checkbox(
            "Enable Google Sheets sync", value=False, key="depd_sheets_sync_enabled"
        )
        if enable_sync:
            if not Config.is_sheets_configured():
                st.warning(
                    "Sheets credentials are missing here. **On Streamlit Cloud:** "
                    "open **⚙️ Manage app → Settings → Secrets** and paste the full "
                    "content of `secrets/cloud_secrets_ready.toml` "
                    "(regenerate locally with `python scripts/build_cloud_secrets.py`) — "
                    "it must include `GOOGLE_SHEET_ID` and a non-empty "
                    "`GOOGLE_SERVICE_ACCOUNT_JSON = '''…'''`. Then **restart the app**. "
                    "**Locally:** `.streamlit/secrets.toml` + `secrets/service_account.json`. "
                    "Sharing the Sheet with the service account's `client_email` as "
                    "**Editor** is also required for writing."
                )
            elif st.button("Sync live data now", use_container_width=True, key="depd_sheets_sync_now"):
                with st.spinner("Writing live Kobo rows to Google Sheets..."):
                    kobo_rows, kobo_err = fetch_kobo_submissions()
                    if not kobo_rows:
                        st.error(f"Nothing to sync: {kobo_err or 'no rows fetched'}")
                    else:
                        written, write_err = write_records_to_google_sheets(kobo_rows)
                        if write_err:
                            st.error(write_err)
                        else:
                            st.success(f"Synced {written} rows to Google Sheets.")

    # Load data
    with st.spinner("Synchronizing DEPD Dashboard Data..."):
        df, is_live, last_updated, messages = load_all_dashboard_data()

    # Render Government Header
    render_header()

    # Extract first cache-fallback notice if any (for yellow badge)
    cache_notice = next((m for m in messages if "snapshot from" in m.lower()), None)

    # Render Status Bar
    render_status_bar(is_live, last_updated, cache_notice=cache_notice, row_count=len(df))

    # Demo-mode diagnostic sidebar expander
    if not is_live:
        with st.sidebar.expander("⚠️ Demo Mode — why?", expanded=False):
            st.markdown("**Credential check** (key names only — values never shown):")

            required_keys = [
                ("KOBO_ASSET_UID", "Kobo asset UID"),
                ("KOBO_TOKEN", "Kobo API token"),
                ("KOBO_EXPORT_SETTINGS_UID", "Kobo CSV export UID"),
                ("GOOGLE_SHEET_ID", "Google Sheet ID"),
                ("GOOGLE_SERVICE_ACCOUNT_JSON", "Service account JSON (or secrets/service_account.json)"),
            ]

            # Inspect st.secrets load status WITHOUT exposing any values.
            # Only the exception class name is shown — messages can quote file
            # contents (including secret lines), so they must never be rendered.
            present_keys = set()
            secrets_error_hint = None
            try:
                present_keys = set(st.secrets.keys())
            except Exception as exc:  # Streamlit wraps BOTH cases in StreamlitSecretNotFoundError
                # Empirically verified: a missing secrets file raises
                # StreamlitSecretNotFoundError with "No secrets found. Valid
                # paths ...", while a broken TOML file raises the SAME exception
                # class with "Error parsing secrets file at <path>: ...".
                # So the class name cannot distinguish them — classify by message
                # content instead. Only curated hints are shown: exception text
                # can contain file paths / parser locations, so it is never
                # rendered as-is.
                exc_msg = str(exc)
                if (
                    isinstance(exc, FileNotFoundError)
                    or "No secrets found" in exc_msg
                ):
                    secrets_error_hint = (
                        "No Streamlit secrets file was found. "
                        "Locally: create `.streamlit/secrets.toml`. "
                        "On Streamlit Community Cloud: paste it via "
                        "**⚙️ Manage app → Settings → Secrets** (it is NOT in the repo — "
                        "`.gitignore` excludes it on purpose)."
                    )
                else:
                    secrets_error_hint = (
                        "Secrets exist but failed to parse as TOML. "
                        "Common causes: an unclosed quote, a real line-break inside "
                        "a `\"...\"` string (use `'''...'''` for the multi-line "
                        "service-account JSON), or a smart-quote copied from a "
                        "chat/document."
                    )

            if secrets_error_hint:
                st.error(secrets_error_hint)

            sa_inline = False
            for key, label in required_keys:
                in_file = key in present_keys
                value = None
                if in_file:
                    try:
                        value = st.secrets.get(key)
                    except Exception:
                        value = None
                env_value = os.getenv(key)
                # Resolution mirrors src.config.get_secret(): st.secrets → env → default
                resolved = value if (in_file and value not in (None, "")) else (
                    env_value if (env_value and env_value.strip()) else None
                )
                if key == "GOOGLE_SERVICE_ACCOUNT_JSON":
                    sa_inline = bool(value not in (None, ""))
                if resolved:
                    st.markdown(f"✅ `{key}` — {label}")
                else:
                    st.markdown(f"❌ `{key}` — {label} **missing**")

            # Sheets fallback file (only relevant when the inline JSON key is empty)
            sa_ok = bool(
                sa_inline
                or os.path.exists("secrets/service_account.json")
                or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            )
            if not sa_ok:
                st.markdown(
                    "❌ No Google service-account credentials: paste the JSON inline "
                    "into `GOOGLE_SERVICE_ACCOUNT_JSON = '''{...}'''` "
                    "(the `secrets/service_account.json` file is not deployed to the cloud)."
                )

            st.markdown(
                """
                **To enable live data:**

                **On Streamlit Community Cloud** (the repo cannot contain secrets):

                1. Open **⚙️ Manage app → Settings → Secrets**
                2. Paste the full content of your local
                   `.streamlit/secrets.toml` — with `GOOGLE_SERVICE_ACCOUNT_JSON`
                   filled in as a `'''…'''` multi-line string (the file
                   `secrets/service_account.json` does **not** exist in the cloud).
                3. Click **Save** → **⚙️ Manage app → Restart app**.
                4. Confirm the green **● Live Data** badge.

                **Locally:** ensure `.streamlit/secrets.toml` and
                `secrets/service_account.json` exist, share the Sheet with the
                service account's `client_email`, then restart Streamlit.

                See README → *Security & Credentials Policy* for details.
                """
            )

    # Show info notices in expandable box if any (always visible, including
    # cache-fallback notices served while live APIs are temporarily down)
    if messages:
        with st.expander("ℹ️ Data Source & System Notices", expanded=bool(cache_notice)):
            for msg in messages:
                st.info(msg)

    # Apply Sidebar Filters
    filtered_df = render_sidebar_filters(df)

    # Render Main KPIs (dynamically updated with filters)
    render_kpi_cards(filtered_df)

    # Main Navigation Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Executive Dashboard",
        "🏢 Organizations",
        "💰 Funding & Utilization",
        "🗺️ Sindh GIS Map",
        "🔍 Data Quality & Auditing"
    ])

    # -------------------------------------------------------------
    # TAB 1: EXECUTIVE DASHBOARD
    # -------------------------------------------------------------
    with tab1:
        render_overview_charts(filtered_df)

        # Accessibility & Infrastructure Breakdown Cards
        st.markdown("<div class='content-card'><div class='content-card-title'>♿ Accessibility & Infrastructure Overview</div>", unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            wc_count = int((filtered_df["wheelchair"] == "Yes").sum()) if "wheelchair" in filtered_df.columns else 0
            wc_pct = (wc_count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
            st.metric("Wheelchair Accessible", f"{wc_count} ({wc_pct:.0f}%)", help="Facilities with wheelchair accessibility")
        with col_b:
            sl_count = int((filtered_df["sign_language"] == "Yes").sum()) if "sign_language" in filtered_df.columns else 0
            sl_pct = (sl_count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
            st.metric("Sign Language Available", f"{sl_count} ({sl_pct:.0f}%)", help="Organizations providing sign language support")
        with col_c:
            owned_count = int((filtered_df["building_type"] == "Owned").sum()) if "building_type" in filtered_df.columns else 0
            st.metric("Owned Buildings", f"{owned_count}", help="Organizations with owned physical premises")
        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 2: ORGANIZATIONS DIRECTORY
    # -------------------------------------------------------------
    with tab2:
        render_organizations_table(filtered_df)

        # Organization Detail Inspector
        if not filtered_df.empty:
            st.markdown("<div class='content-card'><div class='content-card-title'>🔍 Inspect Organization Details</div>", unsafe_allow_html=True)
            selected_org_name = st.selectbox(
                "Select Organization to view full dossier",
                options=filtered_df["org_name"].unique()
            )
            org_row = filtered_df[filtered_df["org_name"] == selected_org_name].iloc[0]
            
            dcol1, dcol2 = st.columns(2)
            with dcol1:
                st.markdown(f"**📍 District:** {org_row.get('district')}")
                st.markdown(f"**🏢 Building Type:** {org_row.get('building_type')}")
                st.markdown(f"**🏠 Address:** {org_row.get('address')}")
                st.markdown(f"**📅 Registration:** {org_row.get('registered_since')} ({org_row.get('years_active')} years active)")
                st.markdown(f"**♿ Wheelchair Accessible:** {org_row.get('wheelchair')}")
                st.markdown(f"**🤟 Sign Language Available:** {org_row.get('sign_language')}")
            with dcol2:
                st.markdown(f"**👤 Focal Person:** {org_row.get('focal_name')}")
                st.markdown(f"**📞 Phone:** {org_row.get('focal_phone')}")
                st.markdown(f"**✉️ Email:** {org_row.get('focal_email')}")
                st.markdown(f"**💰 Amount Received:** {org_row.get('amount_received_display')}")
                st.markdown(f"**💸 Amount Utilized:** {org_row.get('amount_utilized_display')}")
                st.markdown(f"**💵 Balance:** {org_row.get('balance_display')}")

            st.markdown(f"**🛠️ Provided Services:** {org_row.get('services_display')}")
            st.markdown(f"**📝 Previous Experience:** {org_row.get('previous_experience')}")
            st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 3: FUNDING & BUDGET UTILIZATION
    # -------------------------------------------------------------
    with tab3:
        st.markdown("<div class='content-card'><div class='content-card-title'>💰 Budget Utilization & Financial Management</div>", unsafe_allow_html=True)
        
        fcol1, fcol2, fcol3 = st.columns(3)
        tot_rec = filtered_df["amount_received"].sum()
        tot_util = filtered_df["amount_utilized"].sum()
        overall_util_rate = (tot_util / tot_rec * 100) if tot_rec > 0 else 0
        
        with fcol1:
            st.metric("Total Funding Received", format_currency_pkr(tot_rec))
        with fcol2:
            st.metric("Total Amount Utilized", format_currency_pkr(tot_util))
        with fcol3:
            st.metric("Overall Utilization Rate", f"{overall_util_rate:.1f}%")

        # Financial breakdown table
        fin_cols = ["org_name", "district", "fiscal_year", "amount_received_display", "amount_utilized_display", "balance_display", "utilization_rate"]
        renamed_fin = {
            "org_name": "Organization",
            "district": "District",
            "fiscal_year": "Fiscal Year",
            "amount_received_display": "Amount Received",
            "amount_utilized_display": "Utilization Amount",
            "balance_display": "Balance",
            "utilization_rate": "Utilization %"
        }
        
        avail_fin_cols = [c for c in fin_cols if c in filtered_df.columns]
        fin_view = filtered_df[avail_fin_cols].rename(columns=renamed_fin)
        if "Utilization %" in fin_view.columns:
            fin_view["Utilization %"] = fin_view["Utilization %"].apply(lambda x: f"{x:.1f}%")

        st.dataframe(fin_view, use_container_width=True, height=350)
        
        # Download Financial CSV
        fin_csv = fin_view.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Budget Utilization CSV",
            data=fin_csv,
            file_name="depd_financial_utilization.csv",
            mime="text/csv"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 4: SINDH GIS MAP
    # -------------------------------------------------------------
    with tab4:
        st.markdown("<div class='content-card'><div class='content-card-title'>🗺️ Sindh Interactive GIS Map</div>", unsafe_allow_html=True)
        
        total_in_filter = len(filtered_df)
        mapped_count = int(filtered_df["has_gis"].sum()) if "has_gis" in filtered_df.columns else 0
        unmapped_count = total_in_filter - mapped_count

        st.markdown(
            f"Displaying **{mapped_count}** mapped organizations with valid GIS coordinates across Sindh province. "
            f"(<span style='color: #E11D48;'>{unmapped_count} organizations without GIS coordinates remain listed in tables</span>).",
            unsafe_allow_html=True
        )

        # Build and render Folium map
        folium_map = build_sindh_gis_map(filtered_df)
        st_folium(folium_map, width="100%", height=620, returned_objects=[])
        st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 5: DATA QUALITY & AUDITING
    # -------------------------------------------------------------
    with tab5:
        st.markdown("<div class='content-card'><div class='content-card-title'>🔍 Data Quality, Completeness & Auditing</div>", unsafe_allow_html=True)
        
        dq_metrics = compute_data_quality_metrics(filtered_df)

        q1, q2, q3, q4, q5 = st.columns(5)
        with q1:
            st.metric("GIS Coordinates", f"{dq_metrics['with_gis']} / {dq_metrics['total_organizations']}", delta=f"-{dq_metrics['missing_gis']} missing", delta_color="inverse")
        with q2:
            st.metric("Registration Year", f"{dq_metrics['with_reg_year']} / {dq_metrics['total_organizations']}", delta=f"-{dq_metrics['missing_reg_year']} missing", delta_color="inverse")
        with q3:
            st.metric("Focal Contact Info", f"{dq_metrics['with_focal_contact']} / {dq_metrics['total_organizations']}", delta=f"-{dq_metrics['missing_focal_contact']} missing", delta_color="inverse")
        with q4:
            st.metric("Financial Record Joined", f"{dq_metrics['with_financial_record']} / {dq_metrics['total_organizations']}", delta=f"-{dq_metrics['missing_financial_record']} missing", delta_color="inverse")
        with q5:
            st.metric("Duplicate IDs", f"{dq_metrics['duplicate_ids_count']}", delta="0 is optimal", delta_color="off")

        st.markdown("---")

        # Detailed breakdown of data quality issues
        st.markdown("#### 📋 Data Integrity Review Tables")

        with st.expander("📍 Organizations Missing GIS Coordinates", expanded=(dq_metrics['missing_gis'] > 0)):
            missing_gis_df = get_missing_gis_records(filtered_df)
            if not missing_gis_df.empty:
                st.dataframe(missing_gis_df, use_container_width=True)
            else:
                st.success("All filtered organizations have valid GIS coordinates.")

        with st.expander("📅 Organizations Missing Registration Year", expanded=False):
            missing_reg_df = get_missing_registration_records(filtered_df)
            if not missing_reg_df.empty:
                st.dataframe(missing_reg_df, use_container_width=True)
            else:
                st.success("All filtered organizations have valid registration dates.")

        with st.expander("💰 Organizations Without Joined Financial Records", expanded=False):
            missing_fin_df = get_missing_financial_records(filtered_df)
            if not missing_fin_df.empty:
                st.dataframe(missing_fin_df, use_container_width=True)
            else:
                st.success("All filtered organizations have matching Google Sheets financial records.")

        with st.expander("⚠️ Duplicate `_id` Audit", expanded=(dq_metrics['duplicate_ids_count'] > 0)):
            dup_id_df = get_duplicate_id_records(filtered_df)
            if not dup_id_df.empty:
                st.warning(f"Found {len(dup_id_df)} records sharing duplicate `_id` values.")
                st.dataframe(dup_id_df, use_container_width=True)
            else:
                st.success("No duplicate `_id` records detected in the dataset.")

        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
