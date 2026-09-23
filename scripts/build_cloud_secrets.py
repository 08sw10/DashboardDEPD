"""
Build a Streamlit-Community-Cloud-ready secrets TOML from local credentials.

Combines .streamlit/secrets.toml with secrets/service_account.json by inlining
the service-account JSON into GOOGLE_SERVICE_ACCOUNT_JSON as a '''...''' string
(the JSON file itself is never deployed to the cloud).

Output: secrets/cloud_secrets_ready.toml  (inside gitignored secrets/ dir).

Usage:  python scripts/build_cloud_secrets.py
"""

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_TOML = ROOT / ".streamlit" / "secrets.toml"
SRC_SA = ROOT / "secrets" / "service_account.json"
OUT = ROOT / "secrets" / "cloud_secrets_ready.toml"

PLACEHOLDER = 'GOOGLE_SERVICE_ACCOUNT_JSON = ""'


def main() -> None:
    toml_text = SRC_TOML.read_text(encoding="utf-8")
    if PLACEHOLDER not in toml_text:
        print(f"ERROR: expected {PLACEHOLDER!r} in {SRC_TOML}")
        raise SystemExit(1)

    sa_json = json.loads(SRC_SA.read_text(encoding="utf-8"))  # validate JSON
    sa_inline = json.dumps(sa_json, indent=2)

    out_text = toml_text.replace(
        PLACEHOLDER, f"GOOGLE_SERVICE_ACCOUNT_JSON = '''\n{sa_inline}\n'''"
    )

    # Write WITHOUT BOM and with \n — tomllib/Streamlit both require clean UTF-8.
    OUT.write_text(out_text, encoding="utf-8", newline="\n")

    # Validate: must parse as TOML and every required key must be non-empty.
    parsed = tomllib.loads(OUT.read_text(encoding="utf-8"))
    required = [
        "KOBO_BASE_URL",
        "KOBO_ASSET_UID",
        "KOBO_TOKEN",
        "GOOGLE_SHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
    ]
    missing = [k for k in required if not str(parsed.get(k, "")).strip()]
    if missing:
        print(f"ERROR: empty required keys after build: {missing}")
        raise SystemExit(1)
    json.loads(parsed["GOOGLE_SERVICE_ACCOUNT_JSON"])  # must remain valid JSON

    print(f"OK: wrote {OUT} ({OUT.stat().st_size} bytes);")
    print(f"  all {len(required)} required keys non-empty; service-account JSON valid.")
    print("  Copy the ENTIRE file content into:")
    print("  Streamlit Cloud -> Manage app -> Settings -> Secrets -> Save -> Restart app.")


if __name__ == "__main__":
    main()