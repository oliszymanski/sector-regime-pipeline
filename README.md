# US Sector Rotation & Macro Regime Pipeline

An end-to-end quantitative data pipeline and interactive analytics platform that evaluates cross-sectional sector momentum across distinct macroeconomic market regimes.

The system ingests 10 years of daily adjusted equity and ETF price series via Python, enforces strict relational schema constraints and indexing within Microsoft SQL Server (Docker), computes rolling trend and volatility indicators using advanced T-SQL analytical window functions, and delivers an interactive Streamlit dashboard.

---

## Architecture Overview

```text
sector-regime-pipeline/
├── sql/
│   ├── 01_create_tables.sql          # DDL: Database creation, tables, constraints, and indexes
│   ├── 02_views_regimes.sql          # T-SQL View: SPY 200 SMA, 20d rolling volatility, regime labels
│   └── 03_views_sector_rankings.sql  # T-SQL View: Daily sector returns, DENSE_RANK, regime join
├── src/
│   ├── load_data.py                  # Ingestion: yfinance extraction, validation, batch insertion
│   └── app.py                        # Presentation: Streamlit interactive dashboard & Plotly charts
├── .env                              # Environment credentials (excluded from version control)
├── .env.example                      # Template for environment configuration
├── .gitignore                        # Git exclusion rules
├── docker-compose.yml                # SQL Server 2025 container specification
├── requirements.txt                  # Pinned Python package dependencies
└── README.md                         # Project documentation
```

---

## Quantitative Methodology

### 1. Market Regime Classification (`dbo.vw_regimes`)

Market conditions are categorized using the SPDR S&P 500 ETF Trust (`SPY`) as the broader market benchmark across two orthogonal dimensions: **Trend** and **Realized Volatility**.

* **Daily Asset Return**:
  $$\text{Return}_t = \frac{P_t - P_{t-1}}{P_{t-1}}$$

* **Trend Filter ($200$-Day Simple Moving Average)**:
  $$\text{SMA}_{200, t} = \frac{1}{200} \sum_{i=0}^{199} P_{t-i}$$

* **Volatility Filter ($20$-Day Annualized Realized Volatility)**:
  $$\sigma_{20d, t} = \text{STDEV}\left(\text{Return}_{t-19 \dots t}\right) \times \sqrt{252}$$

* **Regime Matrix**:
  The benchmark state at time $t$ is mapped into one of four distinct macroeconomic quadrants:
  * **Bull_LowVol**: $P_t \ge \text{SMA}_{200, t} \quad \text{and} \quad \sigma_{20d, t} < 0.15$
  * **Bull_HighVol**: $P_t \ge \text{SMA}_{200, t} \quad \text{and} \quad \sigma_{20d, t} \ge 0.15$
  * **Bear_LowVol**: $P_t < \text{SMA}_{200, t} \quad \text{and} \quad \sigma_{20d, t} < 0.15$
  * **Bear_HighVol**: $P_t < \text{SMA}_{200, t} \quad \text{and} \quad \sigma_{20d, t} \ge 0.15$

*A 200-session warmup window (`WHERE rn >= 200`) ensures rolling window estimates are fully populated before downstream joins.*

---

### 2. Relative Sector Strength & Cross-Sectional Ranking (`dbo.vw_sector_rankings`)

For each trading session $t$, daily percentage returns are calculated across the 9 primary Select Sector SPDR ETFs:

$$\text{SectorReturn}_{s, t} = \frac{\text{AdjClose}_{s, t} - \text{AdjClose}_{s, t-1}}{\text{AdjClose}_{s, t-1}} \times 100$$

Cross-sectional rank is assigned via `DENSE_RANK()`:

$$\text{Rank}_{s, t} = \text{DENSE\_RANK}() \quad \text{OVER} \left( \text{PARTITION BY } t \quad \text{ORDER BY } \text{SectorReturn}_{s, t} \text{ DESC} \right)$$

* A rank of $1$ designates the relative session outperformer; a rank of $9$ designates the relative underperformer.

---

## Tech Stack

* **Database Engine**: Microsoft SQL Server 2025 (`mcr.microsoft.com/mssql/server:2025-latest`)
* **Data Processing & Pipeline**: Python 3.12, SQLAlchemy 2.0, pyodbc, yfinance, Pandas
* **Database Driver**: Microsoft ODBC Driver 18 for SQL Server
* **Transformation & Business Logic**: T-SQL (Common Table Expressions, Analytic Window Functions `LAG`, `AVG OVER`, `STDEV OVER`, `DENSE_RANK`)
* **Visualization & Serving**: Streamlit, Plotly Express

---

## Installation & Setup Guide

### 1. Prerequisites

Ensure the following tools are installed on the host operating system:

* [Docker](https://docs.docker.com/engine/install/) & Docker Compose
* Python 3.11+ (Python 3.12 recommended)
* [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)

### 2. Clone the Repository & Configure Environment

```bash
git clone https://github.com/oliszymanski/sector-regime-pipeline.git
cd sector-regime-pipeline

# Create local environment configuration
cp .env.example .env
```

Edit `.env` to define your database password:

```env
MSSQL_SA_PASSWORD=YourStrongPasswordHere
```

### 3. Initialize Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

---

## Execution Pipeline

### Step 1: Start the Database Container

Deploy the Microsoft SQL Server container:

```bash
docker compose up -d
```

Verify the container is operational:

```bash
docker ps --filter "name=sqlserver"
```

---

### Step 2: Initialize Database Schema (DDL)

Execute `sql/01_create_tables.sql` to initialize the `MarketAnalytics` database, relational tables, constraints, and performance indexes:

```bash
docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C \
  < sql/01_create_tables.sql
```

---

### Step 3: Ingest Historical Financial Data

Run the ingestion script to extract 10 years of daily OHLCV series for benchmark and sector tickers from Yahoo Finance and load them into SQL Server:

```bash
python src/load_data.py
```

---

### Step 4: Compile Analytical Views

Compile the transformation logic in sequential order:

```bash
# 1. Compile Market Regime View
docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -d MarketAnalytics -C \
  < sql/02_views_regimes.sql

# 2. Compile Cross-Sectional Sector Rankings View
docker exec -i sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -d MarketAnalytics -C \
  < sql/03_views_sector_rankings.sql
```

---

### Step 5: Verify Pipeline Output

Execute an ad-hoc query against the final compiled view:

```bash
docker exec -it sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -d MarketAnalytics -C \
  -Q "SELECT TOP (10) trade_date, regime_label, sector, ticker, return_pct, sector_rank FROM dbo.vw_sector_rankings ORDER BY trade_date DESC, sector_rank ASC;"
```

---

### Step 6: Launch the Streamlit Dashboard

Start the web application:

```bash
streamlit run src/app.py
```

The application will be accessible at `http://localhost:8501`.

---

## Interactive Dashboard Features

1. **Current Regime Snapshot (KPIs)**: Instant display of latest session date, active market regime label, session outperformer (Rank 1), and session laggard (Rank 9).
2. **Sector Sensitivity Heatmap**: Cross-tabulation of average daily return (%) across the 4 macroeconomic quadrants, highlighting defensive versus cyclical behavior.
3. **Regime-Specific Rank Distribution**: Horizontal ranking breakdown of sector strength within any selected regime filter.
4. **Normalized Cumulative Return Curves**: Dynamic time-series asset growth simulations allowing multi-sector comparative performance analysis.
