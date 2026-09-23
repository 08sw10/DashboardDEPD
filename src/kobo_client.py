"""
KoboToolbox v2 API Client with pagination and authentication.
Fetches organization profile submissions securely.
Includes disk-cache fallback so the dashboard never goes blank during API outages.
"""

import os
import csv
import json
import logging
import requests
from io import StringIO
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from src.config import Config

logger = logging.getLogger(__name__)

# ── Disk cache paths ──────────────────────────────────────────────────────────
CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
KOBO_CACHE = CACHE_DIR / "kobo_submissions.json"
KOBO_META  = CACHE_DIR / "kobo_last_sync.json"


def _load_kobo_cache() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Reads the last successful Kobo snapshot from disk."""
    if not KOBO_CACHE.exists():
        return [], None
    try:
        rows = json.loads(KOBO_CACHE.read_text(encoding="utf-8"))
        meta = json.loads(KOBO_META.read_text(encoding="utf-8")) if KOBO_META.exists() else {}
        ts = meta.get("last_sync", "unknown time")
        return rows, f"Showing snapshot from {ts} — live API unreachable."
    except Exception:
        return [], None


def _save_kobo_cache(rows: List[Dict[str, Any]]) -> None:
    """Persists a successful Kobo fetch to disk."""
    try:
        KOBO_CACHE.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        KOBO_META.write_text(
            json.dumps({"last_sync": datetime.now().isoformat(timespec="seconds"), "rows": len(rows)}),
            encoding="utf-8"
        )
    except Exception:
        pass


def fetch_kobo_csv_export(
    base_url: Optional[str] = None,
    asset_uid: Optional[str] = None,
    token: Optional[str] = None,
    export_settings_uid: Optional[str] = None,
    timeout: int = 60
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Fetches submissions via the KoboToolbox synchronous CSV export endpoint:

        {base_url}/api/v2/assets/{asset_uid}/export-settings/{export_settings_uid}/data.csv

    Preferred over JSON pagination for large forms and for forms containing
    repeat groups (the CSV export flattens them). Returns the SAME tuple
    contract as fetch_kobo_submissions(): (rows, error_or_notice).

    Rows are returned as a list of dicts keyed by the CSV header names, so the
    existing data_processor normalization pipeline works unchanged.
    """
    # ── Developer offline-simulation toggle ───────────────────────────────────
    if os.getenv("DEPD_FORCE_CACHE") == "1":
        rows, notice = _load_kobo_cache()
        return rows, notice or "Simulating offline — Kobo cache empty."

    base_url = (base_url or Config.KOBO_BASE_URL or "https://kf.kobotoolbox.org").rstrip("/")
    asset_uid = asset_uid or Config.KOBO_ASSET_UID
    token = token or Config.KOBO_TOKEN
    export_settings_uid = export_settings_uid or Config.KOBO_EXPORT_SETTINGS_UID

    if not asset_uid or not token:
        return [], "KoboToolbox Asset UID or API Token is not configured."
    if not export_settings_uid:
        return [], "KoboToolbox Export Settings UID is not configured."

    csv_url = f"{base_url}/api/v2/assets/{asset_uid}/export-settings/{export_settings_uid}/data.csv"
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "text/csv, application/csv, text/plain, */*",
    }

    try:
        response = requests.get(csv_url, headers=headers, timeout=timeout, allow_redirects=True)

        if response.status_code == 401:
            return [], "Unauthorized: Please verify your KoboToolbox API Token."
        elif response.status_code == 404:
            return [], "Kobo CSV export not found: verify Asset UID and Export Settings UID."
        elif response.status_code >= 400:
            cached, notice = _load_kobo_cache()
            if cached:
                return cached, notice
            return [], f"Kobo CSV export HTTP Error {response.status_code}: {response.reason}"

        # Kobo CSV exports may be comma- OR semicolon-delimited depending on
        # locale/settings — sniff the delimiter from the header line.
        text = response.text.lstrip("\ufeff")  # strip BOM if present
        first_line = next((ln for ln in text.splitlines() if ln.strip()), "")
        delimiter = ";" if first_line.count(";") > first_line.count(",") else ","

        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
        # Strip stray whitespace around header names (e.g. '  ;"Region"...').
        if reader.fieldnames:
            reader.fieldnames = [(fn or "").strip() for fn in reader.fieldnames]

        rows = []
        for r in reader:
            clean = {}
            for k, v in r.items():
                key = (k or "").strip()
                if key:
                    clean[key] = v
            # Skip completely blank trailing rows
            if any(str(val).strip() for val in clean.values() if val is not None):
                rows.append(clean)

        # ── Success: persist to disk cache ────────────────────────────────────
        _save_kobo_cache(rows)
        return rows, None

    except requests.exceptions.Timeout:
        cached, notice = _load_kobo_cache()
        if cached:
            return cached, notice
        return [], "Connection timeout while reaching KoboToolbox CSV export."
    except requests.exceptions.ConnectionError:
        cached, notice = _load_kobo_cache()
        if cached:
            return cached, notice
        return [], "Unable to connect to KoboToolbox server. Check internet connection."
    except Exception as e:
        logger.error(f"Kobo CSV Export Error: {str(e)}")
        cached, notice = _load_kobo_cache()
        if cached:
            return cached, notice
        return [], f"Error retrieving KoboToolbox CSV export: {type(e).__name__}"


