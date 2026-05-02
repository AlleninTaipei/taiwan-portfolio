"""
fetch_prices.py — 從 yfinance 抓取台股收盤價，寫入 daily_prices 資料表

執行方式：
    python scripts/fetch_prices.py
"""

import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import psycopg2
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/taiwan_portfolio")


def get_tickers(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT ticker FROM stocks ORDER BY ticker")
        return [row[0] for row in cur.fetchall()]


def upsert_prices(conn, ticker: str, df: pd.DataFrame):
    with conn.cursor() as cur:
        for price_date, row in df.iterrows():
            cur.execute(
                """
                INSERT INTO daily_prices (ticker, price_date, close_price)
                VALUES (%s, %s, %s)
                ON CONFLICT (ticker, price_date) DO UPDATE
                    SET close_price = EXCLUDED.close_price
                """,
                (ticker, price_date.date(), float(row["Close"].iloc[0]) if hasattr(row["Close"], "iloc") else float(row["Close"])),
            )
    conn.commit()


def main():
    conn = psycopg2.connect(DB_URL)
    tickers = get_tickers(conn)

    if not tickers:
        print("stocks 資料表是空的，請先執行 sample_data.sql 或用 add_transaction.py 新增股票。")
        conn.close()
        return

    print(f"共 {len(tickers)} 支股票，開始抓取收盤價...\n")

    for ticker in tickers:
        df = pd.DataFrame()
        for suffix in (".TW", ".TWO"):
            tw_ticker = ticker + suffix
            print(f"  抓取 {tw_ticker} ...")
            try:
                df = yf.download(tw_ticker, period="3mo", auto_adjust=True, progress=False)
                if not df.empty:
                    break
            except Exception as e:
                print(f"    錯誤：{e}")

        if df.empty:
            print(f"    警告：{ticker} 在 .TW / .TWO 均無資料，跳過")
            continue

        upsert_prices(conn, ticker, df[["Close"]])
        print(f"    寫入 {len(df)} 筆")

    conn.close()
    print("\n完成！")


if __name__ == "__main__":
    main()
