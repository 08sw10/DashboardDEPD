"""
DEPD Sindh — Kobo -> Google Sheets Sync (standalone, schedulable)

Fetches the latest KoboToolbox submissions and (optionally) writes them into a
Google Sheet so that the dashboard — or any downstream BI tool (Power BI,
Looker Studio, Excel) — always reads a fresh, shareable data source.

USAGE
-----
    python scripts/sync_kobo_to_sheets.py                 # fetch + write + print summary
    python scripts/sync_kobo_to_sheets.py --once          # same (single run)
    python scripts/sync_kobo_to_sheets.py --loop 300      # run every 300 seconds
    python scripts/sync_kobo_to_sheets.py --no-write      # fetch only (dry run, writes local CSV)
    python scripts/sync_kobo_to_sheets.py --csv out.csv   # also dump a local CSV

CREDENTIALS (environment variables or .streamlit/secrets.toml):
    KOBO_BASE_URL             (default https://kf.kobotoolbox.org)
    KOBO_ASSET_UID            e.g. atnnG8BW8S5tvsxXFA96PV
    KOBO_TOKEN                your Kobo API token         [SECRET]
    KOBO_EXPORT_SETTINGS_UID  export-settings UID from the Kobo download URL (optional)
    GOOGLE_SHEET_ID           target spreadsheet ID
    GOOGLE_SHEET_TAB          target tab name (default "Budget Utilization")
    GOOGLE_SERVICE_ACCOUNT_JSON  service account JSON (string) OR
    secrets/service_account.json  local file path

SECURITY: Never hard-code the token or key. Use env vars / secrets. The private
key previously shared in chat must be rotated in Google Cloud Console.
"""

import os
import sys
import csv
import time
import json
import logging
import argparse
from pathlib import Path

# Allow running as a standalone script from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.kobo_client import fetch_kobo_submissions, fetch_kobo_csv_export
from src.sheets_client import write_records_to_google_sheets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kobo_sync")


def fetch_latest() -> list:
    """Fetches the latest Kobo rows (CSV export preferred, JSON fallback)."""
    rows, err = fetch_kobo_submissions()
    if err:
        logger.error("Kobo fetch error: %s", err)
    if not rows:
        logger.error("No Kobo rows retrieved. Aborting sync.")
        sys.exit(2)
    logger.info("Fetched %d rows from KoboToolbox.", len(rows))
    return rows


def write_local_csv(rows: list, csv_path: str) -> None:
    """Writes rows to a local CSV for inspection / offline use."""
    if not rows:
        return
    headers = []
    for r in rows:
        for k in r.keys():
            if k not in headers:
                headers.append(k)
    out = Path(csv_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to local CSV: %s", len(rows), out)


def sync_once(do_write: bool, csv_path: str | None) -> None:
    """Performs a single fetch -> (optional) write cycle."""
    rows = fetch_latest()

    if csv_path:
        write_local_csv(rows, csv_path)

    if not do_write:
        logger.info("--no-write set: skipping Google Sheets write (dry run).")
        return

    if not Config.is_sheets_configured():
        logger.warning(
            "Google Sheets is not configured (missing GOOGLE_SHEET_ID or service account). "
            "Skipping write."
        )
        return

    written, err = write_records_to_google_sheets(rows)
    if err:
        logger.error("Google Sheets write error: %s", err)
        sys.exit(3)
    logger.info("Google Sheets updated successfully (%d data rows written).", written)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync KoboToolbox -> Google Sheets.")
    parser.add_argument("--no-write", action="store_true", help="Fetch only; do not write to Google Sheets.")
    parser.add_argument("--csv", type=str, default=None, help="Also write fetched rows to this local CSV path.")
    parser.add_argument("--loop", type=int, default=0, help="Repeat every N seconds (0 = run once).")
    args = parser.parse_args()

    if args.loop and args.loop > 0:
        logger.info("Starting sync loop every %d seconds. Press Ctrl+C to stop.", args.loop)
        while True:
            try:
                sync_once(do_write=not args.no_write, csv_path=args.csv)
            except SystemExit:
                raise
            except Exception as exc:
                logger.exception("Unhandled sync error: %s", exc)
            time.sleep(args.loop)
    else:
        sync_once(do_write=not args.no_write, csv_path=args.csv)


if __name__ == "__main__":
    main()