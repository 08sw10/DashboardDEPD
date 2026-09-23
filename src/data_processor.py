"""
Data processing, cleaning, and normalization engine for DEPD Sindh Dashboard.
Implements _id string normalization, oldest registration date logic,
dynamic active years calculation, services parsing, document audit, and left-join.
"""

import re
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Document keys to audit
DOCUMENT_KEYS = [
    "Board Members List",
    "Board Meeting Minutes",
    "Staff Members List",
    "Building Rent Agreement",
    "Most Recent Audit Report",
    "Bank Statement"
]

def clean_currency_to_float(value: Any) -> float:
    """
    Safely converts currency string (e.g. 'Rs. 1,250,000', '1,200', 'Rs 500') to float.
    Handles 'Rs.', 'PKR', commas, and whitespace cleanly.
    Returns 0.0 for invalid or empty values.
    """
    if pd.isna(value) or value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ["nan", "none", "-", "null", "not available"]:
        return 0.0

    # Remove currency words/abbreviations and commas
    val_str = re.sub(r"(?i)\b(rs\.?|pkr|rupees)\b", "", val_str)
    val_str = val_str.replace(",", "").strip()
    
    # Extract number (supports optional decimals)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", val_str)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return 0.0
    return 0.0

def format_currency_pkr(amount: Optional[float], show_symbol: bool = True) -> str:
    """Formats numeric amount as Pakistani Rupees (e.g., 'Rs. 1,250,000')."""
    if amount is None or pd.isna(amount):
        return "Rs. 0" if show_symbol else "0"
    formatted = f"{int(round(amount)):,}"
    return f"Rs. {formatted}" if show_symbol else formatted

def extract_year_from_date(date_val: Any) -> Optional[int]:
    """
    Extracts a 4-digit year from string, date, or number safely.
    Validates that year is between 1900 and current year + 1.
    """
    if pd.isna(date_val) or date_val is None:
        return None
    
    val_str = str(date_val).strip()
    # Look for 4-digit year (19xx or 20xx)
    match = re.search(r"\b(19\d{2}|20\d{2})\b", val_str)
    if match:
        year = int(match.group(1))
        current_year = datetime.datetime.now().year
        if 1900 <= year <= current_year + 1:
            return year
    return None

def find_best_field_value(record: Dict[str, Any], candidates: List[str], default: Any = None) -> Any:
    """
    Searches a record dict for keys matching candidates (case-insensitive substring/regex).
    """
    record_keys = list(record.keys())
    
    # 1. Exact match
    for cand in candidates:
        if cand in record and record[cand] is not None:
            return record[cand]
            
    # 2. Normalized match (ignoring case, spaces, leading numbers)
    for cand in candidates:
        cand_norm = re.sub(r"[^a-zA-Z0-9]", "", cand).lower()
        for k in record_keys:
            k_norm = re.sub(r"[^a-zA-Z0-9]", "", k).lower()
            if cand_norm in k_norm:
                val = record[k]
                if val is not None and str(val).strip() != "":
                    return val

    return default

def extract_oldest_registration_year(record: Dict[str, Any]) -> Tuple[Optional[int], Optional[str]]:
    """
    Scans ALL registration date fields (Society, Trust, NGO, Section 42, Foundation, SPDPA, etc.)
    and returns the OLDEST (minimum) valid registration year.
    An org with Society=2018, Trust=2020, SPDPA=2023 must produce registration_year=2018.
    """
    valid_years: List[int] = []

    for key, val in record.items():
        key_lower = key.lower()
        if (
            ("registration" in key_lower and "date" in key_lower)
            or ("registration" in key_lower or "reg date" in key_lower or "registered" in key_lower)
            or key_lower.startswith("5.")
        ):
            year = extract_year_from_date(val)
            if year:
                valid_years.append(year)

    if not valid_years:
        return None, "Not Available"

    oldest = min(valid_years)
    return oldest, f"Registered Since: {oldest}"

