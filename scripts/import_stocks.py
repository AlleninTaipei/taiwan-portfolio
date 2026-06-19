"""
import_stocks.py — 將股票清單 CSV 批次 upsert 進 stocks 資料表

CSV 格式（utf-8-sig，標頭為 股票代號,股票名稱,產業分類）：
    預設讀取 db/stocks_seed.csv，可由 fetch_tw_stocks.py 重新產生或手動維護。
    已存在的 ticker 會更新名稱與產業分類，不存在的則新增；
    缺少代號或名稱的資料行會被跳過並列出行號，不會中止整批匯入。

執行方式：
    python scripts/import_stocks.py [csv 路徑，預設 db/stocks_seed.csv]
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import csv
from pathlib import Path

from db_ops import stock_exists, insert_stock, update_stock

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "db" / "stocks_seed.csv"


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV

    inserted = updated = skipped = 0

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            ticker = (row.get("股票代號") or "").strip()
            name   = (row.get("股票名稱") or "").strip()
            sector = (row.get("產業分類") or "").strip() or None

            if not ticker or not name:
                print(f"  第 {line_no} 行缺少股票代號或名稱，跳過", file=sys.stderr)
                skipped += 1
                continue

            if stock_exists(ticker):
                update_stock(ticker, name, sector)
                updated += 1
            else:
                insert_stock(ticker, name, sector)
                inserted += 1

    print(f"完成：新增 {inserted} 筆，更新 {updated} 筆，跳過 {skipped} 筆")


if __name__ == "__main__":
    main()
