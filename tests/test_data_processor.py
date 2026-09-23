"""
Unit tests for data processor, normalization, and merge logic.
"""

import datetime
import pandas as pd
import pytest
from src.data_processor import (
    clean_currency_to_float,
    format_currency_pkr,
    extract_year_from_date,
    extract_oldest_registration_year,
    extract_services,
    extract_document_status,
    process_single_organization,
    process_kobo_submissions,
    process_google_sheets_records,
    merge_kobo_and_financial_data,
    detect_duplicate_ids
)

def test_clean_currency_to_float():
    assert clean_currency_to_float("Rs. 1,250,000") == 1250000.0
    assert clean_currency_to_float("Rs 500.50") == 500.50
    assert clean_currency_to_float("3,000,000") == 3000000.0
    assert clean_currency_to_float(None) == 0.0
    assert clean_currency_to_float("") == 0.0
    assert clean_currency_to_float("Invalid") == 0.0

def test_format_currency_pkr():
    assert format_currency_pkr(1250000) == "Rs. 1,250,000"
    assert format_currency_pkr(0) == "Rs. 0"
    assert format_currency_pkr(None) == "Rs. 0"

def test_extract_year_from_date():
    assert extract_year_from_date("2018-05-20") == 2018
    assert extract_year_from_date("15/08/2015") == 2015
    assert extract_year_from_date("2020") == 2020
    assert extract_year_from_date(2019) == 2019
    assert extract_year_from_date(None) is None
    assert extract_year_from_date("InvalidDate") is None

def test_oldest_registration_year_logic():
    # Society (2018), Trust (2016), SPDPA (2022) -> Oldest must be 2016!
    sample = {
        "5. Registration Date Society": "2018-09-20",
        "5.1 Registration Date Trust": "2016-03-15",
        "5.5 Registration Date (SPDPA)": "2022-01-05"
    }
    oldest_year, text = extract_oldest_registration_year(sample)
    assert oldest_year == 2016
    assert text == "Registered Since: 2016"

    # Single registration
    sample_single = {"5. Registration Date Society": "2021-04-10"}
    oldest_year, text = extract_oldest_registration_year(sample_single)
    assert oldest_year == 2021
    assert text == "Registered Since: 2021"

    # No registration
    oldest_year, text = extract_oldest_registration_year({})
    assert oldest_year is None
    assert text == "Not Available"

def test_years_active_dynamic_calculation():
    current_year = datetime.datetime.now().year
    sample = {
        "_id": 101,
        "1. Organization Name": "Test Org",
        "5. Registration Date Society": "2015-01-01"
    }
    processed = process_single_organization(sample)
    expected_active = current_year - 2015
    assert processed["registration_year"] == 2015
    assert processed["years_active"] == expected_active

def test_services_extraction():
    sample = {
        "Services/Specialized academic schooling": "1",
        "Services/Speech therapy": "true",
        "Services/Physiotherapy": "0",
        "Services/Autism clinical support": None,
        "Services/Vocational training": "yes"
    }
    srv_list, count, display = extract_services(sample)
    assert count == 3
    assert "Specialized academic schooling" in srv_list
    assert "Speech therapy" in srv_list
    assert "Vocational training" in srv_list
    assert "Physiotherapy" not in srv_list

def test_document_status():
    sample = {
        "15.1: Board Members List": "Attached",
        "15.2: Board Meeting Minutes": "Not Available",
        "15.3: Staff Members List": "Attached"
    }
    status = extract_document_status(sample)
    assert status["Board Members List"] == "✓ Available"
    assert status["Board Meeting Minutes"] == "✕ Not Available"
    assert status["Staff Members List"] == "✓ Available"

def test_id_normalization_and_left_join():
    # Kobo has orgs with integer _id and string _id
    kobo_data = [
        {"_id": 1001, "1. Organization Name": "Org A", "7. District": "Karachi East"},
        {"_id": " 1002 ", "1. Organization Name": "Org B", "7. District": "Hyderabad"},
        {"_id": 1003, "1. Organization Name": "Org C", "7. District": "Sukkur"}
    ]
    # Google Sheets has financial data for 1001 and 1002 (with trailing spaces)
    sheets_data = [
        {"_id": " 1001", "Amount Received": "Rs. 2,000,000", "Utilization Amount": "Rs. 1,500,000"},
        {"_id": "1002 ", "Amount Received": "Rs. 1,000,000", "Utilization Amount": "Rs. 800,000"}
    ]

    org_df = process_kobo_submissions(kobo_data)
    fin_df = process_google_sheets_records(sheets_data)
    merged = merge_kobo_and_financial_data(org_df, fin_df)

    assert len(merged) == 3
    
    # Check 1001
    row_1001 = merged[merged["_id"] == "1001"].iloc[0]
    assert row_1001["amount_received"] == 2000000.0
    assert row_1001["amount_utilized"] == 1500000.0
    assert row_1001["has_financial_record"] == True

    # Check 1002
    row_1002 = merged[merged["_id"] == "1002"].iloc[0]
    assert row_1002["amount_received"] == 1000000.0
    assert row_1002["has_financial_record"] == True

    # Check 1003 (Missing financial record -> preserved in table!)
    row_1003 = merged[merged["_id"] == "1003"].iloc[0]
    assert row_1003["amount_received"] == 0.0
    assert row_1003["has_financial_record"] == False
    assert row_1003["financial_status"] == "No financial record"

def test_duplicate_id_detection():
    df = pd.DataFrame([
        {"_id": "1001", "org_name": "Org 1"},
        {"_id": "1002", "org_name": "Org 2"},
        {"_id": "1001", "org_name": "Org 1 Duplicate"}
    ])
    dups = detect_duplicate_ids(df)
    assert len(dups) == 2
    assert set(dups["_id"].unique()) == {"1001"}
