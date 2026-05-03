"""
fetch_prices.py — 從 yfinance 抓取台股收盤價，寫入 daily_prices 資料表

執行方式：
    python scripts/fetch_prices.py
"""

import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import yfinance as yf
import pandas as pd
from db_ops import get_all_tickers, upsert_prices


def main():
    tickers = get_all_tickers()

    if not tickers:
        print("stocks 資料表是空的，請先用 add_transaction.py 新增股票。")
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

        count = upsert_prices(ticker, df[["Close"]])
        print(f"    寫入 {count} 筆")

    print("\n完成！")


if __name__ == "__main__":
    main()
