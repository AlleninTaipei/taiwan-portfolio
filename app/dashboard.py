"""
dashboard.py — 台股投資組合損益 Dashboard

執行方式：
    streamlit run app/dashboard.py
"""

import os
import sys
import subprocess
from datetime import date
from pathlib import Path

import psycopg2
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

# ── 匯入共用操作模組 ─────────────────────────────────────────────
_SCRIPTS = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from db_ops import (
    list_stocks, stock_exists, insert_stock, update_stock, delete_stock,
    list_transactions, insert_transaction, update_transaction, delete_transaction,
)

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/taiwan_portfolio")
_ROOT  = Path(__file__).parent.parent

st.set_page_config(page_title="台股損益 Dashboard", page_icon="📈", layout="wide")


# ── Cached loaders ──────────────────────────────────────────────

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


@st.cache_data(ttl=300)
def load_transactions() -> pd.DataFrame:
    return list_transactions()


@st.cache_data(ttl=300)
def load_stocks() -> pd.DataFrame:
    return list_stocks()


def _clear_cache():
    st.cache_data.clear()


# ── 側邊欄 ──────────────────────────────────────────────────────

st.sidebar.title("📈 台股投資組合")
page = st.sidebar.radio(
    "頁面",
    ["損益總覽", "個股明細", "交易管理", "股票管理", "更新股價"],
)

if st.sidebar.button("重新整理資料"):
    _clear_cache()
    st.rerun()


# ── 頁面 1：損益總覽 ────────────────────────────────────────────

if page == "損益總覽":
    st.title("損益總覽")

    try:
        df = load_portfolio()
    except Exception as e:
        st.error(f"無法連接資料庫：{e}")
        st.info("請確認 PostgreSQL 已啟動，且 .env 中的 DATABASE_URL 設定正確。")
        st.stop()

    if df.empty:
        st.warning("目前沒有持倉資料。請至「交易管理」新增交易，再至「更新股價」抓取收盤價。")
        st.stop()

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

    pie_df = df.copy()
    pie_df["label"] = pie_df["ticker"] + " " + pie_df["name"]
    fig = px.pie(
        pie_df,
        values="market_value",
        names="label",
        title="Portfolio Market Value",
        hole=0.4,
    )
    fig.update_traces(textinfo="label+percent")
    st.plotly_chart(fig, use_container_width=True)


# ── 頁面 2：個股明細 ────────────────────────────────────────────

elif page == "個股明細":
    st.title("個股明細")

    try:
        df = load_portfolio()
    except Exception as e:
        st.error(f"無法連接資料庫：{e}")
        st.stop()

    if df.empty:
        st.warning("目前沒有庫存。")
        st.stop()

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

    def color_return(val):
        try:
            color = "green" if float(val) >= 0 else "red"
            return f"color: {color}; font-weight: bold"
        except (TypeError, ValueError):
            return ""

    styled = (
        display.style
        .map(color_return, subset=["報酬率%", "損益(元)"])
        .format({
            "均成本":   "{:,.2f}",
            "現價":     "{:,.2f}",
            "市值":     "{:,.0f}",
            "損益(元)": "{:,.0f}",
            "報酬率%":  "{:.2f}%",
        }, na_rep="—")
    )

    st.dataframe(styled, use_container_width=True, hide_index=True)

    last_date = df["last_updated"].dropna().max()
    last_str = str(last_date) if last_date is not None else "尚無資料"
    st.caption(f"資料筆數：{len(df)} 支股票　｜　最後更新：{last_str}")


# ── 頁面 3：交易管理 ─────────────────────────────────────────────

