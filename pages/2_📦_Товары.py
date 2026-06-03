"""P&L по товарам — Ozon Электроника."""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from src.ozon_api import get_top_products_by_revenue

st.title("📦 Выручка по товарам")

MONTHS_RU = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

col1, col2, col3 = st.columns(3)
with col1:
    year = st.selectbox("Год", [2026, 2025])
with col2:
    m_from = st.selectbox("С", range(1, 13), format_func=lambda m: MONTHS_RU[m-1])
with col3:
    m_to = st.selectbox("По", range(1, 13),
                        index=min(date.today().month - 1, 11),
                        format_func=lambda m: MONTHS_RU[m-1])

import calendar
date_from = date(year, m_from, 1)
date_to   = min(date(year, m_to, calendar.monthrange(year, m_to)[1]), date.today())


@st.cache_data(ttl=3600, show_spinner="Загружаю данные по товарам…")
def load(df: date, dt: date) -> pd.DataFrame:
    return get_top_products_by_revenue(df, dt)


df = load(date_from, date_to)

if df.empty:
    st.warning("Нет данных за период.")
    st.stop()

df = df.sort_values("выручка", ascending=False)

# KPI
k1, k2, k3 = st.columns(3)
k1.metric("Уникальных SKU", f"{df['sku'].nunique():,}")
k2.metric("Выручка итого", f"{df['выручка'].sum():,.0f} ₽")
k3.metric("Нетто итого", f"{df['нетто'].sum():,.0f} ₽")

st.markdown("---")

# Топ-20 по выручке
top20 = df.head(20).copy()
top20["товар_short"] = top20["товар"].str[:55]

fig = px.bar(
    top20, x="выручка", y="товар_short", orientation="h",
    title="Топ-20 товаров по выручке",
    color="выручка", color_continuous_scale=["#CCE5FF", "#005BFF"],
    labels={"выручка": "Выручка, ₽", "товар_short": ""},
)
fig.update_layout(height=600, yaxis={"categoryorder": "total ascending"},
                  coloraxis_showscale=False)
st.plotly_chart(fig, use_container_width=True)

# Таблица
st.markdown("### 📋 Все товары")
display = df[["товар", "выручка", "комиссия", "нетто"]].copy()
for c in ["выручка", "комиссия", "нетто"]:
    display[c] = display[c].apply(lambda v: f"{v:,.0f} ₽")
display.columns = ["Товар", "Выручка", "Комиссия Ozon", "Нетто"]
st.dataframe(display, use_container_width=True, hide_index=True)
