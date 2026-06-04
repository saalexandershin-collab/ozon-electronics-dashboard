"""Юнит-экономика по SKU — Ozon Электроника."""
import streamlit as st
import pandas as pd
import plotly.express as px
import calendar
from datetime import date

# fetch_transactions существует в исходной версии ozon_api.py (c самого первого коммита)
from src.ozon_api import fetch_transactions

st.title("📐 Юнит-экономика по SKU")

MONTHS_RU = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

# ── Classifier ────────────────────────────────────────────────────────────────

def _classify(op_name: str, svc_name: str) -> str:
    c = (op_name + " " + svc_name).lower()
    if any(x in c for x in ("logistic", "доставка", "кросс")):
        return "логистика"
    if any(x in c for x in ("advert", "реклам", "promo")):
        return "реклама"
    return "прочее"


def build_unit_economics(date_from: date, date_to: date) -> pd.DataFrame:
    rows = []
    for op in fetch_transactions(date_from, date_to):
        rev = op.get("accruals_for_sale", 0)
        if rev == 0:
            continue
        com   = op.get("sale_commission", 0)
        items = op.get("items", [])
        if not items:
            continue

        op_name = op.get("operation_type_name", "")
        log = ads = oth = 0.0
        for svc in op.get("services", []):
            cat   = _classify(op_name, svc.get("name", ""))
            price = svc.get("price", 0)
            if cat == "логистика":
                log += price
            elif cat == "реклама":
                ads += price
            else:
                oth += price

        total_qty = sum(item.get("quantity", 1) or 1 for item in items) or len(items)
        for item in items:
            qty = item.get("quantity", 1) or 1
            w   = qty / total_qty
            r_  = rev * w
            c_  = com * w
            l_  = log * w
            a_  = (ads + oth) * w
            rows.append({
                "sku":          item.get("sku"),
                "артикул":      item.get("offer_id", ""),
                "товар":        item.get("name", ""),
                "кол_во":       qty,
                "выручка":      r_,
                "комиссия":     c_,
                "логистика":    l_,
                "реклама_проч": a_,
                "выплата":      r_ + c_ + l_ + a_,
            })

    if not rows:
        return pd.DataFrame()

    df  = pd.DataFrame(rows)
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


# ── Фильтры ───────────────────────────────────────────────────────────────────
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
    return build_unit_economics(df, dt)


df = load(date_from, date_to)

if df.empty:
    st.warning("Нет данных за период.")
    st.stop()

# ── KPI ───────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Уникальных SKU",  f"{df['sku'].nunique():,}")
k2.metric("Продано штук",    f"{int(df['кол_во'].sum()):,}")
k3.metric("Выручка итого",   f"{df['выручка'].sum():,.0f} ₽")
k4.metric("Выплата итого",   f"{df['выплата'].sum():,.0f} ₽")

st.markdown("---")

# ── Топ-20 по выплате ─────────────────────────────────────────────────────────
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

# ── Таблица ───────────────────────────────────────────────────────────────────
st.markdown("### 📋 Все SKU — юнит-экономика")

display = df[[
    "sku", "артикул", "товар",
    "кол_во", "ср_цена",
    "выручка", "комиссия", "логистика", "реклама_проч", "выплата",
]].copy()

for c in ["ср_цена", "выручка", "комиссия", "логистика", "реклама_проч", "выплата"]:
    display[c] = display[c].apply(lambda v: f"{v:,.0f} ₽")
display["кол_во"] = display["кол_во"].apply(lambda v: f"{int(v):,}")

display.columns = [
    "SKU", "Артикул", "Товар",
    "Кол-во", "Ср. цена",
    "Выручка", "Комиссия", "Логистика", "Реклама/прочее", "Выплата",
]
st.dataframe(display, use_container_width=True, hide_index=True)

# ── Структура на 1 шт. (топ SKU) ─────────────────────────────────────────────
st.markdown("### 💧 Структура выплаты на 1 шт. (лучший SKU по выручке)")
top1 = df.iloc[0]
qty  = top1["кол_во"] or 1
unit = {
    "Выручка":        top1["выручка"]      / qty,
    "Комиссия":       top1["комиссия"]     / qty,
    "Логистика":      top1["логистика"]    / qty,
    "Реклама/прочее": top1["реклама_проч"] / qty,
    "Выплата":        top1["выплата"]      / qty,
}
fig2 = px.bar(
    x=list(unit.keys()), y=list(unit.values()),
    color=list(unit.keys()),
    color_discrete_map={
        "Выручка":        "#005BFF",
        "Комиссия":       "#FF4444",
        "Логистика":      "#FF9F00",
        "Реклама/прочее": "#A855F7",
        "Выплата":        "#00B341",
    },
    title=f"{top1['товар'][:70]}",
    labels={"x": "", "y": "₽ / шт."},
)
fig2.update_layout(showlegend=False, height=350, margin=dict(t=50, b=30))
st.plotly_chart(fig2, use_container_width=True)
