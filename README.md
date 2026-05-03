# 台股投資組合損益 Dashboard

以 PostgreSQL + Python + Streamlit 建立的個人台股損益追蹤工具，同時作為學習 PostgreSQL 核心功能的實作專案。

## 功能

- **損益總覽** — 總投入成本、目前市值、損益金額、整體報酬率、持倉圓餅圖（色塊含代號與股票名稱）
- **個股明細** — 各股持倉、均成本、現價、損益金額、報酬率（顏色標記）
- **交易管理** — 在 Dashboard 直接新增、修改、刪除交易紀錄
- **股票管理** — 在 Dashboard 直接新增、修改、刪除股票主檔
- **更新股價** — 按鈕觸發 `fetch_prices.py`，即時顯示執行輸出

## 技術選型

| 層級 | 工具 |
|------|------|
| 資料庫 | PostgreSQL 17 |
| Python | psycopg2-binary、pandas |
| 股價來源 | yfinance（支援 .TW / .TWO） |
| Dashboard | Streamlit + Plotly |

## 專案結構

```
taiwan-portfolio/
├── db/
│   ├── schema.sql          # 資料表、Index、View 定義
│   └── sample_data.sql     # 測試用範例資料
├── scripts/
│   ├── db_ops.py           # 共用 CRUD 操作模組（Dashboard 與 CLI 共用）
│   ├── fetch_prices.py     # 抓取台股收盤價（自動嘗試 .TW / .TWO）
│   └── add_transaction.py  # CLI 新增買賣交易紀錄
├── app/
│   └── dashboard.py        # Streamlit Dashboard（含完整 CRUD）
├── requirements.txt
└── .env                    # DB 連線設定（不入版控）
```

## 架構說明

```
Dashboard (UI 層)  →  db_ops.py (操作執行層)  →  PostgreSQL
CLI scripts        →  db_ops.py
```

`db_ops.py` 為唯一的 DB 操作入口，Dashboard 表單與 CLI 腳本共用相同邏輯，確保行為一致。

## 快速開始

### 1. 安裝 PostgreSQL 17

至 [postgresql.org](https://www.postgresql.org/download/windows/) 下載 Windows installer。

### 2. 建立資料庫

```bash
createdb -U postgres taiwan_portfolio
psql -U postgres -d taiwan_portfolio -f db/schema.sql
psql -U postgres -d taiwan_portfolio -f db/sample_data.sql   # 選用
```

### 3. 設定環境變數

複製 `.env.example` 為 `.env` 並填入密碼：

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/taiwan_portfolio
```

### 4. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 5. 啟動 Dashboard

```bash
streamlit run app/dashboard.py
```

瀏覽器開啟 http://localhost:8501

在 Dashboard 即可完成所有操作：新增股票、新增交易、更新股價。

## CLI 操作（選用）

```bash
# 互動式輸入股票代號、日期、買/賣、股數、成交價
python scripts/add_transaction.py

# 單獨抓取收盤價（等同 Dashboard「更新股價」按鈕）
python scripts/fetch_prices.py
```

## PostgreSQL 學習對照

| SQL 功能 | 在本專案哪裡用到 |
|----------|----------------|
| Foreign Key | `transactions` → `stocks` |
| CHECK constraint | `trade_type IN ('BUY','SELL')` |
| CASE WHEN | 計算持股數、加權平均成本 |
| Subquery | 取最新收盤價 |
| NULLIF | 防止除以零 |
| CREATE INDEX | `daily_prices` 加速查詢 |
| CREATE VIEW | `portfolio_summary` 損益計算 |
| HAVING | 過濾已清倉股票 |
| INSERT ON CONFLICT | UPSERT 收盤價 |

## .gitignore 建議

```
.env
__pycache__/
*.pyc
```
