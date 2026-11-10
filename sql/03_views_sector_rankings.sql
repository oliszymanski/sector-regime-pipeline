USE MarketAnalytics;
GO

CREATE OR ALTER VIEW dbo.vw_sector_rankings AS
WITH sector_returns AS (
SELECT
   p.trade_date,
   t.sector,
   p.ticker,
   p.adj_close,
   ( p.adj_close - LAG(p.adj_close, 1) OVER (PARTITION BY p.ticker ORDER BY p.trade_date) )
   / NULLIF(LAG(p.adj_close, 1) OVER (PARTITION BY p.ticker ORDER BY p.trade_date), 0) AS daily_return
FROM dbo.prices AS p
INNER JOIN dbo.tickers AS t ON p.ticker = t.ticker
WHERE p.ticker <> 'SPY'
)

SELECT
   sr.trade_date,
   sr.sector,
   sr.ticker,
   ROUND( sr.daily_return * 100, 2 ) AS return_pct,
   r.regime_label,
   DENSE_RANK() OVER (
      PARTITION BY sr.trade_date ORDER BY sr.daily_return DESC
   ) AS sector_rank
FROM sector_returns as sr
INNER JOIN dbo.vw_regimes AS r ON sr.trade_date = r.trade_date;
GO
