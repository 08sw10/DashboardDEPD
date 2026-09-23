"""
UI components, Government of Sindh header layout, CSS styling,
KPI metric cards, charts, and filter controls for DEPD Dashboard.
"""

import os
import base64
import datetime
from typing import Tuple, List, Dict, Any, Optional
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from src.data_processor import format_currency_pkr

def get_base64_image(image_path: str) -> str:
    """Reads a local image file and returns base64 data URI."""
    if not os.path.exists(image_path):
        return ""
    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        ext = os.path.splitext(image_path)[1].lstrip(".").lower()
        if ext == "jpg":
            ext = "jpeg"
        return f"data:image/{ext};base64,{encoded}"
    except Exception:
        return ""

def inject_custom_css():
    """Injects professional, accessible Government of Sindh stylesheet."""
    st.markdown(
        """
        <style>
        /* Main background and fonts */
        .main, .stApp {
            background-color: #F8FAFC;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: #1E293B;
        }

        /* Top header container */
        .depd-header-card {
            background: #FFFFFF;
            border-bottom: 3px solid #0A6847;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            border-radius: 8px;
            padding: 16px 24px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .depd-header-left {
            display: flex;
            align-items: center;
            justify-content: flex-start;
            flex: 1;
        }

        .depd-header-center {
            text-align: center;
            flex: 3;
            padding: 0 16px;
        }

        .depd-header-right {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            flex: 1;
        }

        .depd-title-dept {
            font-size: 20px;
            font-weight: 800;
            color: #0A6847;
            letter-spacing: -0.01em;
            margin: 0;
            line-height: 1.25;
        }

        .depd-title-govt {
            font-size: 14px;
            font-weight: 600;
            color: #475569;
            margin: 2px 0;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .depd-title-app {
            font-size: 15px;
            font-weight: 700;
            color: #0F172A;
            margin: 4px 0 0 0;
        }

        /* Status bar */
        .depd-status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 8px 16px;
            margin-bottom: 20px;
            font-size: 12px;
            color: #64748B;
        }

        .live-badge {
            background-color: #DCFCE7;
            color: #15803D;
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .sample-badge {
            background-color: #FEF3C7;
            color: #B45309;
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        /* KPI Metric Cards */
        .kpi-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-bottom: 24px;
        }

        .kpi-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-top: 3px solid #0A6847;
            border-radius: 8px;
            padding: 16px 14px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
        }

        .kpi-label {
            font-size: 11px;
            font-weight: 700;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }

        .kpi-value {
            font-size: 20px;
            font-weight: 800;
            color: #0F172A;
            line-height: 1.2;
        }

        .kpi-sub {
            font-size: 11px;
            color: #94A3B8;
            margin-top: 4px;
        }

        /* Section Cards */
        .content-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 18px 20px;
            margin-bottom: 20px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        }

        .content-card-title {
            font-size: 16px;
            font-weight: 700;
            color: #0A6847;
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 1px solid #F1F5F9;
            padding-bottom: 8px;
        }

        /* Streamlit Element cleanups */
        div[data-testid="stMetricValue"] {
            font-size: 22px;
            font-weight: 800;
            color: #0F172A;
        }
        
        div[data-testid="stMetricLabel"] {
            font-size: 12px;
            font-weight: 600;
            color: #64748B;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 6px 6px 0 0;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 14px;
        }

        /* Folium leaflet tooltip override for DEPD branding */
        .leaflet-tooltip.depd-tooltip {
            background: #FFFFFF;
            border: 1px solid #0A6847;
            border-radius: 6px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.10);
            color: #1E293B;
            padding: 8px 10px;
            max-width: 280px;
            white-space: normal;
        }
        .leaflet-tooltip.depd-tooltip::before {
            border-top-color: #0A6847;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_header(
    sindh_logo_path: str = "assets/sindh_government_logo.png",
    depd_logo_path: str = "assets/depd_logo.png"
):
    """
    Renders the official Government of Sindh and DEPD header.
    Left: Sindh Logo | Center: Government & DEPD Titles | Right: DEPD Logo.
    """
    sindh_logo_b64 = get_base64_image(sindh_logo_path)
    depd_logo_b64 = get_base64_image(depd_logo_path)

    sindh_img_html = f'<img src="{sindh_logo_b64}" style="max-height: 75px; max-width: 140px; object-fit: contain;" alt="Government of Sindh" />' if sindh_logo_b64 else '<div style="font-size: 12px; color: #0A6847; font-weight: bold;">Government of Sindh</div>'
    depd_img_html = f'<img src="{depd_logo_b64}" style="max-height: 65px; max-width: 220px; object-fit: contain;" alt="DEPD Logo" />' if depd_logo_b64 else '<div style="font-size: 12px; color: #0A6847; font-weight: bold;">DEPD Sindh</div>'

    header_html = f"""
    <div class="depd-header-card">
        <div class="depd-header-left">
            {sindh_img_html}
        </div>
        <div class="depd-header-center">
            <div class="depd-title-dept">Department of Empowerment of Persons with Disabilities</div>
            <div class="depd-title-govt">Government of Sindh</div>
            <div class="depd-title-app">Organization & Funding Management Dashboard</div>
        </div>
        <div class="depd-header-right">
            {depd_img_html}
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

def render_status_bar(
    is_live: bool,
    last_updated_time: datetime.datetime,
    cache_notice: Optional[str] = None,
    row_count: Optional[int] = None
):
    """
    Renders the top status bar with live/cached/demo indicator and timestamp.

    Args:
        is_live: True when both Kobo and Sheets returned fresh live data.
        last_updated_time: Timestamp of the last data load.
        cache_notice: When truthy, shows a yellow 'Cached Snapshot' badge
                      instead of green/yellow demo badge.
        row_count: Optional record count appended to the badge,
                   e.g. "● Live Data — 62 rows".
    """
    time_str = last_updated_time.strftime("%d %B %Y, %I:%M %p")
    row_suffix = f" — {row_count} rows" if row_count is not None else ""

    if cache_notice:
        badge_html = f'<span class="sample-badge">● Cached Snapshot{row_suffix}</span>'
        status_text = cache_notice
    elif is_live:
        badge_html = f'<span class="live-badge">● Live Data{row_suffix}</span>'
        status_text = "Connected to KoboToolbox & Google Sheets APIs"
    else:
        badge_html = f'<span class="sample-badge">● Demo / Offline Mode{row_suffix}</span>'
        status_text = "Using local data. Configure API secrets in secrets.toml for live synchronization."

    status_html = f"""
    <div class="depd-status-bar">
        <div>{badge_html} &nbsp; <span style="font-size: 11px; color: #475569;">{status_text}</span></div>
        <div><strong>Last Updated:</strong> {time_str}</div>
    </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)

def render_kpi_cards(df: pd.DataFrame):
    """
    Renders top KPI metrics:
    - Total Organizations
    - Total Districts
    - Total Amount Received
    - Total Amount Utilized
    - Total Balance
    """
    if df.empty:
        total_orgs = 0
        total_districts = 0
        total_received = 0.0
        total_utilized = 0.0
        total_balance = 0.0
        util_rate = 0.0
    else:
        total_orgs = len(df)
        total_districts = df["district"].nunique() if "district" in df.columns else 0
        total_received = df["amount_received"].sum() if "amount_received" in df.columns else 0.0
        total_utilized = df["amount_utilized"].sum() if "amount_utilized" in df.columns else 0.0
        total_balance = df["balance"].sum() if "balance" in df.columns else (total_received - total_utilized)
        util_rate = (total_utilized / total_received * 100.0) if total_received > 0 else 0.0

    kpi_html = f"""
    <div class="kpi-container">
        <div class="kpi-card" style="border-top-color: #0A6847;">
            <div class="kpi-label">Organizations</div>
            <div class="kpi-value">{total_orgs:,}</div>
            <div class="kpi-sub">Total Registered</div>
        </div>
        <div class="kpi-card" style="border-top-color: #2563EB;">
            <div class="kpi-label">Districts Covered</div>
            <div class="kpi-value">{total_districts}</div>
            <div class="kpi-sub">Sindh Province</div>
        </div>
        <div class="kpi-card" style="border-top-color: #0D9488;">
            <div class="kpi-label">Total Received</div>
            <div class="kpi-value">{format_currency_pkr(total_received)}</div>
            <div class="kpi-sub">Allocated Funds</div>
        </div>
        <div class="kpi-card" style="border-top-color: #E11D48;">
            <div class="kpi-label">Total Utilized</div>
            <div class="kpi-value">{format_currency_pkr(total_utilized)}</div>
            <div class="kpi-sub">{util_rate:.1f}% Utilization</div>
        </div>
        <div class="kpi-card" style="border-top-color: #D97706;">
            <div class="kpi-label">Total Balance</div>
            <div class="kpi-value">{format_currency_pkr(total_balance)}</div>
            <div class="kpi-sub">Remaining Funds</div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

def render_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renders sidebar filters and returns the filtered DataFrame.
    Filters: District, Organization, Registration Year, Building Type,
    Wheelchair, Sign Language, Services, Documents, Fiscal Year.
    """
    st.sidebar.markdown("### 🎛️ Dashboard Filters")

    if df.empty:
        st.sidebar.info("No data available to filter.")
        return df

    filtered_df = df.copy()

    # 1. District Filter
    all_districts = sorted([d for d in df["district"].dropna().unique() if str(d).strip()])
    selected_districts = st.sidebar.multiselect("📍 District", options=all_districts, default=[])
    if selected_districts:
        filtered_df = filtered_df[filtered_df["district"].isin(selected_districts)]

    # 2. Organization Name Filter
    all_orgs = sorted([o for o in df["org_name"].dropna().unique() if str(o).strip()])
    selected_orgs = st.sidebar.multiselect("🏢 Organization", options=all_orgs, default=[])
    if selected_orgs:
        filtered_df = filtered_df[filtered_df["org_name"].isin(selected_orgs)]

    # 3. Registration Year Filter
    valid_years = [int(y) for y in df["registration_year"].dropna().unique()]
    if valid_years:
        min_year = min(valid_years)
        max_year = max(valid_years)
        if min_year < max_year:
            year_range = st.sidebar.slider("📅 Registration Year Range", min_value=min_year, max_value=max_year, value=(min_year, max_year))
            filtered_df = filtered_df[
                (filtered_df["registration_year"].isna()) | 
                ((filtered_df["registration_year"] >= year_range[0]) & (filtered_df["registration_year"] <= year_range[1]))
            ]

    # 4. Building Type Filter
    if "building_type" in df.columns:
        all_buildings = sorted([b for b in df["building_type"].dropna().unique() if str(b).strip()])
        if all_buildings:
            selected_buildings = st.sidebar.multiselect("🏛️ Building Type", options=all_buildings, default=[])
            if selected_buildings:
                filtered_df = filtered_df[filtered_df["building_type"].isin(selected_buildings)]

    # 5. Accessibility Filters
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### ♿ Accessibility")
    
    wheelchair_opt = st.sidebar.selectbox("Wheelchair Accessible", ["All", "Yes", "No"], index=0)
    if wheelchair_opt != "All":
        filtered_df = filtered_df[filtered_df["wheelchair"] == wheelchair_opt]

    sign_lang_opt = st.sidebar.selectbox("Sign Language Available", ["All", "Yes", "No"], index=0)
    if sign_lang_opt != "All":
        filtered_df = filtered_df[filtered_df["sign_language"] == sign_lang_opt]

    # 6. Service Multiselect Filter
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🛠️ Services")
    all_services = set()
    for s_list in df["services_list"].dropna():
        if isinstance(s_list, list):
            all_services.update(s_list)
        elif isinstance(s_list, str):
            all_services.update([s.strip() for s in s_list.split(",") if s.strip()])
    
    sorted_services = sorted(list(all_services))
    if sorted_services:
        selected_services = st.sidebar.multiselect("Filter by Service", options=sorted_services, default=[])
        if selected_services:
            filtered_df = filtered_df[filtered_df["services_list"].apply(
                lambda s_list: any(sel in (s_list if isinstance(s_list, list) else []) for sel in selected_services)
            )]

    # 7. Document Availability Filter
    doc_filter_opt = st.sidebar.selectbox(
        "📋 Document Status Filter",
        ["All Organizations", "Audit Report Available", "Board List Available", "Rent Agreement Available", "Bank Statement Available"]
    )
    if doc_filter_opt == "Audit Report Available" and "doc_audit_report" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["doc_audit_report"] == "✓ Available"]
    elif doc_filter_opt == "Board List Available" and "doc_board_members" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["doc_board_members"] == "✓ Available"]
    elif doc_filter_opt == "Rent Agreement Available" and "doc_rent_agreement" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["doc_rent_agreement"] == "✓ Available"]
    elif doc_filter_opt == "Bank Statement Available" and "doc_bank_statement" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["doc_bank_statement"] == "✓ Available"]

    # 8. Fiscal Year Filter
    if "fiscal_year" in df.columns:
        all_fys = sorted([fy for fy in df["fiscal_year"].dropna().unique() if str(fy).strip() and str(fy) != "Not Available"])
        if all_fys:
            selected_fy = st.sidebar.multiselect("💵 Fiscal Year", options=all_fys, default=[])
            if selected_fy:
                filtered_df = filtered_df[filtered_df["fiscal_year"].isin(selected_fy)]

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Showing **{len(filtered_df)}** of **{len(df)}** organizations.")

    return filtered_df

def render_overview_charts(df: pd.DataFrame):
    """Renders analytical charts for the Executive Dashboard tab."""
    if df.empty:
        st.warning("No data matching the selected filters.")
        return

    col1, col2 = st.columns(2)

    # Chart 1: Organizations by District
    with col1:
        st.markdown("<div class='content-card'><div class='content-card-title'>🏢 Organizations by District</div>", unsafe_allow_html=True)
        district_counts = df["district"].value_counts().reset_index()
        district_counts.columns = ["District", "Organizations"]
        fig_dist = px.bar(
            district_counts,
            x="District",
            y="Organizations",
            text="Organizations",
            color="Organizations",
            color_continuous_scale="Greens"
        )
        fig_dist.update_layout(
            margin=dict(l=20, r=20, t=20, b=40),
            height=320,
            xaxis_tickangle=-45,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Chart 2: Funding by District (Received vs Utilized)
    with col2:
        st.markdown("<div class='content-card'><div class='content-card-title'>💰 Funding Allocation & Utilization by District</div>", unsafe_allow_html=True)
        funding_dist = df.groupby("district")[["amount_received", "amount_utilized"]].sum().reset_index()
        fig_fund = go.Figure()
        fig_fund.add_trace(go.Bar(
            x=funding_dist["district"],
            y=funding_dist["amount_received"],
            name="Received",
            marker_color="#0A6847"
        ))
        fig_fund.add_trace(go.Bar(
            x=funding_dist["district"],
            y=funding_dist["amount_utilized"],
            name="Utilized",
            marker_color="#E11D48"
        ))
        fig_fund.update_layout(
            barmode="group",
            margin=dict(l=20, r=20, t=20, b=40),
            height=320,
            xaxis_tickangle=-45,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_fund, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    # Chart 3: Services Distribution
    with col3:
        st.markdown("<div class='content-card'><div class='content-card-title'>🛠️ Most Offered Services</div>", unsafe_allow_html=True)
        service_counts = {}
        for s_list in df["services_list"].dropna():
            if isinstance(s_list, list):
                for s in s_list:
                    service_counts[s] = service_counts.get(s, 0) + 1
        
        if service_counts:
            srv_df = pd.DataFrame(list(service_counts.items()), columns=["Service", "Count"]).sort_values(by="Count", ascending=True)
            fig_srv = px.bar(
                srv_df,
                x="Count",
                y="Service",
                orientation="h",
                text="Count",
                color="Count",
                color_continuous_scale="Blues"
            )
            fig_srv.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                height=340,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_srv, use_container_width=True)
        else:
            st.info("No service details reported.")
        st.markdown("</div>", unsafe_allow_html=True)

    # Chart 4: Registration Timeline / Distribution
    with col4:
        st.markdown("<div class='content-card'><div class='content-card-title'>📅 Registration Timeline (Oldest Valid Year)</div>", unsafe_allow_html=True)
        reg_df = df[df["registration_year"].notna()].copy()
        if not reg_df.empty:
            year_counts = reg_df["registration_year"].astype(int).value_counts().reset_index()
            year_counts.columns = ["Year", "Organizations"]
            year_counts = year_counts.sort_values(by="Year")
            fig_reg = px.line(
                year_counts,
                x="Year",
                y="Organizations",
                markers=True,
                line_shape="spline",
                color_discrete_sequence=["#0A6847"]
            )
            fig_reg.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                height=340,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_reg, use_container_width=True)
        else:
            st.info("No registration dates available.")
        st.markdown("</div>", unsafe_allow_html=True)

def render_organizations_table(df: pd.DataFrame):
    """Renders the searchable organizations table with detail drawers and CSV download."""
    st.markdown("<div class='content-card'><div class='content-card-title'>🏢 Organizations Directory</div>", unsafe_allow_html=True)

    # Search bar
    search_query = st.text_input("🔍 Search organizations by name, district, focal person, or address...", "")
    
    table_df = df.copy()
    if search_query:
        sq = search_query.lower()
        table_df = table_df[
            table_df["org_name"].str.lower().str.contains(sq, na=False) |
            table_df["district"].str.lower().str.contains(sq, na=False) |
            table_df["focal_name"].str.lower().str.contains(sq, na=False) |
            table_df["address"].str.lower().str.contains(sq, na=False)
        ]

    # Display columns
    display_cols = [
        "org_name", "district", "registration_year", "years_active",
        "services_count", "wheelchair", "sign_language", "documents_available_count",
        "amount_received_display", "amount_utilized_display", "balance_display"
    ]
    renamed_cols = {
        "org_name": "Organization",
        "district": "District",
        "registration_year": "Reg. Year",
        "years_active": "Years Active",
        "services_count": "Services Count",
        "wheelchair": "Wheelchair",
        "sign_language": "Sign Lang.",
        "documents_available_count": "Docs (x/6)",
        "amount_received_display": "Amount Received",
        "amount_utilized_display": "Amount Utilized",
        "balance_display": "Balance"
    }
    
    available_display_cols = [c for c in display_cols if c in table_df.columns]
    view_df = table_df[available_display_cols].rename(columns=renamed_cols)

    st.dataframe(view_df, use_container_width=True, height=450)

    # CSV Download
    csv_data = table_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered Organizations CSV",
        data=csv_data,
        file_name="depd_organizations_data.csv",
        mime="text/csv"
    )

    st.markdown("</div>", unsafe_allow_html=True)
