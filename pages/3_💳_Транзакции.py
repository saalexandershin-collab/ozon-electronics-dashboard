"""Транзакции — Ozon Электроника."""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from src.ozon_api import get_finance_transactions

st.title("💳 Транзакции Ozon")

col1, col2 = st.columns(2)
with col1:
    date_from = st.date_input("С", value=date.today().replace(day=1))
with col2:
    date_to = st.date_input("По", value=date.today())

if date_from > date_to:
    st.error("Начало должно быть ≤ концу")
    st.stop()


@st.cache_data(ttl=1800, show_spinner="Загружаю транзакции…")
def load(df: date, dt: date) -> pd.DataFrame:
    return get_finance_transactions(df, dt)


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
    "accruals_for_sale", "sale_commission", "delivery_charge",
    "return_delivery_charge", "amount"
] if c in df.columns]

if show_cols:
    st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
else:
    st.dataframe(df, use_container_width=True, hide_index=True)
