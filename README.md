# DEPD Sindh — Live Organization & Funding Management Dashboard

Production-ready, live monitoring and data management dashboard for the **Department of Empowerment of Persons with Disabilities (DEPD), Government of Sindh**.

Integrates **KoboToolbox API v2** (Organization Profiles) and **Google Sheets API** (Financial & Budget Utilization) joined on unique record key `_id`, with interactive **Folium GIS mapping**, comprehensive data quality auditing, dynamic filtering, and containerized Docker deployment.

---

## 🏛️ System Architecture

```text
┌───────────────────────────┐      ┌───────────────────────────┐
│   KoboToolbox API v2      │      │     Google Sheets API     │
│   (Organization Profiles) │      │   (Budget Utilization)    │
└─────────────┬─────────────┘      └─────────────┬─────────────┘
              │                                  │
              │  _id (Normalized String)         │  _id (Normalized String)
              ▼                                  ▼
┌──────────────────────────────────────────────────────────────┐
│                    Data Processing Engine                    │
│  - Field Normalization & Typo Tolerance                      │
│  - Oldest Registration Date & Dynamic Active Years           │
│  - Services Discovery & Document Availability Audit          │
│  - Robust Left-Join on _id & Duplicate _id Detection         │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│             Streamlit Executive Dashboard (Port 8501)        │
│  - Government of Sindh Branded Header (Sindh & DEPD Logos)   │
│  - 5-Minute API Caching with Live Data Refresh Controls      │
│  - Interactive Sindh Folium GIS Map (Clustering & Popups)    │
│  - Analytics, Searchable Directories, and Data Quality Audit │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔒 Security & Credentials Policy

- **Zero Hardcoded Secrets**: No API tokens, private keys, or passwords exist in source code.
- **Git Protection**: `.gitignore` excludes `.env`, `.streamlit/secrets.toml`, `secrets/`, `*.json.secret`, `*.key`, and `*.pem`.
- **Safe Fallback**: If credentials are not yet configured, the system operates in demo mode using schema-compliant verified fallback datasets rather than crashing or exposing technical stack traces.
- **Do not embed secrets in the repo.** If a private key or API token is ever
  shared or committed, **rotate it immediately** in the Google Cloud Console /
  KoboToolbox account, then store the new value only in `.streamlit/secrets.toml`
  or environment variables.

### Required Environment Variables / Secrets:

| Secret Key | Description | Example |
| :--- | :--- | :--- |
| `KOBO_BASE_URL` | KoboToolbox server endpoint | `https://kf.kobotoolbox.org` |
| `KOBO_ASSET_UID` | Asset UID of the organization form | `aX9sK...` |
| `KOBO_TOKEN` | Kobo API Token | `9c8a7b...` |
| `GOOGLE_SHEET_ID` | Google Sheet ID containing budget utilization | `1BxiMVs...` |
| `GOOGLE_SHEET_TAB` | Sheet tab/worksheet name | `Budget Utilization` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service Account JSON string or file path | `{"type": "service_account", ...}` |
| `KOBO_EXPORT_SETTINGS_UID` | *(optional)* Kobo export-settings UID for synchronous CSV ingest | `esf6EqmZNrk7GizTVWkavef` |
| `GOOGLE_SHEET_WRITE_RANGE` | *(optional)* A1 range used by the Sheets sync writer | `A1:Z5000` |
| `AUTO_REFRESH_MINUTES` | *(optional)* Auto-refresh interval in minutes (data cache TTL is 300s) | `5` |

---

## 🚀 Getting Started

### 1. Local Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/depd-dashboard.git
cd depd-dashboard

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure Secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your live API credentials

# Run Streamlit Application
streamlit run app.py
```

Application will open at `http://localhost:8501`.

---

## 🐳 Docker Deployment

The application is fully containerized and production-ready.

