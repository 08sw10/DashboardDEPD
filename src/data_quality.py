"""
Data Quality and Integrity Auditor for DEPD Sindh Dashboard.
Evaluates completeness of GIS coordinates, registration dates,
focal contact details, financial records, and detects duplicate IDs.
"""

from typing import Dict, Any, Tuple
import pandas as pd

def compute_data_quality_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes exact data completeness and integrity metrics across the joined dataset.
    Does NOT invent arbitrary score algorithms.
    """
    if df.empty:
        return {
            "total_organizations": 0,
            "with_gis": 0,
            "missing_gis": 0,
            "with_reg_year": 0,
            "missing_reg_year": 0,
            "with_focal_contact": 0,
            "missing_focal_contact": 0,
            "with_financial_record": 0,
            "missing_financial_record": 0,
            "duplicate_ids_count": 0
        }

    total = len(df)
    
    # 1. GIS Coordinates
    with_gis = int(df["has_gis"].sum()) if "has_gis" in df.columns else 0
    missing_gis = total - with_gis

    # 2. Registration Year
    with_reg_year = int(df["registration_year"].notna().sum()) if "registration_year" in df.columns else 0
    missing_reg_year = total - with_reg_year

    # 3. Contact Info (Focal name, phone, or email)
    if "focal_phone" in df.columns and "focal_name" in df.columns:
        valid_contact = df[
            (df["focal_name"].notna()) & (df["focal_name"] != "Not Available") & (df["focal_name"] != "") &
            (df["focal_phone"].notna()) & (df["focal_phone"] != "Not Available") & (df["focal_phone"] != "")
        ]
        with_focal_contact = len(valid_contact)
    else:
        with_focal_contact = 0
    missing_focal_contact = total - with_focal_contact

    # 4. Financial Records
    with_financial_record = int(df["has_financial_record"].sum()) if "has_financial_record" in df.columns else 0
    missing_financial_record = total - with_financial_record

    # 5. Duplicate _id
    duplicate_ids_count = 0
    if "_id" in df.columns:
        duplicate_ids_count = int(df.duplicated(subset=["_id"], keep=False).sum())

    return {
        "total_organizations": total,
        "with_gis": with_gis,
        "missing_gis": missing_gis,
        "with_reg_year": with_reg_year,
        "missing_reg_year": missing_reg_year,
        "with_focal_contact": with_focal_contact,
        "missing_focal_contact": missing_focal_contact,
        "with_financial_record": with_financial_record,
        "missing_financial_record": missing_financial_record,
        "duplicate_ids_count": duplicate_ids_count
    }

def get_missing_gis_records(df: pd.DataFrame) -> pd.DataFrame:
    """Returns subset of organizations missing GIS coordinates."""
    if df.empty or "has_gis" not in df.columns:
        return pd.DataFrame()
    cols = ["_id", "org_name", "district", "address", "focal_name", "focal_phone"]
    available_cols = [c for c in cols if c in df.columns]
    return df[~df["has_gis"]][available_cols].copy()

def get_missing_registration_records(df: pd.DataFrame) -> pd.DataFrame:
    """Returns subset of organizations missing registration year."""
    if df.empty or "registration_year" not in df.columns:
        return pd.DataFrame()
    cols = ["_id", "org_name", "district", "focal_name", "focal_phone"]
    available_cols = [c for c in cols if c in df.columns]
    return df[df["registration_year"].isna()][available_cols].copy()

def get_missing_financial_records(df: pd.DataFrame) -> pd.DataFrame:
    """Returns subset of organizations without matching Google Sheets budget records."""
    if df.empty or "has_financial_record" not in df.columns:
        return pd.DataFrame()
    cols = ["_id", "org_name", "district", "registration_year", "focal_name"]
    available_cols = [c for c in cols if c in df.columns]
    return df[~df["has_financial_record"]][available_cols].copy()

def get_duplicate_id_records(df: pd.DataFrame) -> pd.DataFrame:
    """Returns subset of organizations sharing duplicate `_id`."""
    if df.empty or "_id" not in df.columns:
        return pd.DataFrame()
    cols = ["_id", "org_name", "district", "focal_name", "focal_phone"]
    available_cols = [c for c in cols if c in df.columns]
    dup_mask = df.duplicated(subset=["_id"], keep=False)
    return df[dup_mask][available_cols].sort_values(by="_id").copy()
