import streamlit as st

st.set_page_config(
    page_title="Ozon Электроника",
    page_icon="🔌",
    layout="wide",
)

pages = [
    st.Page("pages/1_📊_PnL.py",       title="P&L по месяцам",   icon="📊"),
    st.Page("pages/2_📦_Товары.py",    title="По товарам",        icon="📦"),
    st.Page("pages/3_💳_Транзакции.py", title="Транзакции",       icon="💳"),
]

pg = st.navigation(pages)
pg.run()
