import os
from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="Market Regime & Sector Rotation",
    layout="wide",
)

# ==============================================================================
# DATA LAYER
# ==============================================================================


@st.cache_data(ttl=3600)
def load_analytical_data() -> pd.DataFrame:
    db_pass = os.getenv("MSSQL_SA_PASSWORD")
    if not db_pass:
        st.error(
            "Missing MSSQL_SA_PASSWORD in the environment or .env configuration."
        )
        st.stop()

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", 1433))
    db_user = os.getenv("DB_USER", "sa")
    db_name = os.getenv("DB_NAME", "MarketAnalytics")
    db_driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

    url = URL.create(
        "mssql+pyodbc",
        username=db_user,
        password=db_pass,
        host=db_host,
        port=db_port,
        database=db_name,
        query={
            "driver": db_driver,
            "TrustServerCertificate": "yes",
        },
    )
    engine = create_engine(url)

    query = """
        SELECT
            trade_date,
            regime_label,
            sector,
            ticker,
            CAST(return_pct AS FLOAT) AS return_pct,
            sector_rank
        FROM dbo.vw_sector_rankings
        ORDER BY trade_date ASC;
    """
    df = pd.read_sql(query, engine)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


df = load_analytical_data()

# ==============================================================================
# HEADER & SIDEBAR FILTERS
# ==============================================================================

st.title("Macro Regime & Sector Rotation Dashboard")
st.markdown(
    "Quantitative framework tracking US sector performance across market volatility and trend regimes."
)

st.sidebar.header("Filter Configuration")
min_date = df["trade_date"].min().date()
max_date = df["trade_date"].max().date()

selected_dates = st.sidebar.date_input(
    "Historical Window:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_dt, end_dt = selected_dates
    filtered_df = df[
        (df["trade_date"].dt.date >= start_dt)
        & (df["trade_date"].dt.date <= end_dt)
    ]
else:
    filtered_df = df

# ==============================================================================
# EXECUTIVE SUMMARY METRICS (SNAPSHOT & RECOMMENDED TILT)
# ==============================================================================

latest_date = df["trade_date"].max()
latest_snapshot = df[df["trade_date"] == latest_date]
current_regime = latest_snapshot["regime_label"].iloc[0]

# Historical performance within the active regime to compute Recommended Tilt
regime_history = df[df["regime_label"] == current_regime]
tilt_analysis = (
    regime_history.groupby(["sector", "ticker"])["sector_rank"]
    .mean()
    .reset_index()
    .sort_values(by="sector_rank", ascending=True)
)

top_tilt = tilt_analysis.iloc[0]
recommended_sector = top_tilt["sector"]
recommended_ticker = top_tilt["ticker"]
recommended_rank = top_tilt["sector_rank"]

top_session_sector = latest_snapshot.loc[
    latest_snapshot["sector_rank"] == 1, "sector"
].values[0]
worst_session_sector = latest_snapshot.loc[
    latest_snapshot["sector_rank"] == 9, "sector"
].values[0]

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Latest Session", latest_date.strftime("%Y-%m-%d"))
col2.metric("Current Regime", current_regime)
col3.metric(
    "Recommended Tilt",
    f"{recommended_ticker} ({recommended_sector})",
    f"Avg Rank: {recommended_rank:.2f}",
)
col4.metric("Session Leader", top_session_sector)
col5.metric("Session Laggard", worst_session_sector)

st.divider()

# ==============================================================================
# SENSITIVITY MATRIX (HEATMAP)
# ==============================================================================

st.subheader("Historical Sector Sensitivity Matrix")
st.caption(
    "Average daily percentage return (%) broken down by macro regime quadrant."
)

heatmap_data = (
    filtered_df.groupby(["sector", "regime_label"])["return_pct"]
    .mean()
    .unstack()
    .round(3)
)

fig_heatmap = px.imshow(
    heatmap_data,
    labels=dict(
        x="Market Regime", y="Sector", color="Avg Daily Return (%)"
    ),
    x=heatmap_data.columns,
    y=heatmap_data.index,
    color_continuous_scale="RdYlGn",
    color_continuous_midpoint=0.0,
    text_auto=True,
    aspect="auto",
)
fig_heatmap.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0))
st.plotly_chart(fig_heatmap, use_container_width=True)

# ==============================================================================
# REGIME BREAKDOWN & CUMULATIVE PERFORMANCE
# ==============================================================================

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Average Sector Rank in Regime")
    st.caption("Lower numerical rank indicates superior relative performance.")

    target_regime = st.selectbox(
        "Select Market Regime for Ranking Analysis:",
        options=sorted(filtered_df["regime_label"].unique()),
    )

    regime_ranks = (
        filtered_df[filtered_df["regime_label"] == target_regime]
        .groupby(["sector", "ticker"])["sector_rank"]
        .mean()
        .reset_index()
        .sort_values(by="sector_rank", ascending=True)
    )

    fig_ranks = px.bar(
        regime_ranks,
        x="sector_rank",
        y="sector",
        orientation="h",
        color="sector_rank",
        color_continuous_scale="Blues_r",
        labels={
            "sector_rank": "Average Rank (1 = Highest Return)",
            "sector": "Sector",
        },
    )
    fig_ranks.update_layout(
        yaxis={"autorange": "reversed"},
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig_ranks, use_container_width=True)

with right_col:
    st.subheader("Cumulative Growth Trajectory")
    st.caption("Historical capital growth of $1.00 across selected sectors.")

    selected_sectors = st.multiselect(
        "Select Sectors to Track:",
        options=sorted(filtered_df["sector"].unique()),
        default=["Technology", "Financial Services", "Utilities"],
    )

    if selected_sectors:
        subset = filtered_df[
            filtered_df["sector"].isin(selected_sectors)
        ].copy()
        subset["daily_factor"] = 1.0 + (subset["return_pct"] / 100.0)
        subset["cumulative_return"] = subset.groupby("sector")[
            "daily_factor"
        ].cumprod()

        fig_cum = px.line(
            subset,
            x="trade_date",
            y="cumulative_return",
            color="sector",
            labels={
                "trade_date": "Date",
                "cumulative_return": "Normalized Equity Curve ($)",
            },
        )
        fig_cum.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=30, b=0),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig_cum, use_container_width=True)
    else:
        st.info("Select at least one sector to display cumulative returns.")