```bash
# Build Docker image
docker build -t depd-dashboard .

# Run Docker container locally
docker run -d -p 8501:8501 --name depd-dashboard depd-dashboard

# Run with environment variables
docker run -d -p 8501:8501 \
  -e KOBO_BASE_URL="https://kf.kobotoolbox.org" \
  -e KOBO_ASSET_UID="your_asset_uid" \
  -e KOBO_TOKEN="your_kobo_token" \
  -e GOOGLE_SHEET_ID="your_sheet_id" \
  -e GOOGLE_SHEET_TAB="Budget Utilization" \
  -e GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}' \
  --name depd-dashboard depd-dashboard
```

Access container at: `http://localhost:8501`

---

## 🧪 Testing & Verification

Run automated test suite:

```bash
python -m pytest tests/ -v
```

### Test Coverage Includes:
- **`test_data_processor.py`**: `_id` string normalization, Left Join integrity, Oldest registration date selection across multiple registration types, Dynamic active years calculation, Services extraction, Document compliance status, Duplicate `_id` auditing.
- **`test_kobo_client.py`**: KoboToolbox v2 API token auth, automatic pagination following `next` URL, and network timeout handling.
- **`test_sheets_client.py`**: Header fuzzy normalization handling spelling variations and extra spacing.
- **`test_map_builder.py`**: Folium map generation, district boundary overlay, and HTML popup generation.

---

## 📊 Dashboard Modules & Features

### 1. 📊 Executive Dashboard
- **Top KPIs**: Total Organizations, Districts Covered, Total Funding Received, Total Amount Utilized, Total Balance.
- **Visual Analytics**: Organizations by District, Received vs. Utilized by District, Services Distribution, Registration Timeline.
- **Accessibility & Infrastructure**: Wheelchair accessibility %, Sign language support %, Owned vs. Rented premises.

### 2. 🏢 Organizations Directory
- Live search across organization names, districts, addresses, and focal persons.
- Comprehensive data table with dynamic sorting and full dossier inspection.
- Filtered CSV download.

### 3. 💰 Funding & Budget Utilization
- Financial management KPIs, utilization rate percentages.
- Tabular breakdown of allocated vs utilized funds.
- Dedicated budget utilization CSV export.

### 4. 🔄 Live Data, Auto-Refresh & Kobo → Sheets Sync

- **Live KoboToolbox ingestion** via API v2 JSON pagination, or the
  **synchronous CSV export** endpoint when `KOBO_EXPORT_SETTINGS_UID` is set
  (recommended for large forms and forms with repeat groups).
- **Automatic refresh every 5 minutes**: data is cached with
  `@st.cache_data(ttl=300)` and a guarded app ticker pushes a visible refresh on
  the same cadence (set `AUTO_REFRESH_MINUTES=0` to disable the timer). A
  **Refresh Live Data** button in the sidebar forces an immediate pull.
- **Optional Google Sheets sync** sits behind a sidebar feature flag
  (*⬆️ Sync Kobo → Google Sheets*) that writes the live Kobo rows into the sheet.
- **Resilient cache fallback**: on any API outage the dashboard serves the last
  successful on-disk snapshot (`data/cache/`, git-ignored) and shows a yellow
  **● Cached Snapshot** badge with the snapshot timestamp — it never goes blank.
- **Optional Kobo → Google Sheets sync** so any BI tool (Power BI, Looker
  Studio, Excel) can read a single shared sheet. Run it on demand or on a loop:

  ```bash
  # One-shot: fetch Kobo and overwrite the Google Sheet
  python scripts/sync_kobo_to_sheets.py

  # Continuous loop every 5 minutes
  python scripts/sync_kobo_to_sheets.py --loop 300

  # Dry run: fetch + dump a local CSV, do not write to Sheets
  python scripts/sync_kobo_to_sheets.py --no-write --csv data/kobo_export.csv
  ```

#### Scheduling the sync

