"""
fetch_prices.py
---------------
Fetches 1 year of daily closing prices from Yahoo Finance (yfinance)
for all companies in the database and stores them in stock_prices table.
Run from: C:\Users\Jignesh\Desktop\bse_portal\scripts\
Usage:    python fetch_prices.py
"""

import sys
import os
import time
import pandas as pd
import yfinance as yf
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_connect import get_engine

# Install yfinance if not already done:
#   python -m pip install yfinance


if __name__ == "__main__":
    print("=" * 60)
    print("BSE Portal — Stock Price Fetcher (yfinance)")
    print("=" * 60)

    try:
        engine = get_engine()
        conn   = engine.connect()
    except Exception as e:
        print(f"❌ Cannot connect to MySQL: {e}")
        sys.exit(1)

    # Get all active companies and their NSE symbols
    companies = conn.execute(text(
        "SELECT company_id, company_name, nse_symbol FROM companies WHERE is_active = 1"
    )).fetchall()

    print(f"Found {len(companies)} companies in database\n")

    total_inserted = 0
    total_failed   = 0

    for company_id, company_name, nse_symbol in companies:
        if not nse_symbol:
            print(f"  ⚠️  {company_name}: no NSE symbol, skipping")
            total_failed += 1
            continue

        ticker_str = f"{nse_symbol}.NS"   # .NS = NSE listing on Yahoo Finance
        print(f"  Fetching {ticker_str:20s} for {company_name}...", end=" ")

        try:
            ticker = yf.Ticker(ticker_str)
            hist   = ticker.history(period="1y")   # last 12 months of daily prices

            if hist.empty:
                print(f"❌ No data returned")
                total_failed += 1
                continue

            rows_inserted = 0
            for price_date, price_row in hist.iterrows():
                try:
                    close_price = float(price_row["Close"])
                    volume      = int(price_row["Volume"]) if pd.notna(price_row["Volume"]) else None
                    date_str    = price_date.strftime("%Y-%m-%d")

                    conn.execute(text(
                        "INSERT IGNORE INTO stock_prices "
                        "(company_id, price_date, close_price, volume) "
                        "VALUES (:cid, :d, :p, :v)"
                    ), {
                        "cid": company_id,
                        "d":   date_str,
                        "p":   close_price,
                        "v":   volume,
                    })
                    rows_inserted += 1

                except Exception as row_err:
                    pass   # skip individual bad rows silently

            conn.commit()
            print(f"✅ {rows_inserted} days")
            total_inserted += rows_inserted

        except Exception as e:
            print(f"❌ Error: {e}")
            total_failed += 1

        # Be polite to Yahoo Finance — small delay between requests
        time.sleep(0.5)

    conn.close()

    print("\n" + "=" * 60)
    print(f"Done!  ✅ Price rows inserted: {total_inserted}   ❌ Companies failed: {total_failed}")
    print("\nSample check — run this in MySQL Workbench:")
    print("  SELECT c.company_name, sp.price_date, sp.close_price")
    print("  FROM stock_prices sp")
    print("  JOIN companies c ON c.company_id = sp.company_id")
    print("  ORDER BY sp.price_date DESC LIMIT 10;")
    print("=" * 60)
