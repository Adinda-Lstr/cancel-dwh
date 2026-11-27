"""Dashboard BI: Analisis Alasan dan Pola Pembatalan Order Toko Shopee.
Jalankan dari folder proyek:  streamlit run dashboard/app.py
Sumber data: schema mart pada PostgreSQL (hak baca saja)."""
from pathlib import Path

import pandas as pd
import streamlit as st

import data
import ui
from views import alasan, event, ringkasan, segmen, validasi

st.set_page_config(page_title="Pembatalan Order Shopee", page_icon=":material/inventory_2:", layout="wide")
ui.style()

try:
    orders = data.load_orders()
    cats = data.load_categories()
except Exception as exc:  # database mati / .env salah
    st.error("Tidak bisa membaca data mart. Pastikan Docker menyala dan file .env sudah diisi.")
    st.caption(f"Detail teknis: {type(exc).__name__}")
    st.stop()


st.logo(str(Path(__file__).parent / "assets" / "logo.svg"), size="large")


def _pg(title, icon, path, default=False):
    return st.Page(lambda: None, title=title, icon=icon, url_path=path, default=default)


nav = st.navigation({
    "Analisis": [_pg("Ringkasan", ":material/space_dashboard:", "ringkasan", True),
                 _pg("Alasan Pembatalan", ":material/contact_support:", "alasan"),
                 _pg("Segmen", ":material/donut_small:", "segmen"),
                 _pg("Event & Kalender", ":material/event:", "event")],
    "Kualitas data": [_pg("Validasi & Lineage", ":material/verified:", "validasi")]})
page = nav.title

with st.sidebar:
    st.divider()
    st.markdown("**Filter** (kosong = semua)")
    months = [pd.Timestamp(m) for m in sorted(orders["order_month"].unique())]
    start, end = st.select_slider("Periode", options=months, value=(months[0], months[-1]),
                                  format_func=ui.bulan)
    payment = st.multiselect("Kelompok pembayaran", sorted(orders["payment_group"].unique()), placeholder="Semua")
    event_cat = st.multiselect("Kategori event", sorted(orders["event_category"].unique()), placeholder="Semua")
    province = st.multiselect("Provinsi", sorted(orders["province_name"].unique()), placeholder="Semua")

GENERIC = {"Ringkasan": "Seberapa besar masalah pembatalan?", "Alasan Pembatalan": "Apa alasan terbesar pembatalan?",
           "Segmen": "Kelompok mana yang paling rentan batal?", "Event & Kalender": "Apakah ada pola waktu?",
           "Validasi & Lineage": "Apakah angkanya bisa dipercaya?"}


def headline(page, d, d_ev):
    """Judul halaman berisi temuan utama dari data yang sedang difilter (Knaflic, 2015)."""
    try:
        if d.empty or page == "Validasi & Lineage":
            return GENERIC[page]
        c = d[d["is_cancelled"]]
        if page == "Ringkasan":
            return (f"{ui.pct(d['is_cancelled'].mean() * 100)} order dibatalkan, "
                    f"{ui.pct((c['cancel_actor'] == 'Pembeli').mean() * 100)} di antaranya oleh pembeli")
        if page == "Alasan Pembatalan":
            top = c["cancel_reason"].value_counts(normalize=True)
            return f"Alasan terbesar: {top.index[0]} ({ui.pct(top.iloc[0] * 100)} dari pembatalan)"
        if page == "Segmen":
            g = d.groupby("payment_name")["is_cancelled"].agg(["mean", "size"])
            g = g[g["size"] >= 100].sort_values("mean")
            return (f"{g.index[-1]} paling rentan batal: {ui.pct(g['mean'].iloc[-1] * 100)} "
                    f"vs rata-rata {ui.pct(d['is_cancelled'].mean() * 100)}")
        k = d_ev[d_ev["event_category"] != "Unknown"].groupby("event_category")["is_cancelled"].agg(["mean", "size"])
        base = k.loc["Biasa", "mean"] * 100
        k = k[(k["size"] >= ui.MIN_SAMPLE) & (k.index != "Biasa")].sort_values("mean")
        return f"Cancel rate tertinggi saat {k.index[-1]}: {ui.pct(k['mean'].iloc[-1] * 100)} vs hari biasa {ui.pct(base)}"
    except Exception:
        return GENERIC[page]


f = {"start": start, "end": end, "payment": payment, "event": event_cat, "province": province}
df = data.filter_frame(orders, f)
df_all_events = data.filter_frame(orders, {**f, "event": []})  # halaman event membandingkan semua kategori
cat_df = data.filter_frame(cats, f)

st.title(headline(page, df, df_all_events))
st.caption(f"Analisis alasan dan pola pembatalan order · Periode {ui.bulan(start)} – {ui.bulan(end)} · {ui.id_num(len(df))} order terpilih dari {ui.id_num(len(orders))}")

if df.empty and page != "Validasi & Lineage":
    st.warning("Tidak ada order yang cocok dengan filter. Longgarkan filter di sidebar.")
    st.stop()

if page == "Ringkasan":
    ringkasan.render(df)
elif page == "Alasan Pembatalan":
    alasan.render(df)
elif page == "Segmen":
    segmen.render(df, cat_df)
elif page == "Event & Kalender":
    event.render(df_all_events)
else:
    validasi.render(orders)
