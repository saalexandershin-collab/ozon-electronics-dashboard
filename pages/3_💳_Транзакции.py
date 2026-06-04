"""Транзакции — Ozon Электроника."""
import streamlit as st
import pandas as pd
import calendar
from datetime import date
from src.ozon_api import fetch_transactions

st.title("💳 Транзакции Ozon")

col1, col2 = st.columns(2)
with col1:
    date_from = st.date_input("С", value=date.today().replace(day=1))
with col2:
    date_to = st.date_input("По", value=date.today())

if date_from > date_to:
    st.error("Начало должно быть ≤ концу")
    st.stop()


def _fetch_range(d_from: date, d_to: date) -> list:
    """Fetch transactions month-by-month (Ozon limit: 1 month per request)."""
    all_ops = []
    cur = d_from
    while cur <= d_to:
        y, m = cur.year, cur.month
        month_end = min(date(y, m, calendar.monthrange(y, m)[1]), d_to)
        all_ops.extend(fetch_transactions(cur, month_end))
        cur = date(y + (m == 12), (m % 12) + 1, 1)
    return all_ops


@st.cache_data(ttl=1800, show_spinner="Загружаю транзакции…")
def load(df: date, dt: date) -> pd.DataFrame:
    ops = _fetch_range(df, dt)
    if not ops:
        return pd.DataFrame()
    rows = []
    for op in ops:
        rows.append({
            "operation_date":       op.get("operation_date", ""),
            "operation_type_name":  op.get("operation_type_name", ""),
            "posting_number":       op.get("posting_number", ""),
            "accruals_for_sale":    op.get("accruals_for_sale", 0),
            "sale_commission":      op.get("sale_commission", 0),
            "amount":               op.get("amount", 0),
        })
    return pd.DataFrame(rows)


df = load(date_from, date_to)

if df.empty:
    st.warning("Нет транзакций за период.")
    st.stop()

st.markdown(f"**Всего транзакций: {len(df):,}**")

# ── Фильтр по типу операции ───────────────────────────────────────────────────
if "operation_type_name" in df.columns:
    op_types = ["Все"] + sorted(df["operation_type_name"].dropna().unique().tolist())
    selected = st.selectbox("Тип операции", op_types)
    if selected != "Все":
        df = df[df["operation_type_name"] == selected]

# ── Итоговая сумма ─────────────────────────────────────────────────────────────
if "amount" in df.columns:
    total = pd.to_numeric(df["amount"], errors="coerce").sum()
    st.metric("Итого за период", f"{total:,.2f} ₽")

# ── Таблица ────────────────────────────────────────────────────────────────────
show_cols = [c for c in [
    "operation_date", "operation_type_name", "posting_number",
    "accruals_for_sale", "sale_commission", "amount"
] if c in df.columns]

st.dataframe(df[show_cols] if show_cols else df, use_container_width=True, hide_index=True)
