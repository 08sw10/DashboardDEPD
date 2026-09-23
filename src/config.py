"""
Configuration and secrets management for DEPD Sindh Dashboard.
Handles environment variables, Streamlit secrets, and credentials safely.
NEVER exposes private keys or tokens in logs or UI.
"""

import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Safely retrieves a configuration key from streamlit secrets, environment, or default.
    """
    # 1. Try Streamlit secrets if running inside Streamlit
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            val = st.secrets[key]
            if isinstance(val, str):
                return val.strip()
            return val
    except Exception:
        pass

    # 2. Try OS Environment variables / .env
    env_val = os.getenv(key)
    if env_val is not None and env_val.strip() != "":
        return env_val.strip()

    return default

class Config:
    """Centralized configuration properties for DEPD Dashboard."""

    # KoboToolbox API
    KOBO_BASE_URL: str = get_secret("KOBO_BASE_URL", "https://kf.kobotoolbox.org")
    KOBO_ASSET_UID: Optional[str] = get_secret("KOBO_ASSET_UID")
    KOBO_TOKEN: Optional[str] = get_secret("KOBO_TOKEN")

    # KoboToolbox synchronous CSV export (preferred for large forms / repeat groups)
    # Optional: the export-settings UID from the Kobo "Data > Download" export URL.
    # When set, the dashboard ingests the CSV export endpoint instead of JSON pagination.
    KOBO_EXPORT_SETTINGS_UID: Optional[str] = get_secret("KOBO_EXPORT_SETTINGS_UID")

    # Google Sheets API
    GOOGLE_SHEET_ID: Optional[str] = get_secret("GOOGLE_SHEET_ID")
    GOOGLE_SHEET_TAB: str = get_secret("GOOGLE_SHEET_TAB", "Budget Utilization")
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = get_secret("GOOGLE_SERVICE_ACCOUNT_JSON")
    # Optional: range to write synced Kobo rows into (used by the sync script).
    GOOGLE_SHEET_WRITE_RANGE: str = get_secret("GOOGLE_SHEET_WRITE_RANGE", "A1:Z5000")

    # Automatic dashboard refresh interval in minutes.
    # Matches the @st.cache_data(ttl=300) window: cached data is re-read after
    # 5 minutes, and the guarded app ticker pushes a visible refresh at the same
    # cadence. Set 0 to disable the timer (manual "Refresh Live Data" only).
    try:
        AUTO_REFRESH_MINUTES: int = int(str(get_secret("AUTO_REFRESH_MINUTES", "5") or "5"))
    except (TypeError, ValueError):
        AUTO_REFRESH_MINUTES = 5

    @classmethod
    def is_kobo_configured(cls) -> bool:
        """Returns True if minimum Kobo credentials are provided."""
        return bool(cls.KOBO_ASSET_UID and cls.KOBO_TOKEN)

    @classmethod
    def is_kobo_csv_export_configured(cls) -> bool:
        """True when an explicit CSV export-settings UID is provided for synchronous exports."""
        return bool(cls.KOBO_ASSET_UID and cls.KOBO_TOKEN and cls.KOBO_EXPORT_SETTINGS_UID)

    @classmethod
    def is_sheets_configured(cls) -> bool:
        """Returns True if Google Sheet ID and service account credentials exist."""
        return bool(cls.GOOGLE_SHEET_ID and (cls.GOOGLE_SERVICE_ACCOUNT_JSON or os.path.exists("secrets/service_account.json") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")))

    @classmethod
    def get_service_account_dict(cls) -> Optional[Dict[str, Any]]:
        """
        Parses Google Service Account JSON string or reads from file safely.
        Returns dict or None.
        """
        raw_json = cls.GOOGLE_SERVICE_ACCOUNT_JSON
        if raw_json:
            try:
                # If it's already a dict (from st.secrets table)
                if isinstance(raw_json, dict):
                    return raw_json
                return json.loads(raw_json)
            except Exception:
                pass

        # Check local file in secrets/service_account.json
        local_path = "secrets/service_account.json"
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        # Check GOOGLE_APPLICATION_CREDENTIALS
        adc_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if adc_path and os.path.exists(adc_path):
            try:
                with open(adc_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        return None
