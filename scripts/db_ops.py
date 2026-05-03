"""
db_ops.py — 共用資料庫 CRUD 操作模組
Dashboard 與 CLI scripts 共同匯入此模組執行 DB 操作
"""

import os
from contextlib import contextmanager
from datetime import date

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/taiwan_portfolio")


@contextmanager
def _conn():
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
    finally:
        conn.close()


# ── Stocks ──────────────────────────────────────────────────────

def list_stocks() -> pd.DataFrame:
    with _conn() as conn:
        return pd.read_sql("SELECT ticker, name, sector FROM stocks ORDER BY ticker", conn)


def stock_exists(ticker: str) -> bool:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM stocks WHERE ticker = %s", (ticker.upper(),))
            return cur.fetchone() is not None


def insert_stock(ticker: str, name: str, sector: str | None = None) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO stocks (ticker, name, sector) VALUES (%s, %s, %s)",
                (ticker.upper(), name.strip(), sector.strip() if sector else None),
            )
        conn.commit()


def update_stock(ticker: str, name: str, sector: str | None = None) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE stocks SET name = %s, sector = %s WHERE ticker = %s",
                (name.strip(), sector.strip() if sector else None, ticker.upper()),
            )
        conn.commit()


def delete_stock(ticker: str) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM stocks WHERE ticker = %s", (ticker.upper(),))
        conn.commit()


# ── Transactions ────────────────────────────────────────────────

def list_transactions() -> pd.DataFrame:
    with _conn() as conn:
        return pd.read_sql(
            """
            SELECT t.id, t.ticker, s.name, t.trade_date, t.trade_type,
                   t.shares, t.price, t.fee
            FROM transactions t
            JOIN stocks s ON s.ticker = t.ticker
            ORDER BY t.trade_date DESC, t.id DESC
            """,
            conn,
        )


def insert_transaction(
    ticker: str,
    trade_date: date,
    trade_type: str,
    shares: int,
    price: float,
    fee: float = 0.0,
) -> int:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (ticker, trade_date, trade_type, shares, price, fee)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (ticker.upper(), trade_date, trade_type.upper(), int(shares), float(price), float(fee)),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
    return new_id


def update_transaction(
    tx_id: int,
    trade_date: date,
    trade_type: str,
    shares: int,
    price: float,
    fee: float,
) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE transactions
                SET trade_date = %s, trade_type = %s, shares = %s,
                    price = %s, fee = %s
                WHERE id = %s
                """,
                (trade_date, trade_type.upper(), int(shares), float(price), float(fee), int(tx_id)),
            )
        conn.commit()


def delete_transaction(tx_id: int) -> None:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM transactions WHERE id = %s", (int(tx_id),))
        conn.commit()


# ── Prices ──────────────────────────────────────────────────────

def get_all_tickers() -> list[str]:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ticker FROM stocks ORDER BY ticker")
            return [row[0] for row in cur.fetchall()]


def upsert_prices(ticker: str, df: pd.DataFrame) -> int:
    """Upsert closing prices; returns the number of rows written."""
    with _conn() as conn:
        with conn.cursor() as cur:
            for price_date, row in df.iterrows():
                close = (
                    float(row["Close"].iloc[0])
                    if hasattr(row["Close"], "iloc")
                    else float(row["Close"])
                )
                cur.execute(
                    """
                    INSERT INTO daily_prices (ticker, price_date, close_price)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (ticker, price_date) DO UPDATE
                        SET close_price = EXCLUDED.close_price
                    """,
                    (ticker, price_date.date(), close),
                )
        conn.commit()
    return len(df)
