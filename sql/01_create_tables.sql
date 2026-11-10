SELECT TOP(10) * FROM dbo.tickers;
SELECT TOP(10) * FROM dbo.prices;


IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MarketAnalytics') BEGIN
CREATE DATABASE MarketAnalytics;
END;

GO

USE MarketAnalytics;
GO

IF OBJECT_ID( 'dbo.prices', 'U' ) IS NOT NULL DROP TABLE dbo.prices;    -- drops dbs if exist on server and creates new ones
IF OBJECT_ID( 'dbo.tickers', 'U' ) IS NOT NULL DROP TABLE dbo.tickers;
GO

CREATE TABLE dbo.tickers (
   ticker VARCHAR(10) NOT NULL,
   ticker_name VARCHAR(150) NULL,
   sector VARCHAR(100) NOT NULL,
   CONSTRAINT PK_tickers PRIMARY KEY CLUSTERED (ticker)
);

CREATE TABLE dbo.prices (
   trade_date DATE NOT NULL,
   ticker VARCHAR(10) NOT NULL,
   close_price DECIMAL(18, 4) NOT NULL,
   adj_close DECIMAL(18, 4) NOT NULL,
   volume BIGINT NOT NULL,

   CONSTRAINT PK_prices PRIMARY KEY CLUSTERED (ticker, trade_date),
   CONSTRAINT FK_prices_tickers FOREIGN KEY (ticker) REFERENCES dbo.tickers(ticker)
);
