"""P&L по месяцам — Ozon Электроника."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
from src.ozon_api import get_pnl_monthly

st.title("📊 P&L по месяцам — Ozon Электроника")

MONTHS_RU = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

# ── Фильтры ───────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 3])
with col1:
    year = st.selectbox("Год", [2026, 2025], index=0)
with col2:
    default_months = list(range(1, date.today().month + 1)) if year == date.today().year else list(range(1, 13))
    selected = st.multiselect(
        "Месяцы",
        options=list(range(1, 13)),
        default=default_months,
        format_func=lambda m: MONTHS_RU[m - 1],
    )

if not selected:
    st.info("Выберите хотя бы один месяц")
    st.stop()

# ── Загрузка ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Загружаю данные из Ozon API…")
def load(yr: int, months: tuple) -> pd.DataFrame:
    return get_pnl_monthly(yr, list(months))

with st.spinner("Загружаю…"):
    df = load(year, tuple(sorted(selected)))

if df.empty:
    st.warning("Нет данных. Проверьте API-ключи в `.streamlit/secrets.toml`")
    st.stop()

df["месяц_название"] = df["месяц"].apply(lambda m: MONTHS_RU[m - 1])

# ── KPI ───────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("💰 Выручка",       f"{df['выручка'].sum():,.0f} ₽")
k2.metric("📤 Нетто (выплата)", f"{df['нетто'].sum():,.0f} ₽")
k3.metric("📉 Комиссия Ozon",  f"{abs(df['комиссия'].sum()):,.0f} ₽")

comm_pct = abs(df['комиссия'].sum()) / df['выручка'].sum() * 100 if df['выручка'].sum() else 0
k4.metric("% комиссии",       f"{comm_pct:.1f}%")

netto_pct = df['нетто'].sum() / df['выручка'].sum() * 100 if df['выручка'].sum() else 0
k5.metric("% нетто/выручка",  f"{netto_pct:.1f}%")

st.markdown("---")

# ── Таблица P&L ───────────────────────────────────────────────────────────────
st.markdown("### 📋 P&L по месяцам")

pnl_rows = [
    ("Выручка (начисления)",     "выручка",    False),
    ("  − Комиссия Ozon",        "комиссия",   True),
    ("  − Логистика",            "логистика",  True),
    ("  − Возвраты/отмены",      "возвраты",   True),
    ("  − Хранение",             "хранение",   True),
    ("  − Эквайринг",            "эквайринг",  True),
    ("  − Подписки Ozon",        "подписки",   True),
    ("  − Штрафы",               "штрафы",     True),
    ("  − Прочее",               "прочее",     True),
    ("НЕТТО (выплата)",          "нетто",      False),
]

months_sorted = sorted(df["месяц"].unique())
table_data = {"Статья": [r[0] for r in pnl_rows]}

for m in months_sorted:
    row_m = df[df["месяц"] == m].iloc[0]
    col_name = MONTHS_RU[m - 1]
    table_data[col_name] = []
    for label, col, is_cost in pnl_rows:
        val = row_m.get(col, 0)
        if is_cost:
            val = abs(val) * -1  # show negatives as costs
        table_data[col_name].append(val)

# Add total column
table_data["ИТОГО"] = []
for label, col, is_cost in pnl_rows:
    val = df[col].sum() if col in df.columns else 0
    if is_cost:
        val = abs(val) * -1
    table_data["ИТОГО"].append(val)

tbl = pd.DataFrame(table_data)

# Format numbers
def fmt(val):
    if isinstance(val, (int, float)):
        if val == 0:
            return "—"
        return f"{val:,.0f} ₽"
    return val

num_cols = [c for c in tbl.columns if c != "Статья"]
tbl_display = tbl.copy()
for c in num_cols:
    tbl_display[c] = tbl_display[c].apply(fmt)

st.dataframe(tbl_display, use_container_width=True, hide_index=True)

# ── График: выручка vs нетто ──────────────────────────────────────────────────
st.markdown("### 📈 Динамика выручки и выплат")

fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["месяц_название"], y=df["выручка"],
    name="Выручка", marker_color="#005BFF", opacity=0.85,
))
fig.add_trace(go.Bar(
    x=df["месяц_название"], y=df["нетто"],
    name="Нетто (выплата)", marker_color="#00B341", opacity=0.85,
))
fig.add_trace(go.Scatter(
    x=df["месяц_название"],
    y=df["комиссия"].abs(),
    name="Комиссия", mode="lines+markers",
    line=dict(color="#FF4444", width=2), marker=dict(size=6),
))
fig.update_layout(
    barmode="group", height=400,
    xaxis_title="Месяц", yaxis_title="₽",
    legend=dict(orientation="h", y=1.1),
    margin=dict(t=30, b=40),
)
st.plotly_chart(fig, use_container_width=True)

# ── Структура расходов ────────────────────────────────────────────────────────
st.markdown("### 🥧 Структура расходов Ozon (итого)")

expense_cats = [
    ("Комиссия Ozon",    "комиссия"),
    ("Эквайринг",        "эквайринг"),
    ("Подписки",         "подписки"),
    ("Логистика",        "логистика"),
    ("Возвраты/отмены",  "возвраты"),
    ("Хранение",         "хранение"),
    ("Штрафы",           "штрафы"),
    ("Прочее",           "прочее"),
]

labels  = [x[0] for x in expense_cats]
values  = [abs(df[x[1]].sum()) if x[1] in df.columns else 0 for x in expense_cats]
colors  = ["#005BFF", "#FF9F00", "#A855F7", "#00B341", "#FF4444", "#0EA5E9", "#F43F5E", "#94A3B8"]

fig2 = go.Figure(go.Pie(
    labels=labels, values=values, hole=0.45,
    marker_colors=colors,
    textinfo="label+percent",
))
fig2.update_layout(height=380, margin=dict(t=10, b=10, l=10, r=10))
st.plotly_chart(fig2, use_container_width=True)
