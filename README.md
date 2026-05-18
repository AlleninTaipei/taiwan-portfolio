# 台股投資組合損益 Dashboard

以 PostgreSQL + Python + Streamlit 建立的個人台股損益追蹤工具，同時作為學習 PostgreSQL 核心功能的實作專案。

## 功能

- **損益總覽** — 總投入成本、目前市值、損益金額、整體報酬率、投資組合圓餅圖（色塊含代號與股票名稱）
- **個股明細** — 投資組合、均成本、現價、損益金額、報酬率（顏色標記）
- **交易管理** — 在 Dashboard 直接新增、修改、刪除交易紀錄
- **股票管理** — 在 Dashboard 直接新增、修改、刪除股票主檔
- **更新股價** — 按鈕觸發 `fetch_prices.py`，即時顯示執行輸出

## 技術選型

| 層級 | 工具 |
|------|------|
| 資料庫 | PostgreSQL 14 |
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

### macOS（Homebrew）

#### 1. 安裝 PostgreSQL 14

```bash
brew install postgresql@14
brew services start postgresql@14   # 啟動並設定開機自動啟動
```

#### 2. 建立資料庫

```bash
createdb taiwan_portfolio
psql -d taiwan_portfolio -f db/schema.sql
psql -d taiwan_portfolio -f db/sample_data.sql   # 選用
```

#### 3. 設定環境變數

建立 `.env`：

```
DATABASE_URL=postgresql://你的使用者名稱@localhost:5432/taiwan_portfolio
```

> 查詢使用者名稱：`whoami`

#### 4. 安裝 Python 套件

```bash
pip3 install -r requirements.txt
```

#### 5. 啟動 Dashboard

```bash
python3 -m streamlit run app/dashboard.py
```

---

### Windows

#### 1. 安裝 PostgreSQL 14