| Platform | How to schedule |
| :--- | :--- |
| **Windows** | Task Scheduler → *Create Basic Task* → daily, repeat every 5 min → Action: `python D:\DEPD\DashboardDEPD\scripts\sync_kobo_to_sheets.py` |
| **Linux/macOS** | `crontab -e` → `*/5 * * * * cd /path/to/DashboardDEPD && /path/to/python scripts/sync_kobo_to_sheets.py >> sync.log 2>&1` |
| **Docker** | Add a sidecar container running the loop command, or a host cron invoking `docker exec` |
| **Google Cloud** | Cloud Scheduler → HTTP trigger to a Cloud Run job running the script |

#### Connecting external dashboards

- **Google Sheets source (recommended):** point Power BI / Looker Studio / Excel
  at the synced spreadsheet (`GOOGLE_SHEET_ID` → `GOOGLE_SHEET_TAB`). The sheet is
  overwritten on each sync, so consumers always see fresh data.
- **Direct Kobo API:** use the JSON endpoint
  `https://kf.kobotoolbox.org/api/v2/assets/<ASSET_UID>/data.json` with the
  header `Authorization: Token <KOBO_TOKEN>`.

#### Limitations

- Kobo CSV export **flattens repeat groups** into single columns; nested repeat
  structures are lossy. Use the JSON export if you need intact nested groups.
- The synchronous CSV export timeout scales with form size — very large exports
  may need a longer `timeout` or an async export job.
- Respect Kobo rate limits — do not sync more frequently than every few minutes.

### 5. 🗺️ Sindh Interactive GIS Map
- Centered on Sindh province with Marker Clustering.
- Responsive hover tooltip with Organization Name, District, and Registration Year.
- Detailed interactive HTML popup cards showing focal contacts, accessibility, provided services, document audits, and funding summary.
- Sindh District Boundaries overlay.
- Graceful handling of organizations without coordinates (flagged without crashing the map).

### 6. 🔍 Data Quality & Auditing
- Real-time audit metrics:
  - Organizations with vs. missing GIS coordinates
  - Organizations with missing registration dates
  - Organizations with missing focal contact details
  - Organizations with vs. without joined financial records
  - Duplicate `_id` detector and audit breakdown table

---

## 📁 Repository Structure

```text
depd-dashboard/
├── app.py                      # Streamlit application entrypoint
├── src/
│   ├── __init__.py
│   ├── config.py               # Safe environment & secrets manager
│   ├── kobo_client.py          # Kobo API client with pagination
│   ├── sheets_client.py        # Google Sheets client with header normalization
│   ├── data_processor.py       # Normalization, oldest date logic & left join on _id
│   ├── map_builder.py          # Folium GIS map with clustering & rich popups
│   ├── data_quality.py         # Data quality & integrity auditor
│   └── ui.py                   # Header branding, CSS styling, KPIs & charts
├── assets/
│   ├── sindh_government_logo.png   # Official Government of Sindh Emblem
│   └── depd_logo.png               # Official DEPD Logo
├── data/
│   ├── sindh_districts.geojson     # Sindh district spatial boundaries
│   └── sample_data.py              # Schema-matched verified sample dataset
├── tests/
│   ├── __init__.py
│   ├── test_data_processor.py
│   ├── test_kobo_client.py
│   ├── test_sheets_client.py
│   └── test_map_builder.py
├── .streamlit/
│   ├── config.toml                 # Streamlit server & theme settings
│   └── secrets.toml.example        # Secrets template
├── .github/
│   └── workflows/
│       └── deploy.yml              # CI/CD workflow
├── Dockerfile                      # Production Docker container
├── requirements.txt                # Python dependencies
├── .gitignore                      # Security-hardened gitignore
└── README.md                       # Documentation
```

---

## 🏛️ Government of Sindh & DEPD

**Department of Empowerment of Persons with Disabilities**  
Government of Sindh, Pakistan.