elif page == "交易管理":
    st.title("交易管理")

    tab_view, tab_add, tab_edit, tab_del = st.tabs(["📋 查看", "➕ 新增", "✏️ 修改", "🗑️ 刪除"])

    # ── 查看 ──
    with tab_view:
        try:
            tx_df = load_transactions()
            if tx_df.empty:
                st.info("尚無交易紀錄。請至「➕ 新增」標籤新增交易。")
            else:
                show = tx_df.copy()
                show.columns = ["ID", "代號", "名稱", "日期", "類型", "股數", "價格", "費用"]
                st.dataframe(show, use_container_width=True, hide_index=True)
                st.caption(f"共 {len(tx_df)} 筆交易紀錄")
        except Exception as e:
            st.error(f"載入失敗：{e}")

    # ── 新增 ──
    with tab_add:
        st.info(
            "股票下拉選單的內容來自「股票管理」。\n\n"
            "若找不到想要的股票，請先前往「股票管理 → 新增」建立後再回來。"
        )
        try:
            stocks_df = load_stocks()
            stock_opts = (
                [f"{r.ticker}  {r.name}" for r in stocks_df.itertuples()]
                if not stocks_df.empty else []
            )
        except Exception:
            stock_opts = []

        if not stock_opts:
            st.warning("尚無股票資料，請先至「股票管理」新增股票。")
        else:
            col1, col2 = st.columns(2)
            selected  = col1.selectbox("股票", options=stock_opts, key="add_tx_stock")
            tx_ticker = selected.split()[0]
            tx_date   = col2.date_input("交易日期", value=date.today(), key="add_tx_date")

            col3, col4 = st.columns(2)
            tx_type   = col3.radio("類型", ["BUY", "SELL"], horizontal=True, key="add_tx_type")
            tx_shares = col4.number_input("股數", min_value=1, step=1, value=1000,
                                           key="add_tx_shares")

            st.divider()

            # ── 費用計算區 ───────────────────────────────────────
            col5, col6, col7 = st.columns(3)

            tx_price  = col5.number_input(
                "成交價（元）", min_value=0.01, step=0.01, value=100.0,
                format="%.2f", key="add_tx_price",
            )
            fee_pct = col6.number_input(
                "手續費（%）",
                min_value=0.0, max_value=0.1425, value=0.1425,
                step=0.0001, format="%.4f", key="add_tx_fee_pct",
                help="買賣皆收，上限 0.1425%",
            )
            if tx_type == "SELL":
                tax_pct = col7.number_input(
                    "證交稅（%）",
                    min_value=0.0, max_value=0.3, value=0.3,
                    step=0.001, format="%.3f", key="add_tx_tax_pct",
                    help="賣出時課徵，上限 0.3%",
                )
            else:
                col7.text_input("證交稅（%）", value="— 僅賣出適用",
                                 disabled=True, key="add_tx_tax_disabled")
                tax_pct = 0.0

            fee_amt  = int(tx_shares) * tx_price * fee_pct  / 100
            tax_amt  = int(tx_shares) * tx_price * tax_pct  / 100
            total_fee = fee_amt + tax_amt

            _, cost_col = st.columns([2, 1])
            cost_col.metric(
                "交易成本（元）",
                f"NT$ {total_fee:,.0f}",
                help=f"手續費 NT${fee_amt:,.0f}　＋　證交稅 NT${tax_amt:,.0f}",
            )

            st.divider()

            if st.button("新增交易", type="primary", key="btn_add_tx"):
                try:
                    new_id = insert_transaction(
                        tx_ticker, tx_date, tx_type,
                        int(tx_shares), tx_price, round(total_fee, 0),
                    )
                    st.success(
                        f"✓ 已新增交易 id={new_id}（"
                        f"{tx_date} {tx_type} {tx_ticker} "
                        f"{int(tx_shares)}股 @ {tx_price:.2f}元，"
                        f"交易成本 NT${total_fee:,.0f}元）"
                    )
                    _clear_cache()
                except Exception as e:
                    st.error(f"新增失敗：{e}")

    # ── 修改 ──
    with tab_edit:
        try:
            tx_df = load_transactions()
            if tx_df.empty:
                st.info("尚無交易紀錄可修改。")
            else:
                tx_opts = {
                    int(r.id): (
                        f"id={r.id}  {r.trade_date}  {r.trade_type}  "
                        f"{r.ticker}  {int(r.shares)}股  @{r.price}"
                    )
                    for r in tx_df.itertuples()
                }
                edit_id = st.selectbox(
                    "選擇要修改的交易",
                    options=list(tx_opts.keys()),
                    format_func=lambda x: tx_opts[x],
                    key="edit_tx_select",
                )

                row = tx_df[tx_df["id"] == edit_id].iloc[0]

                with st.form("form_edit_tx"):
                    col1, col2 = st.columns(2)
                    e_date = col1.date_input(
                        "交易日期",
                        value=pd.Timestamp(row["trade_date"]).date(),
                    )
                    e_type = col2.radio(
                        "類型", ["BUY", "SELL"],
                        index=0 if row["trade_type"] == "BUY" else 1,
                        horizontal=True,
                    )

                    col3, col4 = st.columns(2)
                    e_shares = col3.number_input("股數", min_value=1, step=1,
                                                  value=int(row["shares"]))
                    e_price  = col4.number_input("成交價（元）", min_value=0.01, step=0.01,
                                                  value=float(row["price"]), format="%.2f")

                    e_fee = st.number_input("手續費（元）", min_value=0.0, step=1.0,
                                             value=float(row["fee"]), format="%.0f")

                    if st.form_submit_button("儲存修改", type="primary"):
                        try:
                            update_transaction(
                                edit_id, e_date, e_type,
                                int(e_shares), e_price, e_fee,
                            )
                            st.success(f"✓ id={edit_id} 已更新")
                            _clear_cache()
                        except Exception as e:
                            st.error(f"修改失敗：{e}")
        except Exception as e:
            st.error(f"載入失敗：{e}")

    # ── 刪除 ──
    with tab_del:
        try:
            tx_df = load_transactions()
            if tx_df.empty:
                st.info("尚無交易紀錄可刪除。")
            else:
                tx_opts = {
                    int(r.id): (
                        f"id={r.id}  {r.trade_date}  {r.trade_type}  "
                        f"{r.ticker}  {int(r.shares)}股  @{r.price}"
                    )
                    for r in tx_df.itertuples()
                }
                del_id = st.selectbox(
                    "選擇要刪除的交易",
                    options=list(tx_opts.keys()),
                    format_func=lambda x: tx_opts[x],
                    key="del_tx_select",
                )

                row = tx_df[tx_df["id"] == del_id].iloc[0]
                st.warning(
                    f"確認刪除：id={del_id}　{row['trade_date']}　{row['trade_type']}　"
                    f"{row['ticker']}　{int(row['shares'])}股　"
                    f"@{row['price']}元　費用={int(row['fee'])}元"
                )
                if st.button("確認刪除", type="primary", key="btn_del_tx"):
                    try:
                        delete_transaction(int(del_id))
                        st.success(f"✓ id={del_id} 已刪除")
                        _clear_cache()
                        st.rerun()
                    except Exception as e:
                        st.error(f"刪除失敗：{e}")
        except Exception as e:
            st.error(f"載入失敗：{e}")