def fetch_kobo_submissions(
    base_url: Optional[str] = None,
    asset_uid: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = 30
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Fetches all submissions from KoboToolbox API v2 with automatic pagination.

    When a CSV export-settings UID is configured, it prefers the synchronous CSV
    export endpoint (handles repeat groups and large forms deterministically) and
    falls back to JSON pagination otherwise.

    Args:
        base_url: Kobo base URL (defaults to Config.KOBO_BASE_URL)
        asset_uid: Kobo asset UID (defaults to Config.KOBO_ASSET_UID)
        token: Kobo API Token (defaults to Config.KOBO_TOKEN)
        timeout: Request timeout in seconds

    Returns:
        Tuple of (submissions_list, error_message)
    """
    # Prefer the CSV export endpoint when an export-settings UID is configured
    # (handles repeat groups and large forms deterministically). Falls back to
    # JSON pagination otherwise. Only applies when the caller did NOT explicitly
    # pass credentials (explicit args = JSON pagination intent, e.g. unit tests).
    if asset_uid is None and token is None and Config.is_kobo_csv_export_configured():
        rows, err = fetch_kobo_csv_export(
            base_url=base_url, asset_uid=asset_uid, token=token, timeout=max(timeout, 60)
        )
        if rows or err:
            return rows, err
    # ── Developer offline-simulation toggle ───────────────────────────────────
    if os.getenv("DEPD_FORCE_CACHE") == "1":
        rows, notice = _load_kobo_cache()
        return rows, notice or "Simulating offline — Kobo cache empty."

    base_url = (base_url or Config.KOBO_BASE_URL or "https://kf.kobotoolbox.org").rstrip("/")
    asset_uid = asset_uid or Config.KOBO_ASSET_UID
    token = token or Config.KOBO_TOKEN

    if not asset_uid or not token:
        return [], "KoboToolbox Asset UID or API Token is not configured."

    url = f"{base_url}/api/v2/assets/{asset_uid}/data.json"
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json"
    }

    all_results: List[Dict[str, Any]] = []
    page_count = 0
    max_pages = 200  # Safety limit for thousands of records

    try:
        current_url: Optional[str] = url
        while current_url and page_count < max_pages:
            page_count += 1
            logger.info(f"Fetching Kobo page {page_count}...")

            response = requests.get(current_url, headers=headers, timeout=timeout)

            if response.status_code == 401:
                return [], "Unauthorized: Please verify your KoboToolbox API Token."
            elif response.status_code == 404:
                return [], f"Asset not found: Please verify your Kobo Asset UID."
            elif response.status_code >= 400:
                # Server-side error — attempt cache fallback
                cached, notice = _load_kobo_cache()
                if cached:
                    return cached, notice
                return [], f"Kobo API HTTP Error {response.status_code}: {response.reason}"

            data = response.json()

            # Kobo v2 returns results in 'results' key
            if isinstance(data, dict):
                results = data.get("results", [])
                if isinstance(results, list):
                    all_results.extend(results)
                current_url = data.get("next")
            elif isinstance(data, list):
                all_results.extend(data)
                current_url = None
            else:
                break

        # ── Success: persist to disk cache ────────────────────────────────────
        _save_kobo_cache(all_results)
        return all_results, None

    except requests.exceptions.Timeout:
        cached, notice = _load_kobo_cache()
        if cached:
            return cached, notice
        return [], "Connection timeout while reaching KoboToolbox API."
    except requests.exceptions.ConnectionError:
        cached, notice = _load_kobo_cache()
        if cached:
            return cached, notice
        return [], "Unable to connect to KoboToolbox server. Check internet connection."
    except Exception as e:
        logger.error(f"Kobo API Error: {str(e)}")
        cached, notice = _load_kobo_cache()
        if cached:
            return cached, notice
        return [], f"Error retrieving KoboToolbox data: {type(e).__name__}"


def fetch_kobo_dataframe():
    """
    Convenience wrapper: returns Kobo submissions as a pandas DataFrame.

    Returns (df, error_or_notice). On failure returns an empty DataFrame plus
    the error/notice string (same contract as fetch_kobo_submissions()).
    """
    import pandas as pd

    rows, err = fetch_kobo_submissions()
    return pd.DataFrame(rows), err