def extract_services(record: Dict[str, Any]) -> Tuple[List[str], int, str]:
    """
    Extracts all services offered by the organization from 'Services/*' or relevant keys.
    Returns (services_list, count, comma_separated_display_string).
    """
    services = []
    
    for key, val in record.items():
        if key.startswith("Services/") or key.startswith("services/"):
            # Extract service name
            service_name = key.split("/", 1)[1].strip()
            # Check if active (truthy)
            if val is not None:
                val_str = str(val).strip().lower()
                if val_str in ["1", "true", "yes", "attached", "available"] or (val_str != "" and val_str != "0" and val_str != "false" and val_str != "no"):
                    services.append(service_name)
                    
    # Also check other potential service fields if present
    other_services = find_best_field_value(record, ["Services/Others", "services_other", "other services"])
    if other_services and str(other_services).strip() not in ["0", "no", "none", "nan", ""]:
        if str(other_services).strip() not in services and str(other_services).strip() != "1":
            services.append(f"Other: {str(other_services).strip()}")

    services_count = len(services)
    display_str = ", ".join(services) if services else "None Reported"
    return services, services_count, display_str

def extract_document_status(record: Dict[str, Any]) -> Dict[str, str]:
    """
    Audits availability for the 6 core documents.
    Maps values like 'Attached', 'Available', 'Yes' -> '✓ Available', else '✕ Not Available'.
    """
    doc_status = {}
    for doc_name in DOCUMENT_KEYS:
        val = find_best_field_value(record, [doc_name, f"15.{doc_name}"])
        is_available = False
        if val is not None:
            val_lower = str(val).strip().lower()
            # Check if negative first
            if any(neg in val_lower for neg in ["not", "unavail", "missing", "none", "no", "0", "false", "nan"]):
                is_available = False
            elif any(term in val_lower for term in ["attach", "avail", "yes", "true", "1", "provided"]):
                is_available = True
        
        doc_status[doc_name] = "✓ Available" if is_available else "✕ Not Available"
        
    return doc_status

