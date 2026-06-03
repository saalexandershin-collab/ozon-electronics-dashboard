"""Ozon Seller API client — Electronics cabinet."""
import requests
import streamlit as st
from datetime import date
import pandas as pd
from collections import defaultdict


def _headers() -> dict:
    try:
        client_id = st.secrets["ozon"]["client_id"]
        api_key   = st.secrets["ozon"]["api_key"]
    except Exception:
        import os
        client_id = os.getenv("OZON_CLIENT_ID", "")
        api_key   = os.getenv("OZON_API_KEY", "")
    return {
        "Client-Id": str(client_id),
        "Api-Key":   api_key,
        "Content-Type": "application/json",
    }


BASE = "https://api-seller.ozon.ru"


def fetch_transactions(date_from: date, date_to: date) -> list[dict]:
    """Fetch all finance transactions for a period (handles pagination)."""
    all_ops = []
    page = 1
    while True:
        r = requests.post(
            f"{BASE}/v3/finance/transaction/list",
            json={
                "filter": {
                    "date": {
                        "from": f"{date_from}T00:00:00Z",
                        "to":   f"{date_to}T23:59:59Z",
                    },
                    "transaction_type": "all",
                },
                "page":      page,
                "page_size": 100,
            },
            headers=_headers(), timeout=30,
        )
        r.raise_for_status()
        result = r.json().get("result", {})
        ops        = result.get("operations", [])
        page_count = result.get("page_count", 1)
        all_ops.extend(ops)
        if page >= page_count or not ops:
            break
        page += 1
    return all_ops


def _classify_service(op_type_name: str, svc_name: str) -> str:
    """Map operation/service name to P&L category."""
    c = (op_type_name + " " + svc_name).lower()
    if "acquiring" in svc_name.lower() or "эквайринг" in c:
        return "эквайринг"
    if any(x in c for x in ("storage", "хранение", "склад", "размещение")):
        return "хранение"
    if any(x in c for x in ("return", "возврат", "невыкуп", "отмен")):
        return "возвраты"
    if any(x in c for x in ("logistic", "доставка", "кросс")):
        return "логистика"
    if any(x in c for x in ("subscribe", "подписка", "premium", "отзыв")):
        return "подписки"
    if any(x in c for x in ("penalty", "штраф", "превышение", "нерекоменд")):
        return "штрафы"
    if any(x in c for x in ("advert", "реклам", "promo")):
        return "реклама"
    return "прочее"


def build_pnl(date_from: date, date_to: date) -> dict:
    """Return dict with P&L breakdown for the period."""
    ops = fetch_transactions(date_from, date_to)
    d: dict[str, float] = defaultdict(float)
    d["выручка"]  = sum(op.get("accruals_for_sale", 0) for op in ops)
    d["комиссия"] = sum(op.get("sale_commission", 0) for op in ops)
    d["нетто"]    = sum(op.get("amount", 0) for op in ops)
    d["ops_count"] = len(ops)
    for op in ops:
        op_name = op.get("operation_type_name", "")
        for svc in op.get("services", []):
            cat = _classify_service(op_name, svc.get("name", ""))
            d[cat] += svc.get("price", 0)
    return dict(d)


def get_pnl_monthly(year: int, months: list[int]) -> pd.DataFrame:
    """Return P&L DataFrame grouped by month."""
    import calendar
    rows = []
    for m in months:
        last_day = calendar.monthrange(year, m)[1]
        d_from = date(year, m, 1)
        d_to   = min(date(year, m, last_day), date.today())
        pnl = build_pnl(d_from, d_to)
        pnl["месяц"] = m
        pnl["год"]   = year
        rows.append(pnl)
    return pd.DataFrame(rows).fillna(0)


def get_products(limit: int = 200) -> pd.DataFrame:
    """Return list of products in the cabinet."""
    r = requests.post(
        f"{BASE}/v3/product/list",
        json={"filter": {}, "last_id": "", "limit": limit},
        headers=_headers(), timeout=15,
    )
    r.raise_for_status()
    items = r.json().get("result", {}).get("items", [])
    return pd.DataFrame(items) if items else pd.DataFrame()


def get_top_products_by_revenue(date_from: date, date_to: date) -> pd.DataFrame:
    """Get revenue breakdown by product from transactions."""
    ops = fetch_transactions(date_from, date_to)
    rows = []
    for op in ops:
        revenue = op.get("accruals_for_sale", 0)
        if revenue == 0:
            continue
        commission = op.get("sale_commission", 0)
        for item in op.get("items", []):
            rows.append({
                "sku":      item.get("sku"),
                "товар":    item.get("name", ""),
                "выручка":  revenue,
                "комиссия": commission,
                "нетто":    op.get("amount", 0),
            })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.groupby(["sku", "товар"])[["выручка", "комиссия", "нетто"]].sum().reset_index()
