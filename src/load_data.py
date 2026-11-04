"""
data fetched:
    sectors that are in SPY (included):
        - SPY
        - XLK
        - XLF
        - XLV
        - XLE
        - XLY
        - XLP
        - XLI
        - XLU
        - XLB
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()

db_pass = os.getenv("MSSQL_SA_PASSWORD")

if not db_pass: raise ValueError("Variable empty or it doesn't exist.")

engine = create_engine(f'mssql+mssqlpython://sa:{db_pass}@localhost:1433/master?TrustServerCertificate=yes')

