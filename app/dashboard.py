"""
dashboard.py — 台股投資組合損益 Dashboard

執行方式：
    streamlit run app/dashboard.py
"""

import os
import psycopg2
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/taiwan_portfolio")

st.set_page_config(page_title="台股損益 Dashboard", page_icon="📈", layout="wide")


@st.cache_data(ttl=300)
def load_portfolio() -> pd.DataFrame:
    conn = psycopg2.connect(DB_URL)
    df = pd.read_sql(
        """
        SELECT ticker, name, sector, holding_shares, avg_cost,
               current_price, market_value, total_cost, pnl_amount,
               return_pct, last_updated
        FROM portfolio_summary
        ORDER BY market_value DESC NULLS LAST
        """,
        conn,
    )
    conn.close()
    return df


def format_pct(val):
    color = "color: green" if val >= 0 else "color: red"
    return color


# ── 側邊欄 ──────────────────────────────────────────────────
st.sidebar.title("📈 台股投資組合")
page = st.sidebar.radio("頁面", ["損益總覽", "個股明細"])

if st.sidebar.button("重新整理資料"):
    st.cache_data.clear()
    st.rerun()

# ── 載入資料 ────────────────────────────────────────────────
try:
    df = load_portfolio()
except Exception as e:
    st.error(f"無法連接資料庫：{e}")
    st.info("請確認 PostgreSQL 已啟動，且 .env 中的 DATABASE_URL 設定正確。")
    st.stop()

if df.empty:
    st.warning("目前沒有持倉資料。請執行 `scripts/add_transaction.py` 新增交易，再執行 `scripts/fetch_prices.py` 抓取收盤價。")
    st.stop()

# ── 頁面 1：損益總覽 ────────────────────────────────────────
if page == "損益總覽":
    st.title("損益總覽")

    total_cost   = df["total_cost"].sum()
    market_value = df["market_value"].sum()
    pnl          = df["pnl_amount"].sum()
    return_pct   = (pnl / total_cost * 100) if total_cost else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("總投入成本",  f"${total_cost:,.0f}")
    col2.metric("目前市值",    f"${market_value:,.0f}")
    col3.metric("損益金額",    f"${pnl:,.0f}", delta=f"{pnl:,.0f}")
    col4.metric("整體報酬率",  f"{return_pct:.2f}%", delta=f"{return_pct:.2f}%")

    st.divider()

    # 圓餅圖：各股市值佔比（標籤用代號避免字型問題，hover 顯示中文名稱）
    pie_df = df.copy()
    pie_df["label"] = pie_df["ticker"] + " " + pie_df["name"]
    fig = px.pie(
        pie_df,
        values="market_value",
        names="ticker",
        hover_data={"label": True, "market_value": True, "ticker": False},
        title="Portfolio Market Value",
        hole=0.4,
    )
    fig.update_traces(textinfo="label+percent")
    st.plotly_chart(fig, use_container_width=True)

    # 文字補充說明
    name_map = df.set_index("ticker")["name"].to_dict()
    st.caption("　".join([f"{k}＝{v}" for k, v in name_map.items()]))

# ── 頁面 2：個股明細 ────────────────────────────────────────
elif page == "個股明細":
    st.title("個股明細")

    display = df[[
        "ticker", "name", "sector", "holding_shares",
        "avg_cost", "current_price", "market_value",
        "pnl_amount", "return_pct", "last_updated"
    ]].copy()

    display.columns = [
        "代號", "名稱", "產業", "持股",
        "均成本", "現價", "市值",
        "損益(元)", "報酬率%", "更新日期"
    ]

    # 報酬率顏色標記（空值不套用顏色）
    def color_return(val):
        try:
            color = "green" if float(val) >= 0 else "red"
            return f"color: {color}; font-weight: bold"
        except (TypeError, ValueError):
            return ""

    styled = (
        display.style
        .applymap(color_return, subset=["報酬率%", "損益(元)"])
        .format({
            "均成本":   "{:,.2f}",
            "現價":     "{:,.2f}",
            "市值":     "{:,.0f}",
            "損益(元)": "{:,.0f}",
            "報酬率%":  "{:.2f}%",
        })
    )

    st.dataframe(styled, use_container_width=True, hide_index=True)

    last_date = df['last_updated'].dropna().max()
    last_str = str(last_date) if last_date is not None else "尚無資料"
    st.caption(f"資料筆數：{len(df)} 支股票　｜　最後更新：{last_str}")
