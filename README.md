# sector-regime-pipeline
An end-to-end quantitative financial analytics pipeline and interactive dashboard. The system ingests multi-year historical price series across 10 US sector Select Sector SPDR ETFs and the S&P 500 benchmark (`SPY`), models market regimes and relative sector performance dynamically using optimized Microsoft SQL Server views (with CTEs and Window Functions), and surfaces macro sensitivity matrices via an interactive Streamlit & Plotly analytical interface.

---

## 🏛 Architecture Overview

```text
               ┌───────────────────────┐
               │     Yahoo Finance     │
               └──────────┬────────────┘
                          │ (REST API / yfinance)
                          ▼
               ┌───────────────────────┐
               │    src/load_data.py   │
               └──────────┬────────────┘
                          │ (SQLAlchemy Batch Append)
                          ▼
┌────────────────────────────────────────────────────────┐
│             Microsoft SQL Server (Docker)              │
│                                                        │
│  ┌────────────────────┐      ┌──────────────────────┐  │
│  │   dbo.tickers      │      │      dbo.prices      │  │
│  │ (Dimension Table)  │      │    (Fact Table)      │  │
│  └─────────┬──────────┘      └──────────┬───────────┘  │
│            │                            │              │
│            └──────────────┬─────────────┘              │
│                           ▼                            │
│           ┌────────────────────────────────┐           │
│           │        dbo.vw_regimes          │           │
│           │   (200d SMA, 20d Volatility)   │           │
│           └───────────────┬────────────────┘           │
│                           ▼                            │
│           ┌────────────────────────────────┐           │
│           │    dbo.vw_sector_rankings      │           │
│           │    (DENSE_RANK() by return)    │           │
│           └───────────────┬────────────────┘           │
└───────────────────────────┼────────────────────────────┘
                            │
                            ▼
               ┌───────────────────────┐
               │       src/app.py      │
               │  (Streamlit & Plotly) │
               └───────────────────────┘
```

### 1. Ingestion Layer (`src/load_data.py`)
* Extracts 10 years of split- and dividend-adjusted market price data for the broad market benchmark (`SPY`) and 9 primary sector ETFs (`XLK`, `XLF`, `XLV`, `XLE`, `XLY`, `XLP`, `XLI`, `XLU`, `XLB`).
* Validates schema and uses typed chunked ingestion (`fast_executemany=True`) to append records into dedicated tables.

### 2. Analytical Transformation Layer (T-SQL Views)
* **`dbo.vw_regimes`**:
  * Calculates daily percentage returns:
    $$\text{daily\_return}_t = \frac{P_t - P_{t-1}}{P_{t-1}}$$
  * Evaluates the 200-day Simple Moving Average ($\text{SMA}_{200}$):
    $$\text{SMA}_{200, t} = \frac{1}{200} \sum_{i=0}^{199} P_{t-i}$$
  * Computes 20-day annualized rolling volatility ($\sigma_{20d}$):
    $$\sigma_{20d, t} = \text{STDEV}(\text{daily\_return}_{t-19 \dots t}) \times \sqrt{252}$$
  * Segregates market condition into 4 distinct quadrants:
    * **`Bull_LowVol`**: $P_t \ge \text{SMA}_{200}$ and $\sigma_{20d} < 15\%$
    * **`Bull_HighVol`**: $P_t \ge \text{SMA}_{200}$ and $\sigma_{20d} \ge 15\%$
    * **`Bear_LowVol`**: $P_t < \text{SMA}_{200}$ and $\sigma_{20d} < 15\%$
    * **`Bear_HighVol`**: $P_t < \text{SMA}_{200}$ and $\sigma_{20d} \ge 15\%$
* **`dbo.vw_sector_rankings`**:
  * Calculates daily sector returns independently using windowed partitions (`PARTITION BY ticker ORDER BY trade_date`).
  * Assigns cross-sectional performance ranks for each trading day using `DENSE_RANK() OVER (PARTITION BY trade_date ORDER BY daily_return DESC)`.
  * Joins each sector's daily rank with the S&P 500 macro regime snapshot.

### 3. Presentation Layer (`src/app.py`)
* **Live Market KPIs**: Current regime status, latest session date, top-performing and lagging sectors.
* **Sensitivity Heatmap**: Average daily percentage returns across each sector/regime intersection.
* **Cross-Sectional Ranking**: Average sector positions per regime.
* **Cumulative Return Charts**: Historical capital growth trajectories with dynamic sector comparisons.

---

## 📁 Repository Structure

