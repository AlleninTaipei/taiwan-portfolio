"""
fetch_tw_stocks.py — 從證交所 ISIN 查詢頁面擷取上市/上柜普通股與 ETF 清單，更新 db/stocks_seed.csv

資料來源：
    上市 https://isin.twse.com.tw/isin/C_public.jsp?strMode=2
    上柜 https://isin.twse.com.tw/isin/C_public.jsp?strMode=4
擷取「股票」與「ETF」區段，不含受益憑證、認購權證、存託憑證等其他證券類別。

執行方式：
    python scripts/fetch_tw_stocks.py
"""
import io
import sys

sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

import csv
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URLS = {
    "上市": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2",
    "上柜": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4",
}

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "db" / "stocks_seed.csv"

CODE_NAME_RE = re.compile(r"^(\S+)\s+(.+)$")

SECTIONS = {"股票", "ETF"}


def fetch_stock_rows(market: str, url: str):
    resp = requests.get(url, timeout=30)
    resp.encoding = "big5"
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find_all("table")[1]

    section = ""
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) == 1:
            section = cells[0].get_text(strip=True)
            continue
        if len(cells) < 5 or section not in SECTIONS:
            continue

        code_name = cells[0].get_text(strip=True)
        industry = cells[4].get_text(strip=True)

        m = CODE_NAME_RE.match(code_name)
        if not m:
            continue
        code, name = m.group(1), m.group(2)
        rows.append((code, name, section, industry))

    print(f"{market}: 取得 {len(rows)} 筆資料", file=sys.stderr)
    return rows


def main():
    all_rows = []
    for market, url in URLS.items():
        all_rows.extend(fetch_stock_rows(market, url))

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["股票代號", "股票名稱", "類別", "產業分類"])
        writer.writerows(all_rows)

    print(f"完成，共 {len(all_rows)} 筆，已輸出至 {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
