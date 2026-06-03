# 🔌 Ozon Электроника — P&L Дашборд

P&L дашборд для кабинета Ozon Электроника: выручка, комиссии, логистика по месяцам и товарам.

## Стек

Streamlit + Ozon Seller API + Plotly

## Быстрый старт (локально)

```bash
git clone https://github.com/YOUR_REPO/ozon-electronics-dashboard.git
cd ozon-electronics-dashboard
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Вставьте Client ID и API Key в secrets.toml
streamlit run app.py
```

## Деплой на Streamlit Cloud

1. Залейте репозиторий на GitHub
2. Зайдите на [share.streamlit.io](https://share.streamlit.io)
3. Подключите репозиторий, главный файл — `app.py`
4. В разделе **Secrets** вставьте:

```toml
[ozon]
client_id = "ваш_client_id"
api_key   = "ваш_api_key"
```
