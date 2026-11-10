"""
tables needed:
    1. tickers: (ticker, ticker_name, sector),
    2. prices: (trade_date, ticker, close_price, adj_close, volume),
    3. regimes: (trade_date, spy_close, sma_200, vol_20d, regime_label)
"""

#======================================================================================
#   IMPORTS
#======================================================================================

import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

import yfinance as yf
import pandas as pd


load_dotenv()

ticker_data = {
    "SPY": "Broad Market",
    "XLK": "Technology",
    "XLF": "Financial Services",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLY": "Consumer Cyclical",
    "XLP": "Consumer Defensive",
    "XLI": "Industrials",
    "XLU": "Utilities",
    "XLB": "Basic Materials",
}

#======================================================================================
#   FUNCTIONS
#======================================================================================

def get_ticker_data( ls_tickers : list ) -> pd.DataFrame:
    tickers = {
        'ticker' : [],
        'ticker_name' : [],
        'sector' : []
    }

    for ticker in ls_tickers:
        info = yf.Ticker(ticker).info

        tickers['ticker'].append(ticker)
        tickers['ticker_name'].append( info.get('longName') )
        tickers['sector'].append( ticker_data.get(ticker) )

    df_tickers = pd.DataFrame(tickers)

    return df_tickers



def get_prices_data( ls_tickers : list ) -> pd.DataFrame:
    prices = {
        'trade_date' : [],
        'ticker' : [],
        'close_price' : [],
        'adj_close' : [],
        'volume' : []
    }

    for ticker in ticker_data:
        info = yf.Ticker(ticker).history(period='10y', interval='1d', auto_adjust=False)

        prices['trade_date'].extend(info.index.date)
        prices['ticker'].extend([ticker] * len(info))
        prices['close_price'].extend(info['Close'].tolist())
        prices['adj_close'].extend(info['Adj Close'].tolist())
        prices['volume'].extend(info['Volume'].tolist())


    df_prices = pd.DataFrame(prices)

    return df_prices



#======================================================================================
#   DATA PREPERATION
#======================================================================================

ls_tickers = list(ticker_data.keys())

df_tickers = get_ticker_data( ls_tickers=ls_tickers )
df_prices_data = get_prices_data( ls_tickers=ls_tickers )

print(df_tickers.head(20))



#======================================================================================
#   DB CONNECTION
#======================================================================================

db_pass = os.getenv("MSSQL_SA_PASSWORD")
if not db_pass: raise ValueError("Variable empty or it doesn't exist.")

url = URL.create(
    "mssql+pyodbc",
    username='sa',
    password=db_pass,
    host='localhost',
    port=1433,
    database="MarketAnalytics",
    query={
        "driver" : "ODBC Driver 18 for SQL Server",
        "TrustServerCertificate" : "yes"
    }
)

engine = create_engine(url)

df_tickers.to_sql(          # tickers table
    name='tickers',
    con=engine,
    schema='dbo',
    if_exists='append',
    index=False
)

df_prices_data.to_sql(      # prices table
    name='prices',
    con=engine,
    schema='dbo',
    if_exists='append',
    index=False
)
