"""
Unit tests for Folium GIS Map generation and HTML popup creation.
"""

import pandas as pd
import folium
from src.map_builder import create_popup_html, build_sindh_gis_map

def test_create_popup_html():
    row = pd.Series({
        "org_name": "Test Welfare Society",
        "acronym": "TWS",
        "district": "Karachi East",
        "address": "PECHS Block 6",
        "focal_name": "Aslam Khan",
        "focal_phone": "03001234567",
        "focal_email": "test@tws.org",
        "registered_since": "Registered Since: 2015",
        "years_active": 11,
        "building_type": "Owned",
        "wheelchair": "Yes",
        "sign_language": "Yes",
        "services_list": ["Special schooling", "Speech therapy"],
        "amount_received_display": "Rs. 3,500,000",
        "amount_utilized_display": "Rs. 2,850,000",
        "balance_display": "Rs. 650,000",
        "has_financial_record": True,
        "documents_status": {
            "Board Members List": "✓ Available",
            "Audit Report": "✓ Available"
        }
    })

    html = create_popup_html(row)
    assert "Test Welfare Society" in html
    assert "TWS" in html
    assert "Karachi East" in html
    assert "Aslam Khan" in html
    assert "Rs. 3,500,000" in html
    assert "Special schooling" in html

def test_build_sindh_gis_map():
    df = pd.DataFrame([
        {
            "_id": "1",
            "org_name": "Org 1",
            "district": "Karachi",
            "latitude": 24.8607,
            "longitude": 67.0011,
            "has_gis": True,
            "registered_since": "Registered Since: 2018",
            "has_financial_record": True
        },
        {
            "_id": "2",
            "org_name": "Org 2",
            "district": "Hyderabad",
            "latitude": None,
            "longitude": None,
            "has_gis": False,
            "registered_since": "Not Available",
            "has_financial_record": False
        }
    ])

    m = build_sindh_gis_map(df, geojson_path="data/sindh_districts.geojson")
    assert isinstance(m, folium.Map)
