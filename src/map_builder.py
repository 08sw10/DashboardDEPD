"""
Interactive Sindh GIS Map Builder using Folium.
Supports marker clustering, Sindh district GeoJSON boundaries,
custom hover tooltips, and rich government-styled detail popups.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl

logger = logging.getLogger(__name__)

# Sindh geographic center & default zoom
SINDH_CENTER = [25.8920, 68.5247]
DEFAULT_ZOOM = 7

def create_popup_html(row: pd.Series) -> str:
    """
    Constructs a rich, accessible HTML popup card for an organization.
    """
    org_name = row.get("org_name", "Organization")
    acronym = row.get("acronym", "")
    district = row.get("district", "Unknown")
    address = row.get("address", "Not Available")
    
    focal_name = row.get("focal_name", "Not Available")
    focal_phone = row.get("focal_phone", "Not Available")
    focal_email = row.get("focal_email", "Not Available")
    
    reg_since = row.get("registered_since", "Not Available")
    years_active = row.get("years_active")
    active_str = f"{years_active} years" if years_active is not None else "Not Available"
    
    building = row.get("building_type", "Not Specified")
    wheelchair = row.get("wheelchair", "No")
    sign_lang = row.get("sign_language", "No")
    
    services_list = row.get("services_list", [])
    if isinstance(services_list, str):
        services_list = [s.strip() for s in services_list.split(",") if s.strip()]
        
    services_html = ""
    if services_list:
        services_items = "".join([f"<li style='margin-bottom: 2px;'>{s}</li>" for s in services_list[:8]])
        if len(services_list) > 8:
            services_items += f"<li style='color: #64748B;'>+{len(services_list)-8} more...</li>"
        services_html = f"<ul style='margin: 4px 0 0 16px; padding: 0; font-size: 11px; color: #334155;'>{services_items}</ul>"
    else:
        services_html = "<span style='font-size: 11px; color: #64748B;'>No services reported</span>"

    # Funding values
    amt_rec = row.get("amount_received_display", "Rs. 0")
    amt_util = row.get("amount_utilized_display", "Rs. 0")
    bal = row.get("balance_display", "Rs. 0")
    has_fin = row.get("has_financial_record", False)

    # Documents
    doc_status = row.get("documents_status", {})
    if not isinstance(doc_status, dict):
        doc_status = {}
    
    doc_badges = ""
    for doc, status in doc_status.items():
        is_avail = "✓" in str(status) or "Available" in str(status)
        badge_bg = "#DCFCE7" if is_avail else "#F1F5F9"
        badge_color = "#166534" if is_avail else "#64748B"
        doc_badges += f"""
        <div style='display: flex; justify-content: space-between; font-size: 10px; padding: 2px 4px; margin-bottom: 2px; background: {badge_bg}; border-radius: 3px;'>
            <span style='color: #1E293B;'>{doc}</span>
            <span style='color: {badge_color}; font-weight: bold;'>{status}</span>
        </div>
        """

    acronym_badge = f"<span style='background: #E2E8F0; color: #334155; padding: 1px 6px; border-radius: 4px; font-size: 10px; margin-left: 6px;'>{acronym}</span>" if acronym else ""

    html = f"""
    <div style='font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; width: 320px; max-height: 440px; overflow-y: auto; padding: 4px; color: #1E293B;'>
        <!-- Header -->
        <div style='border-bottom: 2px solid #0A6847; padding-bottom: 6px; margin-bottom: 8px;'>
            <div style='font-size: 14px; font-weight: bold; color: #0A6847; line-height: 1.2;'>
                {org_name} {acronym_badge}
            </div>
            <div style='font-size: 11px; color: #64748B; margin-top: 3px;'>
                📍 <strong>{district}</strong> | 🏢 {building}
            </div>
        </div>

        <!-- Registration & Contact -->
        <div style='background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px 8px; margin-bottom: 8px; font-size: 11px;'>
            <div style='margin-bottom: 3px;'><strong>📅 Registration:</strong> {reg_since} ({active_str})</div>
            <div style='margin-bottom: 3px;'><strong>👤 Focal Person:</strong> {focal_name}</div>
            <div style='margin-bottom: 3px;'><strong>📞 Phone:</strong> {focal_phone}</div>
            <div style='margin-bottom: 3px;'><strong>✉️ Email:</strong> {focal_email}</div>
            <div><strong>🏠 Address:</strong> {address}</div>
        </div>

        <!-- Accessibility -->
        <div style='display: flex; gap: 6px; margin-bottom: 8px;'>
            <div style='flex: 1; background: {"#EFF6FF" if wheelchair == "Yes" else "#F1F5F9"}; padding: 4px 6px; border-radius: 4px; font-size: 10px; text-align: center;'>
                ♿ Wheelchair: <strong>{wheelchair}</strong>
            </div>
            <div style='flex: 1; background: {"#EFF6FF" if sign_lang == "Yes" else "#F1F5F9"}; padding: 4px 6px; border-radius: 4px; font-size: 10px; text-align: center;'>
                🤟 Sign Lang: <strong>{sign_lang}</strong>
            </div>
        </div>

        <!-- Services -->
        <div style='margin-bottom: 8px; border-top: 1px solid #E2E8F0; padding-top: 6px;'>
            <div style='font-size: 11px; font-weight: bold; color: #0A6847; margin-bottom: 2px;'>🛠️ Provided Services:</div>
            {services_html}
        </div>

        <!-- Budget & Utilization -->
        <div style='background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 6px 8px; margin-bottom: 8px; font-size: 11px;'>
            <div style='font-weight: bold; color: #166534; margin-bottom: 4px;'>💰 Budget & Funding</div>
            {"<div style='display: flex; justify-content: space-between;'><span>Received:</span><strong>" + amt_rec + "</strong></div>" if has_fin else "<div style='color: #64748B;'>No Financial Record Joined</div>"}
            {"<div style='display: flex; justify-content: space-between;'><span>Utilized:</span><strong>" + amt_util + "</strong></div>" if has_fin else ""}
            {"<div style='display: flex; justify-content: space-between; border-top: 1px dashed #86EFAC; margin-top: 3px; padding-top: 2px;'><span>Balance:</span><strong style='color: #0A6847;'>" + bal + "</strong></div>" if has_fin else ""}
        </div>

        <!-- Documents Audit -->
        <div style='border-top: 1px solid #E2E8F0; padding-top: 6px;'>
            <div style='font-size: 11px; font-weight: bold; color: #0A6847; margin-bottom: 4px;'>📋 Document Status:</div>
            {doc_badges}
        </div>
    </div>
    """
    return html

def build_sindh_gis_map(
    df: pd.DataFrame,
    geojson_path: Optional[str] = "data/sindh_districts.geojson",
    height: int = 650
) -> folium.Map:
    """
    Builds a Folium interactive map for Sindh with clustering and rich popups.
    Excludes records with missing coordinates gracefully.
    """
    # Create Folium Map with standard OpenStreetMap base
    m = folium.Map(
        location=SINDH_CENTER,
        zoom_start=DEFAULT_ZOOM,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True
    )

    # Add District Boundary GeoJSON layer if file exists
    if geojson_path and os.path.exists(geojson_path):
        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                geojson_data = json.load(f)
            
            folium.GeoJson(
                geojson_data,
                name="Sindh District Boundaries",
                style_function=lambda feature: {
                    "fillColor": "#0A6847",
                    "color": "#0A6847",
                    "weight": 1.5,
                    "fillOpacity": 0.05,
                    "dashArray": "4, 4"
                },
                highlight_function=lambda feature: {
                    "fillColor": "#0A6847",
                    "color": "#059669",
                    "weight": 2.5,
                    "fillOpacity": 0.15
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["district", "division"],
                    aliases=["District:", "Division:"],
                    localize=True,
                    sticky=True
                )
            ).add_to(m)
        except Exception as e:
            logger.warning(f"Unable to load Sindh GeoJSON layer: {e}")

    # Add Fullscreen & Locate Controls
    Fullscreen(position="topright").add_to(m)
    LocateControl(position="topright").add_to(m)

    # Create Marker Cluster
    marker_cluster = MarkerCluster(
        name="Organizations Cluster",
        overlay=True,
        control=True,
        options={
            "maxClusterRadius": 50,
            "spiderfyOnMaxZoom": True,
            "showCoverageOnHover": False,
            "zoomToBoundsOnClick": True
        }
    ).add_to(m)

    # Add organization markers
    if not df.empty:
        # Filter for rows with valid coordinates
        valid_coords_df = df[df["latitude"].notna() & df["longitude"].notna()].copy()
        
        for _, row in valid_coords_df.iterrows():
            lat = float(row["latitude"])
            lng = float(row["longitude"])
            
            org_name = str(row.get("org_name", "Organization"))
            district = str(row.get("district", "Unknown"))

            # Registration year — numeric only, show oldest valid year
            reg_year = row.get("registration_year")
            if reg_year is not None and not pd.isna(reg_year):
                reg_line = f"📅 Registered Since: <strong>{int(reg_year)}</strong>"
            else:
                reg_line = "📅 Registration Year: <em>Not Available</em>"

            # Optional region line (only shown when field exists and is meaningful)
            region = str(row.get("region", "") or "").strip()
            region_line = f"🗺️ {region} Region<br/>" if region and region.lower() not in ("", "unknown region", "unknown") else ""

            # Hover tooltip — 3 required fields + optional region
            tooltip_text = f"""
<div style='font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 12px; line-height: 1.45;'>
    <strong style='color:#0A6847; font-size: 13px;'>{org_name}</strong><br/>
    {region_line}📍 {district}<br/>
    {reg_line}
</div>
"""
            
            # Click Popup
            popup_html = create_popup_html(row)
            popup = folium.Popup(popup_html, max_width=350)
            
            # Icon Color based on accessibility or funding status
            has_funding = row.get("has_financial_record", False)
            icon_color = "green" if has_funding else "blue"
            icon_symbol = "building"

            folium.Marker(
                location=[lat, lng],
                popup=popup,
                tooltip=folium.Tooltip(tooltip_text, sticky=True, class_name="depd-tooltip"),
                icon=folium.Icon(color=icon_color, icon=icon_symbol, prefix="fa")
            ).add_to(marker_cluster)

    # Add Layer Control
    folium.LayerControl(position="topright", collapsed=True).add_to(m)

    return m