# ── 頁面 4：股票管理 ─────────────────────────────────────────────

elif page == "股票管理":
    st.title("股票管理")
    st.info(
        "股票管理是**交易管理的前置作業**。\n\n"
        "前往「交易管理 → 新增」時，股票下拉選單的內容來自這裡；"
        "若某支股票尚未在此建立，就無法為它新增交易紀錄。\n\n"
        "建議流程：**股票管理（新增）→ 交易管理（新增）→ 更新股價**"
    )

    tab_view, tab_add, tab_edit, tab_del = st.tabs(["📋 查看", "➕ 新增", "✏️ 修改", "🗑️ 刪除"])

    # ── 查看 ──
    with tab_view:
        try:
            stocks_df = load_stocks()
            if stocks_df.empty:
                st.info("尚無股票資料。請至「➕ 新增」標籤新增股票。")
            else:
                show = stocks_df.copy()
                show.columns = ["代號", "名稱", "產業", "類別"]
                st.dataframe(show, use_container_width=True, hide_index=True)
                st.caption(f"共 {len(stocks_df)} 支股票")
        except Exception as e:
            st.error(f"載入失敗：{e}")

    # ── 新增 ──
    with tab_add:
        with st.form("form_add_stock"):
            st.subheader("新增股票")
            col1, col2, col3, col4 = st.columns(4)
            s_ticker   = col1.text_input("股票代號（例如：2330）")
            s_name     = col2.text_input("股票名稱（例如：台積電）")
            s_sector   = col3.text_input("產業分類（可留空）")
            s_category = col4.selectbox("類別", ["股票", "ETF"])

            if st.form_submit_button("新增", type="primary"):
                s_ticker = s_ticker.strip().upper()
                s_name   = s_name.strip()
                if not s_ticker or not s_name:
                    st.error("股票代號與名稱為必填欄位")
                elif stock_exists(s_ticker):
                    st.error(f"股票 {s_ticker} 已存在")
                else:
                    try:
                        insert_stock(s_ticker, s_name, s_sector or None, s_category)
                        st.success(f"✓ 已新增 {s_ticker}  {s_name}")
                        _clear_cache()
                    except Exception as e:
                        st.error(f"新增失敗：{e}")

    # ── 修改 ──
    with tab_edit:
        try:
            stocks_df = load_stocks()
            if stocks_df.empty:
                st.info("尚無股票資料可修改。")
            else:
                stock_opts = {
                    r.ticker: f"{r.ticker}  {r.name}"
                    for r in stocks_df.itertuples()
                }
                edit_ticker = st.selectbox(
                    "選擇要修改的股票",
                    options=list(stock_opts.keys()),
                    format_func=lambda x: stock_opts[x],
                    key="edit_stock_select",
                )

                row = stocks_df[stocks_df["ticker"] == edit_ticker].iloc[0]

                with st.form("form_edit_stock"):
                    e_name     = st.text_input("股票名稱", value=row["name"])
                    e_sector   = st.text_input("產業分類", value=row["sector"] or "")
                    e_category = st.selectbox(
                        "類別", ["股票", "ETF"],
                        index=["股票", "ETF"].index(row["category"]),
                    )

                    if st.form_submit_button("儲存修改", type="primary"):
                        if not e_name.strip():
                            st.error("股票名稱不可為空")
                        else:
                            try:
                                update_stock(edit_ticker, e_name, e_sector or None, e_category)
                                st.success(f"✓ {edit_ticker} 已更新")
                                _clear_cache()
                            except Exception as e:
                                st.error(f"修改失敗：{e}")
        except Exception as e:
            st.error(f"載入失敗：{e}")

    # ── 刪除 ──
    with tab_del:
        try:
            stocks_df = load_stocks()
            if stocks_df.empty:
                st.info("尚無股票資料可刪除。")
            else:
                stock_opts = {
                    r.ticker: f"{r.ticker}  {r.name}"
                    for r in stocks_df.itertuples()
                }
                del_ticker = st.selectbox(
                    "選擇要刪除的股票",
                    options=list(stock_opts.keys()),
                    format_func=lambda x: stock_opts[x],
                    key="del_stock_select",
                )

                row = stocks_df[stocks_df["ticker"] == del_ticker].iloc[0]
                st.warning(
                    f"確認刪除：{del_ticker}  {row['name']}  "
                    f"{row['sector'] or '（無產業分類）'}\n\n"
                    "⚠️ 若有相關交易或股價資料，刪除可能因外鍵約束而失敗。"
                )
                if st.button("確認刪除", type="primary", key="btn_del_stock"):
                    try:
                        delete_stock(del_ticker)
                        st.success(f"✓ {del_ticker} 已刪除")
                        _clear_cache()
                        st.rerun()
                    except Exception as e:
                        st.error(f"刪除失敗（可能有相關交易資料）：{e}")
        except Exception as e:
            st.error(f"載入失敗：{e}")


# ── 頁面 5：更新股價 ─────────────────────────────────────────────

elif page == "更新股價":
    st.title("更新股價")
    st.info(
        "執行 `scripts/fetch_prices.py`，從 yfinance 抓取所有持股的最新收盤價並寫入資料庫。"
    )

    if st.button("🔄 開始更新股價", type="primary"):
        script_path = _ROOT / "scripts" / "fetch_prices.py"

        with st.spinner("正在抓取股價，請稍候…"):
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(_ROOT),
            )

        if result.returncode == 0:
            st.success("✓ 更新完成！")
        else:
            st.error(f"執行失敗（exit code {result.returncode}）")

        if result.stdout:
            st.text_area("執行輸出", result.stdout, height=300)

        if result.stderr:
            with st.expander("錯誤訊息"):
                st.text(result.stderr)

        _clear_cache()