def process_single_organization(raw_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes a single Kobo submission record into standard DEPD organization schema.
    """
    current_year = datetime.datetime.now().year
    
    # Unique ID normalization
    raw_id = raw_record.get("_id") or raw_record.get("id") or raw_record.get("record_id")
    norm_id = str(raw_id).strip() if raw_id is not None else ""

    # Field Extractions
    org_name = find_best_field_value(raw_record, ["1. Organization Name", "Organization Name", "org_name", "name"], "Unnamed Organization")
    acronym = find_best_field_value(raw_record, ["2. Acronym If any", "Acronym", "acronym", "org_acronym"], "")
    district = find_best_field_value(raw_record, ["7. District", "District", "district"], "Unknown District")
    address = find_best_field_value(raw_record, ["8. Address", "Address", "address"], "Not Available")
    
    focal_name = find_best_field_value(raw_record, ["9. Focal / Contact Person - Name", "Focal Person Name", "focal_name", "contact_person"], "Not Available")
    focal_phone = find_best_field_value(raw_record, ["9a. Focal / Contact Person - Phone", "Focal Person Phone", "focal_phone", "phone"], "Not Available")
    focal_email = find_best_field_value(raw_record, ["9b. Focal / Contact Person - Email", "Focal Person Email", "focal_email", "email"], "Not Available")

    # Coordinates
    lat_val = find_best_field_value(raw_record, ["_10. GIS Location_latitude", "latitude", "lat", "_geolocation_0"])
    lng_val = find_best_field_value(raw_record, ["_10. GIS Location_longitude", "longitude", "lng", "lon", "_geolocation_1"])
    
    # Check nested _geolocation [lat, lng]
    if lat_val is None and "_geolocation" in raw_record and isinstance(raw_record["_geolocation"], (list, tuple)) and len(raw_record["_geolocation"]) >= 2:
        lat_val = raw_record["_geolocation"][0]
        lng_val = raw_record["_geolocation"][1]

    latitude = None
    longitude = None
    has_gis = False
    
    if lat_val is not None and lng_val is not None:
        try:
            lat_f = float(str(lat_val).strip())
            lng_f = float(str(lng_val).strip())
            # Pakistan/Sindh bounding box check (lat approx 23-30, lng approx 66-72)
            if 20.0 <= lat_f <= 35.0 and 60.0 <= lng_f <= 75.0:
                latitude = lat_f
                longitude = lng_f
                has_gis = True
        except (ValueError, TypeError):
            pass

    # Infrastructure & Accessibility
    building_type = find_best_field_value(raw_record, ["11. Building Type Rented/Shared/Owned", "Building Type", "building_type"], "Not Specified")
    
    wheelchair_raw = find_best_field_value(raw_record, ["12. Wheelchair Accessible", "Wheelchair Accessible", "wheelchair"], "No")
    wheelchair = "Yes" if str(wheelchair_raw).strip().lower() in ["yes", "true", "1", "accessible"] else "No"

    sign_language_raw = find_best_field_value(raw_record, ["13. Sign Language Available", "Sign Language Available", "sign_language"], "No")
    sign_language = "Yes" if str(sign_language_raw).strip().lower() in ["yes", "true", "1", "available"] else "No"

    previous_exp = find_best_field_value(raw_record, ["21. Previous Experience in disability inclusion and services for Persons with Disabilities", "Previous Experience", "experience"], "Not Provided")

    # Registration Year (OLDEST valid year)
    reg_year, reg_since_str = extract_oldest_registration_year(raw_record)
    years_active = (current_year - reg_year) if reg_year is not None else None

    # Services
    services_list, services_count, services_display = extract_services(raw_record)

    # Documents
    doc_status = extract_document_status(raw_record)
    docs_available_count = sum(1 for status in doc_status.values() if "✓" in status)

    return {
        "_id": norm_id,
        "org_name": str(org_name).strip(),
        "acronym": str(acronym).strip() if acronym else "",
        "district": str(district).strip(),
        "address": str(address).strip(),
        "focal_name": str(focal_name).strip(),
        "focal_phone": str(focal_phone).strip(),
        "focal_email": str(focal_email).strip(),
        "latitude": latitude,
        "longitude": longitude,
        "has_gis": has_gis,
        "gis_status": "Available" if has_gis else "GIS Location Missing",
        "building_type": str(building_type).strip(),
        "wheelchair": wheelchair,
        "sign_language": sign_language,
        "previous_experience": str(previous_exp).strip(),
        "registration_year": reg_year,
        "registered_since": reg_since_str,
        "years_active": years_active,
        "services_list": services_list,
        "services_count": services_count,
        "services_display": services_display,
        "documents_status": doc_status,
        "documents_available_count": docs_available_count,
        "doc_board_members": doc_status["Board Members List"],
        "doc_meeting_minutes": doc_status["Board Meeting Minutes"],
        "doc_staff_list": doc_status["Staff Members List"],
        "doc_rent_agreement": doc_status["Building Rent Agreement"],
        "doc_audit_report": doc_status["Most Recent Audit Report"],
        "doc_bank_statement": doc_status["Bank Statement"]
    }

def process_kobo_submissions(submissions: List[Dict[str, Any]]) -> pd.DataFrame:
    """Processes raw Kobo submissions into a clean pandas DataFrame."""
    if not submissions:
        return pd.DataFrame()

    records = [process_single_organization(s) for s in submissions]
    df = pd.DataFrame(records)
    if "_id" in df.columns:
        df["_id"] = df["_id"].astype(str).str.strip()
    # Ensure registration_year is numeric (float64), not object, so map tooltip can safely call int()
    if "registration_year" in df.columns:
        df["registration_year"] = pd.to_numeric(df["registration_year"], errors="coerce")
    return df

def process_google_sheets_records(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Processes raw Google Sheets budget records into a clean pandas DataFrame."""
    if not records:
        return pd.DataFrame(columns=["_id", "fiscal_year", "amount_received", "amount_utilized", "balance", "has_financial_record"])
        
    processed = []
    for r in records:
        raw_id = r.get("_id") or r.get("id") or r.get("Record ID")
        norm_id = str(raw_id).strip() if raw_id is not None else ""
        
        fiscal_year = r.get("Fiscal Year") or r.get("fiscal_year") or "Current FY"
        amt_rec = clean_currency_to_float(r.get("Amount Received") or r.get("amount_received") or r.get("Amount Recived:"))
        amt_util = clean_currency_to_float(r.get("Utilization Amount") or r.get("amount_utilized") or r.get("Utilization  Amount:") or r.get("Amount Utilized"))
        balance = clean_currency_to_float(r.get("Balance") or r.get("balance") or (amt_rec - amt_util))
        
        utilization_rate = (amt_util / amt_rec * 100.0) if amt_rec > 0 else 0.0

        processed.append({
            "_id": norm_id,
            "fiscal_year": str(fiscal_year).strip(),
            "amount_received": amt_rec,
            "amount_utilized": amt_util,
            "balance": balance,
            "utilization_rate": utilization_rate,
            "has_financial_record": True
        })
        
    df = pd.DataFrame(processed)
    if "_id" in df.columns:
        df["_id"] = df["_id"].astype(str).str.strip()
    return df

def merge_kobo_and_financial_data(org_df: pd.DataFrame, fin_df: pd.DataFrame) -> pd.DataFrame:
    """
    Performs LEFT JOIN of Organization Profile and Financial records on `_id`.
    Preserves all organizations even if financial records are missing.
    """
    if org_df.empty:
        return pd.DataFrame()

    # Ensure _id is normalized string
    org_df = org_df.copy()
    org_df["_id"] = org_df["_id"].astype(str).str.strip()

    if fin_df.empty:
        merged = org_df.copy()
        merged["fiscal_year"] = "Not Available"
        merged["amount_received"] = 0.0
        merged["amount_utilized"] = 0.0
        merged["balance"] = 0.0
        merged["utilization_rate"] = 0.0
        merged["has_financial_record"] = False
        merged["financial_status"] = "No financial record"
    else:
        fin_df = fin_df.copy()
        fin_df["_id"] = fin_df["_id"].astype(str).str.strip()
        
        # Merge on _id
        merged = org_df.merge(fin_df, on="_id", how="left")
        
        # Fill missing financial values
        merged["amount_received"] = merged["amount_received"].fillna(0.0).astype(float)
        merged["amount_utilized"] = merged["amount_utilized"].fillna(0.0).astype(float)
        merged["balance"] = merged["balance"].fillna(0.0).astype(float)
        merged["utilization_rate"] = merged["utilization_rate"].fillna(0.0).astype(float)
        merged["has_financial_record"] = merged["has_financial_record"].fillna(False).infer_objects(copy=False).astype(bool)
        merged["fiscal_year"] = merged["fiscal_year"].fillna("Not Available").astype(str)
        merged["financial_status"] = merged["has_financial_record"].apply(
            lambda x: "Financial Record Attached" if x else "No financial record"
        )

    # Add display formatted currency strings
    merged["amount_received_display"] = merged["amount_received"].apply(lambda x: format_currency_pkr(x))
    merged["amount_utilized_display"] = merged["amount_utilized"].apply(lambda x: format_currency_pkr(x))
    merged["balance_display"] = merged["balance"].apply(lambda x: format_currency_pkr(x))

    return merged

def detect_duplicate_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Finds and returns rows with duplicate `_id` for quality inspection.
    """
    if df.empty or "_id" not in df.columns:
        return pd.DataFrame()
    
    dup_mask = df.duplicated(subset=["_id"], keep=False)
    dup_df = df[dup_mask].copy()
    return dup_df
