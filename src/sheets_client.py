"""
Google Sheets API Client with Service Account authentication.
Fetches financial and budget utilization records with robust column header normalization.
Includes disk-cache fallback so the dashboard never goes blank during API outages.
"""

import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from src.config import Config

logger = logging.getLogger(__name__)

# Standard target columns
COL_ID = "_id"
COL_FISCAL_YEAR = "Fiscal Year"
COL_AMOUNT_RECEIVED = "Amount Received"
COL_AMOUNT_UTILIZED = "Utilization Amount"
COL_BALANCE = "Balance"

# ── Disk cache paths ──────────────────────────────────────────────────────────
CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SHEETS_CACHE = CACHE_DIR / "sheets_records.json"
SHEETS_META  = CACHE_DIR / "sheets_last_sync.json"


def _load_sheets_cache() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Reads the last successful Sheets snapshot from disk."""
    if not SHEETS_CACHE.exists():
        return [], None
    try:
        rows = json.loads(SHEETS_CACHE.read_text(encoding="utf-8"))
        meta = json.loads(SHEETS_META.read_text(encoding="utf-8")) if SHEETS_META.exists() else {}
        ts = meta.get("last_sync", "unknown time")
        return rows, f"Showing snapshot from {ts} — Sheets API unreachable."
    except Exception:
        return [], None


def _save_sheets_cache(rows: List[Dict[str, Any]]) -> None:
    """Persists a successful Sheets fetch to disk."""
    try:
        SHEETS_CACHE.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        SHEETS_META.write_text(
            json.dumps({"last_sync": datetime.now().isoformat(timespec="seconds"), "rows": len(rows)}),
            encoding="utf-8"
        )
    except Exception:
        pass


def normalize_header_name(header: str) -> str:
    """
    Normalizes a column header string by removing colons, collapsing whitespace,
    and handling common spelling/casing variations.
    """
    if not isinstance(header, str):
        return ""

    clean = header.strip()
    # Remove trailing/leading colons and punctuation
    clean = re.sub(r"[:\s]+", " ", clean).strip()
    clean_lower = clean.lower()

    if clean_lower in ["_id", "id", "record id", "kobo id", "organization id", "org id"]:
        return COL_ID
    if "fiscal" in clean_lower and "year" in clean_lower:
        return COL_FISCAL_YEAR
    if "reciv" in clean_lower or "receiv" in clean_lower or "amount rec" in clean_lower:
        return COL_AMOUNT_RECEIVED
    if "utiliz" in clean_lower or "expend" in clean_lower or "spent" in clean_lower:
        return COL_AMOUNT_UTILIZED
    if "balance" in clean_lower or "remaining" in clean_lower:
        return COL_BALANCE

    return clean


def fetch_google_sheets_records(
    sheet_id: Optional[str] = None,
    sheet_tab: Optional[str] = None,
    service_account_dict: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Fetches rows from a Google Sheet using service account credentials.

    Args:
        sheet_id: Google Spreadsheet ID (defaults to Config.GOOGLE_SHEET_ID)
        sheet_tab: Sheet tab / worksheet name (defaults to Config.GOOGLE_SHEET_TAB)
        service_account_dict: Parsed Service Account JSON dict (defaults to Config.get_service_account_dict())

    Returns:
        Tuple of (normalized_records_list, error_message)
    """
    # ── Developer offline-simulation toggle ───────────────────────────────────
    if os.getenv("DEPD_FORCE_CACHE") == "1":
        rows, notice = _load_sheets_cache()
        return rows, notice or "Simulating offline — Sheets cache empty."

    sheet_id = sheet_id or Config.GOOGLE_SHEET_ID
    sheet_tab = sheet_tab or Config.GOOGLE_SHEET_TAB
    service_account_dict = service_account_dict or Config.get_service_account_dict()

    if not sheet_id:
        return [], "Google Sheet ID is not configured."
    if not service_account_dict:
        return [], "Google Service Account credentials are not configured."

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]

        credentials = Credentials.from_service_account_info(
            service_account_dict,
            scopes=scopes
        )

        gc = gspread.authorize(credentials)

        # Open by key
        spreadsheet = gc.open_by_key(sheet_id)

        # Get worksheet
        if sheet_tab:
            try:
                worksheet = spreadsheet.worksheet(sheet_tab)
            except gspread.exceptions.WorksheetNotFound:
                # Fallback to first worksheet if named tab is not found
                logger.warning(f"Worksheet '{sheet_tab}' not found, falling back to first sheet.")
                worksheet = spreadsheet.get_worksheet(0)
        else:
            worksheet = spreadsheet.get_worksheet(0)

        raw_records = worksheet.get_all_records()

        if not raw_records:
            # Try getting raw values if headers had empty cells
            all_values = worksheet.get_all_values()
            if not all_values or len(all_values) < 2:
                return [], "Google Sheet appears to be empty."

            headers = [normalize_header_name(h) for h in all_values[0]]
            records = []
            for row in all_values[1:]:
                row_dict = {}
                for idx, val in enumerate(row):
                    if idx < len(headers) and headers[idx]:
                        row_dict[headers[idx]] = val
                records.append(row_dict)
            # ── Success: persist to disk cache ────────────────────────────────
            _save_sheets_cache(records)
            return records, None

        # Normalize keys in raw_records
        normalized_records = []
        for r in raw_records:
            norm_r = {}
            for k, v in r.items():
                normalized_key = normalize_header_name(k)
                if normalized_key:
                    norm_r[normalized_key] = v
            normalized_records.append(norm_r)

        # ── Success: persist to disk cache ────────────────────────────────────
        _save_sheets_cache(normalized_records)
        return normalized_records, None

    except Exception as exc:
        # Map specific gspread exceptions gracefully
        exc_type = type(exc).__name__
        if "SpreadsheetNotFound" in exc_type:
            err_msg = "Google Spreadsheet not found. Please verify GOOGLE_SHEET_ID and service account sharing permissions."
        elif "APIError" in exc_type:
            logger.error(f"Google Sheets API Error: {str(exc)}")
            err_msg = "Google Sheets API access error. Check service account permissions on the sheet."
        else:
            logger.error(f"Google Sheets Error: {str(exc)}")
            err_msg = f"Error reading Google Sheets: {exc_type}"

        # ── Failure: attempt cache fallback ───────────────────────────────────
        cached, notice = _load_sheets_cache()
        if cached:
            return cached, notice
        return [], err_msg