```text
sector-regime-pipeline/
├── .env                       # Environment credentials (git-ignored)
├── .env.example               # Template for environment configuration
├── .gitignore                 # Standard Python, IDE, and OS ignore rules
├── docker-compose.yml         # Container configuration for Microsoft SQL Server
├── README.md                  # Complete documentation and setup manual
├── requirements.txt           # Production Python library dependencies
├── sql/
│   ├── 01_create_tables.sql   # DDL: MarketAnalytics DB, constraints, indexes
│   ├── 02_views_regimes.sql   # T-SQL: SPY regime classification view
│   └── 03_views_sector_rankings.sql # T-SQL: Sector relative rank view
└── src/
    ├── app.py                 # Streamlit analytical dashboard
    └── load_data.py           # Ingestion script (yfinance -> SQL Server)
```

---

## ⚙️ Prerequisites

* **Docker & Docker Compose** (Docker Engine 20.10+ / Docker Compose v2+)
* **Python 3.11+** (Python 3.12 recommended)
* **Microsoft ODBC Driver 18 for SQL Server**:
  * *Fedora / RHEL*: `sudo dnf install msodbcsql18`
  * *Ubuntu / Debian*: `sudo apt-get install msodbcsql18`
  * *macOS*: `brew install msodbcsql18`
  * *Windows*: Included automatically or installed via Microsoft Web Platform Installer.

---

## 🚀 Step-by-Step Execution Guide

### Step 1: Clone and Configure Environment

```bash
git clone https://github.com/oliszymanski/sector-regime-pipeline.git
cd sector-regime-pipeline
```

Create a `.env` file in the repository root:

```bash
cp .env.example .env
```

Ensure your `.env` contains your target SA password:

```env
MSSQL_SA_PASSWORD=WeHaveToChangeThisPassword_2027!
ACCEPT_EULA=Y
```

---

### Step 2: Spin Up the Database Container

Start Microsoft SQL Server in detached mode:

```bash
docker compose up -d
```

Verify that the container is healthy and listening on port `1433`:

```bash
docker ps --filter "name=sqlserver"
```

---

### Step 3: Initialize Database Schema (DDL) & Views

Apply the migration scripts in sequential order. You can execute them directly inside the running container using `docker exec`:

```bash
# 1. Create database, tables, primary keys, and indexes
docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C \
  < sql/01_create_tables.sql

# 2. Compile market regime classification view
docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -d MarketAnalytics -C \
  < sql/02_views_regimes.sql

# 3. Compile sector ranking view
docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -d MarketAnalytics -C \
  < sql/03_views_sector_rankings.sql
```

*(Note: On older container builds, the executable path may be `/opt/mssql-tools/bin/sqlcmd`)*.

---

### Step 4: Configure Virtual Environment & Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux / macOS (bash/zsh):
source .venv/bin/activate
# On Linux (fish):
source .venv/bin/activate.fish
# On Windows:
.venv\Scripts\activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 5: Ingest Historical Market Data

Execute the ingestion script to pull 10 years of market data from Yahoo Finance and populate `dbo.tickers` and `dbo.prices`:

```bash
python src/load_data.py
```

Verify the ingestion directly via container CLI:

```bash
docker exec -it sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -d MarketAnalytics -C \
  -Q "SELECT TOP (10) trade_date, regime_label, sector, ticker, return_pct, sector_rank FROM dbo.vw_sector_rankings ORDER BY trade_date DESC, sector_rank ASC;"
```

---

### Step 6: Launch the Streamlit Dashboard

Start the application:

```bash
streamlit run src/app.py
```

The web dashboard will automatically open at:
```text
http://localhost:8501
```

---

## 🛠 Troubleshooting & FAQ

### 1. `ODBC Driver 18 for SQL Server: SSL Provider: [certificate verify failed]`
ODBC 18 enforces SSL encryption by default. All project scripts configure `TrustServerCertificate=yes` (or the `-C` flag in `sqlcmd`). Ensure your connection string includes:
```python
query={"driver": "ODBC Driver 18 for SQL Server", "TrustServerCertificate": "yes"}
```

### 2. `Invalid object name 'dbo.vw_regimes'`
This occurs if `sql/03_views_sector_rankings.sql` is run prior to `sql/02_views_regimes.sql`, or if executed against `master` rather than `MarketAnalytics`. Always run scripts sequentially and ensure `USE MarketAnalytics; GO` executes first.

### 3. Streamlit cache invalidation
If new records are ingested, press **`C`** inside the browser window to clear the `@st.cache_data` memory or restart the Streamlit server.
