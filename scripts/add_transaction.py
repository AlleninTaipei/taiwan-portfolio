"""
add_transaction.py — 互動式 CLI，新增一筆買賣交易紀錄

執行方式：
    python scripts/add_transaction.py
"""

import io
import sys

sys.stdin  = io.TextIOWrapper(sys.stdin.buffer,  encoding="utf-8")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from datetime import date
from db_ops import stock_exists, insert_stock, insert_transaction


def _ensure_stock(ticker: str) -> None:
    if stock_exists(ticker):
        return
    name   = input(f"  股票 {ticker} 不在資料庫，請輸入股票名稱（例如：台積電）：").strip()
    sector = input("  產業分類（可留空）：").strip() or None
    insert_stock(ticker, name, sector)
    print(f"  已新增 {ticker} 至股票基本資料。")


def main():
    print("=== 新增交易紀錄 ===\n")

    ticker = input("股票代號（例如：2330）：").strip().upper()

    trade_date_str = input("交易日期（YYYY-MM-DD，按 Enter 使用今天）：").strip()
    trade_date = date.fromisoformat(trade_date_str) if trade_date_str else date.today()

    trade_type = ""
    while trade_type not in ("BUY", "SELL"):
        trade_type = input("買/賣（輸入 BUY 或 SELL）：").strip().upper()

    shares = int(input("股數（整數）：").strip())
    price  = float(input("成交價（元）：").strip())
    fee    = float(input("手續費（元，按 Enter 預設 0）：").strip() or "0")

    _ensure_stock(ticker)
    new_id = insert_transaction(ticker, trade_date, trade_type, shares, price, fee)

    action = "買入" if trade_type == "BUY" else "賣出"
    print(f"\n✓ 已新增：{trade_date} {action} {ticker} {shares} 股 @ {price} 元（id={new_id}）")


if __name__ == "__main__":
    main()
