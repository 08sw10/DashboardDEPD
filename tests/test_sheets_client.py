"""
Unit tests for Google Sheets header normalization and client methods.
"""

from src.sheets_client import normalize_header_name, COL_ID, COL_FISCAL_YEAR, COL_AMOUNT_RECEIVED, COL_AMOUNT_UTILIZED, COL_BALANCE

def test_normalize_header_name():
    # Spacing and colon variations
    assert normalize_header_name("Amount Recived:") == COL_AMOUNT_RECEIVED
    assert normalize_header_name("Amount Received:") == COL_AMOUNT_RECEIVED
    assert normalize_header_name("Amount Received") == COL_AMOUNT_RECEIVED
    assert normalize_header_name("Utilization Amount:") == COL_AMOUNT_UTILIZED
    assert normalize_header_name("Utilization  Amount:") == COL_AMOUNT_UTILIZED
    assert normalize_header_name("Amount Utilized") == COL_AMOUNT_UTILIZED
    assert normalize_header_name("Balance") == COL_BALANCE
    assert normalize_header_name("Balance:") == COL_BALANCE
    assert normalize_header_name("Fiscal Year") == COL_FISCAL_YEAR
    assert normalize_header_name("Fiscal  Year:") == COL_FISCAL_YEAR
    assert normalize_header_name("_id") == COL_ID
    assert normalize_header_name("Record ID") == COL_ID