def write_records_to_google_sheets(
    records: List[Dict[str, Any]],
    sheet_id: Optional[str] = None,
    sheet_tab: Optional[str] = None,
    service_account_dict: Optional[Dict[str, Any]] = None,
    write_range: Optional[str] = None,
    clear_first: bool = True
) -> Tuple[int, Optional[str]]:
    """
    Writes (overwrites) records into a Google Sheet using the service account.

    Used by the optional Kobo -> Google Sheets sync so the dashboard (or any BI
    tool such as Power BI / Looker Studio) can read from the sheet.

    Args:
        records: List of flat dicts to write. Column order = union of keys in
                 first-seen order.
        sheet_id / sheet_tab / service_account_dict: same as the reader.
        write_range: A1 range to write into (defaults to Config.GOOGLE_SHEET_WRITE_RANGE).
        clear_first: If True, clears the target range before writing.

    Returns:
        (rows_written, error_message_or_None)
    """
    sheet_id = sheet_id or Config.GOOGLE_SHEET_ID
    sheet_tab = sheet_tab or Config.GOOGLE_SHEET_TAB
    service_account_dict = service_account_dict or Config.get_service_account_dict()
    write_range = write_range or Config.GOOGLE_SHEET_WRITE_RANGE

    if not records:
        return 0, "No records supplied to write."
    if not sheet_id:
        return 0, "Google Sheet ID is not configured."
    if not service_account_dict:
        return 0, "Google Service Account credentials are not configured."

    # Build header + rows preserving first-seen column order
    headers: List[str] = []
    for r in records:
        for k in r.keys():
            if k not in headers:
                headers.append(k)

    values: List[List[Any]] = [headers]
    for r in records:
        values.append([r.get(h, "") for h in headers])

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        # Full (read-write) spreadsheets scope is required for clearing/writing.
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(service_account_dict, scopes=scopes)
        gc = gspread.authorize(credentials)

        spreadsheet = gc.open_by_key(sheet_id)
        try:
            worksheet = spreadsheet.worksheet(sheet_tab) if sheet_tab else spreadsheet.get_worksheet(0)
        except gspread.exceptions.WorksheetNotFound:
            # Create the tab if it does not exist yet
            worksheet = spreadsheet.add_worksheet(title=sheet_tab, rows=len(values) + 10, cols=len(headers) + 2)

        if clear_first:
            worksheet.clear()

        worksheet.update(values=values, range_name=f"A1:{_col_letter(len(headers))}{len(values)}")

        written = len(values) - 1  # exclude header row
        logger.info(f"Wrote {written} rows to Google Sheet '{sheet_tab}'.")
        return written, None

    except Exception as exc:
        exc_type = type(exc).__name__
        logger.error(f"Google Sheets write error: {exc}")
        return 0, f"Error writing to Google Sheets: {exc_type}"


def _col_letter(col_idx: int) -> str:
    """Converts a 1-based column index to its spreadsheet letter (1 -> A, 27 -> AA)."""
    letters = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters
