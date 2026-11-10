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
    page_icon="📈",
    layout="wide",
)


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    db_pass = os.getenv("MSSQL_SA_PASSWORD")
    if not db_pass:
        st.error("Brak zmiennej MSSQL_SA_PASSWORD w środowisku lub pliku .env")
        st.stop()

    url = URL.create(
        "mssql+pyodbc",
        username="sa",
        password=db_pass,
        host="localhost",
        port=1433,
        database="MarketAnalytics",
        query={
            "driver": "ODBC Driver 18 for SQL Server",
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


df = load_data()

# Nagłówek aplikacji
st.title("📊 US Sector Rotation & Macro Regime Dashboard")
st.markdown(
    "Analiza relatywnej siły sektorów S&P 500 w zależności od reżimu rynkowego (SMA 200 vs Realized Volatility)."
)

# Pasek boczny z filtrami
st.sidebar.header("Parametry Analizy")
min_date = df["trade_date"].min().date()
max_date = df["trade_date"].max().date()

selected_dates = st.sidebar.date_input(
    "Zakres dat:",
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

# 1. Metryki bieżącego stanu (Snapshot ostatniej sesji)
latest_date = df["trade_date"].max()
latest_snapshot = df[df["trade_date"] == latest_date]
latest_regime = latest_snapshot["regime_label"].iloc[0]
top_sector = latest_snapshot.loc[latest_snapshot["sector_rank"] == 1, "sector"].values[0]
worst_sector = latest_snapshot.loc[latest_snapshot["sector_rank"] == 9, "sector"].values[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Ostatnia sesja", latest_date.strftime("%Y-%m-%d"))
col2.metric("Aktualny reżim", latest_regime)
col3.metric("Lider sesji (Rank 1)", top_sector)
col4.metric("Maruder sesji (Rank 9)", worst_sector)

st.divider()

# 2. Główna Heatmapa - Średnia stopa zwrotu sektorów wg reżimów
st.subheader("🔥 Macierz Wrażliwości Sektorowej (Average Daily Return %)")

heatmap_data = (
    filtered_df.groupby(["sector", "regime_label"])["return_pct"]
    .mean()
    .unstack()
    .round(3)
)

fig_heatmap = px.imshow(
    heatmap_data,
    labels=dict(x="Reżim Rynkowy", y="Sektor", color="Średni zwrot (%)"),
    x=heatmap_data.columns,
    y=heatmap_data.index,
    color_continuous_scale="RdYlGn",
    color_continuous_midpoint=0.0,
    text_auto=True,
    aspect="auto",
)
fig_heatmap.update_layout(height=450)
st.plotly_chart(fig_heatmap, use_container_width=True)

# 3. Sekcja szczegółowa - Ranking w reżimie oraz krzywe skumulowane
c1, c2 = st.columns((1, 1))

with c1:
    st.subheader("🏆 Średnia pozycja w rankingu wg reżimu")
    target_regime = st.selectbox(
        "Wybierz reżim rynkowy:",
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
        color_continuous_scale="Viridis_r",
        labels={"sector_rank": "Średnia pozycja (1 = najlepsza)", "sector": ""},
    )
    fig_ranks.update_layout(yaxis={"autorange": "reversed"}, height=400)
    st.plotly_chart(fig_ranks, use_container_width=True)

with c2:
    st.subheader("📈 Skumulowana stopa zwrotu sektorów")
    selected_sectors = st.multiselect(
        "Wybierz sektory do porównania:",
        options=sorted(filtered_df["sector"].unique()),
        default=["Technology", "Financial Services", "Utilities"],
    )

    if selected_sectors:
        subset = filtered_df[filtered_df["sector"].isin(selected_sectors)].copy()
        subset["daily_factor"] = 1.0 + (subset["return_pct"] / 100.0)
        subset["cumulative_return"] = subset.groupby("sector")["daily_factor"].cumprod()

        fig_cum = px.line(
            subset,
            x="trade_date",
            y="cumulative_return",
            color="sector",
            labels={"trade_date": "Data", "cumulative_return": "Wzrost kapitału (Baza 1.0)"},
        )
        fig_cum.update_layout(height=400, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig_cum, use_container_width=True)
    else:
        st.info("Wybierz przynajmniej jeden sektor do wizualizacji.")