至 [postgresql.org](https://www.postgresql.org/download/windows/) 下載 installer。

#### 2. 建立資料庫

```bash
createdb -U postgres taiwan_portfolio
psql -U postgres -d taiwan_portfolio -f db/schema.sql
psql -U postgres -d taiwan_portfolio -f db/sample_data.sql   # 選用
```

#### 3. 設定環境變數

建立 `.env`：

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/taiwan_portfolio
```

#### 4. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

#### 5. 啟動 Dashboard

```bash
python -m streamlit run app/dashboard.py
```

---

瀏覽器開啟 http://localhost:8501

在 Dashboard 即可完成所有操作：新增股票、新增交易、更新股價。

## CLI 操作（選用）

```bash
# 互動式輸入股票代號、日期、買/賣、股數、成交價
python scripts/add_transaction.py

# 單獨抓取收盤價（等同 Dashboard「更新股價」按鈕）
python scripts/fetch_prices.py
```

---

## PostgreSQL 基礎知識

### 資料庫實際存在哪裡？

`taiwan_portfolio` 不是一個資料夾或檔案，而是由 **PostgreSQL 服務**（背景執行的 process）統一管理的資料集合。

所有資料存放在 PostgreSQL 的 **data directory**，預設路徑：

| 平台 | 路徑 |
|------|------|
| macOS (Homebrew Intel) | `/usr/local/var/postgresql@14/` |
| macOS (Homebrew Apple Silicon) | `/opt/homebrew/var/postgresql@14/` |
| Windows | `C:\Program Files\PostgreSQL\14\data\` |

查詢實際路徑：

```bash
psql -d postgres -c "SHOW data_directory;"
```

查詢 `taiwan_portfolio` 的內部識別碼（OID）：

```bash
psql -d postgres -c "SELECT oid, datname FROM pg_database WHERE datname = 'taiwan_portfolio';"
```

> `SHOW` 與 `SELECT` 是 SQL 語法，不能直接在 Windows 終端機執行；
> 加上 `psql -U postgres -c "..."` 才是完整的執行方式。

`data\base\<OID>\` 下存放的是 PostgreSQL 自有格式的二進位檔案，**無法直接用文字編輯器讀取**，只能透過 psql 或 psycopg2 等方式存取。

### data directory 結構

```
data/
├── base/               # 每個資料庫一個子目錄（以 OID 命名）
│   ├── 1/              # template1（系統用）
│   ├── 16384/          # taiwan_portfolio（OID 示例）
│   │   ├── 16385       # stocks 資料表的 heap 檔
│   │   ├── 16390       # transactions 資料表
│   │   └── ...
├── global/             # 跨資料庫的系統目錄（pg_database 等）
├── pg_wal/             # Write-Ahead Log（WAL），確保資料不遺失
├── pg_hba.conf         # 連線驗證規則（允許哪些 IP / 帳號）
├── postgresql.conf     # 主設定檔（port、記憶體、log 等）
└── PG_VERSION          # PostgreSQL 版本號
```

### 連線字串解析

本專案使用的 `DATABASE_URL`：

**macOS（Homebrew，無密碼）**：
```
postgresql://你的使用者名稱@localhost:5432/taiwan_portfolio
```

**Windows**：
```
postgresql://postgres:PASSWORD@localhost:5432/taiwan_portfolio
             ────────  ────────  ─────────  ────  ─────────────
             使用者    密碼      主機       port  資料庫名稱
```

| 欄位 | 說明 |
|------|------|
| 使用者名稱 | macOS：`whoami` 的輸出；Windows：安裝時預設的 `postgres` |
| `localhost` | PostgreSQL 服務執行在本機 |
| `5432` | PostgreSQL 預設監聽 port |
| `taiwan_portfolio` | 本專案建立的資料庫 |

### PostgreSQL 服務管理

**macOS（Homebrew）**：

```bash
brew services start postgresql@14   # 啟動（並設定開機自動啟動）
brew services stop postgresql@14    # 停止
brew services list                  # 查看狀態
```

**Windows — PowerShell**（需以系統管理員身分執行）：

```powershell
Get-Service postgresql*          # 查看服務狀態
Start-Service postgresql-x64-14  # 啟動
Stop-Service  postgresql-x64-14  # 停止
```

**Windows — cmd.exe**（同樣需以系統管理員身分執行）：

```bat
sc query postgresql-x64-14       # 查看服務狀態
net start postgresql-x64-14      # 啟動
net stop  postgresql-x64-14      # 停止
```

> `Get-Service` 等指令是 PowerShell 專屬 cmdlet，無法在 cmd.exe 執行；
> `net start / net stop` 則兩者通用。
> 也可在「服務」管理員（services.msc）中以 GUI 操作 `postgresql-x64-14`。

### psql 常用指令

| 指令 | 說明 |
|------|------|
| `\l` | 列出所有資料庫 |
| `\c taiwan_portfolio` | 切換到此資料庫 |
| `\dt` | 列出所有資料表 |
| `\d stocks` | 查看 stocks 資料表結構 |
| `\dv` | 列出所有 View |
| `\di` | 列出所有 Index |
| `\q` | 離開 psql |

### 本專案的資料表關聯

```
stocks          transactions          daily_prices
──────────      ────────────────      ────────────────
ticker (PK) ←── ticker (FK)           ticker (FK) ──→ stocks
name            trade_date            price_date
sector          trade_type            close_price
                shares
                price                 PK: (ticker, price_date)
                fee

                        ↓ VIEW
                 portfolio_summary
                 ─────────────────────
                 holding_shares（CASE WHEN BUY/SELL）
                 avg_cost（加權平均）
                 current_price（子查詢取最新日期）
                 market_value、pnl_amount、return_pct
```

### PostgreSQL 學習對照

| SQL 功能 | 在本專案哪裡用到 |
|----------|----------------|
| Foreign Key | `transactions.ticker` → `stocks.ticker`；刪除股票若有交易紀錄會報錯（保護資料完整性） |
| CHECK constraint | `trade_type IN ('BUY','SELL')`；資料庫層擋住非法值 |
| CASE WHEN | `portfolio_summary` 中計算持股數（BUY 加、SELL 減）與加權平均成本 |
| Subquery | 取每支股票最新收盤價（`SELECT MAX(price_date)`） |
| NULLIF | `NULLIF(SUM(shares), 0)` 防止除以零導致例外 |
| CREATE INDEX | `daily_prices(ticker DESC, price_date DESC)` 加速最新價查詢 |
| CREATE VIEW | `portfolio_summary` 把複雜損益計算封裝成虛擬資料表 |
| HAVING | 過濾 `holding_shares = 0`（已清倉不顯示） |
| INSERT ON CONFLICT | `upsert_prices()` 中，同一天重複抓到資料時更新而不是報錯 |
| Transaction (commit) | `db_ops.py` 每個寫入操作結束後呼叫 `conn.commit()` |

### 為什麼用 View 而不是直接 SELECT？

`portfolio_summary` 是 **Virtual View**（非實體化），每次查詢時即時計算：

- 優點：資料永遠是最新的（基於 transactions + daily_prices 的即時計算）
- 代價：複雜查詢每次都重新執行；資料量大時可考慮 `MATERIALIZED VIEW` + 定期 `REFRESH`

本專案資料量小（個人持股），Virtual View 完全夠用。

---

## .gitignore 建議

```
.env
__pycache__/
*.pyc
```
