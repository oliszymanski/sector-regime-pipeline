USE MarketAnalytics;
GO

CREATE OR ALTER VIEW dbo.vw_regimes AS
WITH spy_daily AS (
    SELECT
        trade_date,
        close_price AS spy_close,
        adj_close,

        -- Daily percentage return = (P_t - P_t-1) / P_t-1
        (adj_close - LAG(adj_close, 1) OVER (ORDER BY trade_date))
            / NULLIF(LAG(adj_close, 1) OVER (ORDER BY trade_date), 0) AS daily_return
    FROM dbo.prices
    WHERE ticker = 'SPY'
),
spy_metrics AS (
    SELECT
        trade_date,
        spy_close,

        -- 200-day Simple Moving Average
        AVG(spy_close) OVER (
            ORDER BY trade_date
            ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
        ) AS sma_200,

        -- 20-day Annualized Rolling Volatility: STDEV * sqrt(252)
        STDEV(daily_return) OVER (
            ORDER BY trade_date
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) * SQRT(252.0) AS vol_20d,
        ROW_NUMBER() OVER (ORDER BY trade_date) AS rn
    FROM spy_daily
)
SELECT
    trade_date,
    spy_close,
    ROUND(sma_200, 2) AS sma_200,
    ROUND(vol_20d, 4) AS vol_20d,
    CASE
        WHEN spy_close >= sma_200 AND vol_20d < 0.15 THEN 'Bull_LowVol'
        WHEN spy_close >= sma_200 AND vol_20d >= 0.15 THEN 'Bull_HighVol'
        WHEN spy_close < sma_200 AND vol_20d < 0.15 THEN 'Bear_LowVol'
        WHEN spy_close < sma_200 AND vol_20d >= 0.15 THEN 'Bear_HighVol'
        ELSE 'Unclassified'
    END AS regime_label
FROM spy_metrics

-- Filter out the initial warmup period where 200-day SMA is incomplete
WHERE rn >= 200;

GO