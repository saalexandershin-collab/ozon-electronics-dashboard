"""Юнит-экономика по SKU — Ozon Электроника."""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import calendar
from src.ozon_api import fetch_transactions, _classify_service


def get_unit_economics(date_from: date, date_to: date) -> pd.DataFrame:
    """Per-SKU unit economics: qty, avg price, revenue, commission, logistics, ads+other, payout."""
    ops = fetch_transactions(date_from, date_to)
    rows = []
    for op in ops:
        revenue = op.get("accruals_for_sale", 0)
        if revenue == 0:
            continue
        commission = op.get("sale_commission", 0)
        items = op.get("items", [])
        if not items:
            continue
        op_name = op.get("operation_type_name", "")
        svc_logistics = svc_ads = svc_other = 0.0
        for svc in op.get("services", []):
            cat = _classify_service(op_name, svc.get("name", ""))
            price = svc.get("price", 0)
            if cat == "логистика":
                svc_logistics += price
            elif cat == "реклама":
                svc_ads += price
            else:
                svc_other += price
        total_qty = sum(item.get("quantity", 1) or 1 for item in items) or len(items)
        for item in items:
            qty = item.get("quantity", 1) or 1
            w = qty / total_qty
            item_rev = revenue    * w
            item_com = commission * w
            item_log = svc_logistics * w
            item_ads = (svc_ads + svc_other) * w
            rows.append({
                "sku":          item.get("sku"),
                "артикул":      item.get("offer_id", ""),
                "товар":        item.get("name", ""),
                "кол_во":       qty,
                "выручка":      item_rev,
                "комиссия":     item_com,
                "логистика":    item_log,
                "реклама_проч": item_ads,
                "выплата":      item_rev + item_com + item_log + item_ads,
            })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    agg = df.groupby(["sku", "артикул", "товар"]).agg(
        кол_во       =("кол_во",       "sum"),
        выручка      =("выручка",      "sum"),
        комиссия     =("комиссия",     "sum"),
        логистика    =("логистика",    "sum"),
        реклама_проч =("реклама_проч", "sum"),
        выплата      =("выплата",      "sum"),
    ).reset_index()
    agg["ср_цена"] = (agg["выручка"] / agg["кол_во"].replace(0, 1)).round(0)
    return agg.sort_values("выручка", ascending=False).reset_index(drop=True)

st.title("📐 Юнит-экономика по SKU")

MONTHS_RU = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

col1, col2, col3 = st.columns(3)
with col1:
    year = st.selectbox("Год", [2026, 2025])
with col2:
    m_from = st.selectbox("С", range(1, 13), format_func=lambda m: MONTHS_RU[m - 1])
with col3:
    m_to = st.selectbox("По", range(1, 13),
                        index=min(date.today().month - 1, 11),
                        format_func=lambda m: MONTHS_RU[m - 1])

date_from = date(year, m_from, 1)
date_to   = min(date(year, m_to, calendar.monthrange(year, m_to)[1]), date.today())


@st.cache_data(ttl=3600, show_spinner="Загружаю юнит-экономику…")
def load(df: date, dt: date) -> pd.DataFrame:
    return get_unit_economics(df, dt)


df = load(date_from, date_to)

if df.empty:
    st.warning("Нет данных за период.")
    st.stop()

# ── KPI ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Уникальных SKU",   f"{df['sku'].nunique():,}")
k2.metric("Продано штук",     f"{int(df['кол_во'].sum()):,}")
k3.metric("Выручка итого",    f"{df['выручка'].sum():,.0f} ₽")
k4.metric("Выплата итого",    f"{df['выплата'].sum():,.0f} ₽")

st.markdown("---")

# ── Топ-20 по выручке (бар) ───────────────────────────────────────────────
top20 = df.head(20).copy()
top20["товар_short"] = top20["товар"].str[:50]

fig = px.bar(
    top20, x="выплата", y="товар_short", orientation="h",
    title="Топ-20 SKU по выплате",
    color="выплата", color_continuous_scale=["#CCE5FF", "#005BFF"],
    labels={"выплата": "Выплата, ₽", "товар_short": ""},
)
fig.update_layout(height=600, yaxis={"categoryorder": "total ascending"},
                  coloraxis_showscale=False)
st.plotly_chart(fig, use_container_width=True)

# ── Таблица ───────────────────────────────────────────────────────────────
st.markdown("### 📋 Все SKU — юнит-экономика")

display = df[[
    "sku", "артикул", "товар",
    "кол_во", "ср_цена",
    "выручка", "комиссия", "логистика", "реклама_проч", "выплата",
]].copy()

money_cols = ["ср_цена", "выручка", "комиссия", "логистика", "реклама_проч", "выплата"]
for c in money_cols:
    display[c] = display[c].apply(lambda v: f"{v:,.0f} ₽")

display["кол_во"] = display["кол_во"].apply(lambda v: f"{int(v):,}")

display.columns = [
    "SKU", "Артикул", "Товар",
    "Кол-во", "Ср. цена",
    "Выручка", "Комиссия", "Логистика", "Реклама/прочее", "Выплата",
]
st.dataframe(display, use_container_width=True, hide_index=True)

# ── Waterfall: структура на единицу (топ-1 SKU) ──────────────────────────
st.markdown("### 💧 Структура выплаты на 1 шт. (лучший SKU)")

top1 = df.iloc[0]
qty  = top1["кол_во"] or 1
unit = {
    "Выручка":         top1["выручка"]      / qty,
    "Комиссия":        top1["комиссия"]     / qty,
    "Логистика":       top1["логистика"]    / qty,
    "Реклама/прочее":  top1["реклама_проч"] / qty,
    "Выплата":         top1["выплата"]      / qty,
}

wf = px.bar(
    x=list(unit.keys()),
    y=list(unit.values()),
    color=list(unit.keys()),
    color_discrete_map={
        "Выручка":        "#005BFF",
        "Комиссия":       "#FF4444",
        "Логистика":      "#FF9F00",
        "Реклама/прочее": "#A855F7",
        "Выплата":        "#00B341",
    },
    title=f"{top1['товар'][:60]}…",
    labels={"x": "", "y": "₽ / шт."},
)
wf.update_layout(showlegend=False, height=350, margin=dict(t=50, b=30))
st.plotly_chart(wf, use_container_width=True)
