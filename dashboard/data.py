"""Akses data: dashboard HANYA membaca schema mart (user dashboard_user, hak baca saja)."""
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()


@st.cache_resource
def get_engine():
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("DASHBOARD_DB_USER", "dashboard_user"),
        password=os.environ["DWH_ANALYST_PASSWORD"],
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=600, show_spinner=False)
def query(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn)


def load_orders() -> pd.DataFrame:
    df = query("SELECT * FROM mart.v_order_flat")
    df["order_month"] = pd.to_datetime(df["order_month"])
    return df


def load_categories() -> pd.DataFrame:
    df = query("SELECT * FROM mart.v_order_category_flat")
    df["order_month"] = pd.to_datetime(df["order_month"])
    return df


def filter_frame(df, f, has_event=True, has_province=True):
    """Menerapkan filter sidebar. Nama kolom yang sama dipakai di v_order_flat dan v_order_category_flat."""
    m = (df["order_month"] >= f["start"]) & (df["order_month"] <= f["end"])
    if f["payment"]:
        m &= df["payment_group"].isin(f["payment"])
    if f["event"] and has_event:
        m &= df["event_category"].isin(f["event"])
    if f["province"] and has_province:
        m &= df["province_name"].isin(f["province"])
    return df[m]
