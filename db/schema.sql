-- ============================================================
-- 台股投資組合損益 Dashboard — 資料庫 Schema
-- ============================================================

-- 股票基本資料
CREATE TABLE IF NOT EXISTS stocks (
    ticker  VARCHAR(10) PRIMARY KEY,   -- '2330', '0050'
    name    VARCHAR(50) NOT NULL,
    sector  VARCHAR(50)
);

-- 交易紀錄（買/賣）
CREATE TABLE IF NOT EXISTS transactions (
    id          SERIAL PRIMARY KEY,
    ticker      VARCHAR(10) REFERENCES stocks(ticker),
    trade_date  DATE NOT NULL,
    trade_type  VARCHAR(4) NOT NULL CHECK (trade_type IN ('BUY', 'SELL')),
    shares      INTEGER NOT NULL CHECK (shares > 0),
    price       NUMERIC(10,2) NOT NULL,
    fee         NUMERIC(10,2) DEFAULT 0
);

-- 每日收盤價（由 fetch_prices.py 寫入）
CREATE TABLE IF NOT EXISTS daily_prices (
    ticker      VARCHAR(10) REFERENCES stocks(ticker),
    price_date  DATE NOT NULL,
    close_price NUMERIC(10,2) NOT NULL,
    PRIMARY KEY (ticker, price_date)
);

-- 加速歷史價格查詢
CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_date
    ON daily_prices(ticker, price_date DESC);

-- ============================================================
-- 損益計算 View
-- 學習重點：JOIN、CASE WHEN、Subquery、NULLIF、HAVING
-- ============================================================
CREATE OR REPLACE VIEW portfolio_summary AS
SELECT
    t.ticker,
    s.name,
    s.sector,
    SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares ELSE -t.shares END)  AS holding_shares,
    ROUND(
        SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares * t.price ELSE 0 END) /
        NULLIF(SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares ELSE 0 END), 0)
    , 2) AS avg_cost,
    dp.close_price AS current_price,
    -- 持倉市值
    SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares ELSE -t.shares END) * dp.close_price AS market_value,
    -- 總投入成本
    SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares * t.price ELSE 0 END) AS total_cost,
    -- 損益金額
    ROUND(
        SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares ELSE -t.shares END) * dp.close_price
        - SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares * t.price ELSE 0 END)
    , 0) AS pnl_amount,
    -- 報酬率 %
    ROUND(
        (dp.close_price - (
            SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares * t.price ELSE 0 END) /
            NULLIF(SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares ELSE 0 END), 0)
        )) /
        NULLIF(
            SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares * t.price ELSE 0 END) /
            NULLIF(SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares ELSE 0 END), 0)
        , 0) * 100
    , 2) AS return_pct,
    dp.price_date AS last_updated
FROM transactions t
JOIN stocks s ON t.ticker = s.ticker
LEFT JOIN daily_prices dp
    ON t.ticker = dp.ticker
    AND dp.price_date = (
        SELECT MAX(price_date) FROM daily_prices WHERE ticker = t.ticker
    )
GROUP BY t.ticker, s.name, s.sector, dp.close_price, dp.price_date
HAVING SUM(CASE WHEN t.trade_type = 'BUY' THEN t.shares ELSE -t.shares END) > 0;
