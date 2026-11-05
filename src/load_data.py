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

#======================================================================================
#   FUNCTIONS
#======================================================================================

def get_ticker_data( ls_tickers : list ):

    tickers = {'ticker' : [], 'ticker_name' : [], 'sector' : []}

    for ticker in ls_tickers:
        info = yf.Ticker(ticker).info

        tickers['ticker'].append(ticker)
        tickers['ticker_name'].append( info.get('longName') )
        tickers['sector'].append( ticker_data.get(ticker) )

    df_tickers = pd.DataFrame(tickers)

    return df_tickers


def get_prices_data(): return



def get_regimes(): return


#======================================================================================
#   DATA
#======================================================================================

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

ls_tickers = list(ticker_data.keys())

prices = {}
regimes = {}

df_tickers = get_ticker_data( ls_tickers=ls_tickers )

print(df_tickers)


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
    database="master",
    query={
        "driver" : "ODBC Driver 18 for SQL Server",
        "TrustServerCertificate" : "yes"
    }
)

engine = create_engine(url)

df_tickers.to_sql(
    name='tickers',
    con=engine,
    schema='dbo',
    if_exists='replace',
    index=False
)
