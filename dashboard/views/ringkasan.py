"""Halaman 1: Ringkasan. Pertanyaan: seberapa besar masalah pembatalan dan bagaimana trennya?"""
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import ui


def render(df):
    n, batal = len(df), int(df["is_cancelled"].sum())
    cr = batal / n * 100
    est = df["est_revenue_hilang"].sum()
    cancelled = df[df["is_cancelled"]]
    prev = int(cancelled["is_preventable"].sum())
    prev_share = prev / batal * 100 if batal else 0

    cols = st.columns(5)
    ui.kpi(cols[0], "Total order", ui.id_num(n), "order pada periode terpilih", ui.CYAN)
    ui.kpi(cols[1], "Order batal", ui.id_num(batal), "berstatus Batal", ui.PRIMARY)
    ui.kpi(cols[2], "Cancel rate", ui.pct(cr), "batal ÷ seluruh order", ui.PRIMARY, ring=cr)
    ui.kpi(cols[3], "Est. revenue hilang", f"Rp{ui.id_num(est / 1e6, 1)}", "Estimasi, bukan kerugian aktual", ui.BLUE, unit="jt")
    ui.kpi(cols[4], "Dapat dicegah", ui.pct(prev_share), f"oleh penjual · {ui.id_num(prev)} dari {ui.id_num(batal)} batal", ui.GOOD, ring=prev_share)

    monthly = df.groupby("order_month").agg(orders=("order_id", "size"), batal=("is_cancelled", "sum")).reset_index()
    monthly["cr"] = monthly["batal"] / monthly["orders"] * 100
    monthly["label"] = monthly["order_month"].map(ui.bulan)  # sumbu x kategori agar nama bulan berbahasa Indonesia

    left, right = st.columns([2.2, 1])
    with left:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=.12, row_heights=[.42, .58],
                            subplot_titles=("Volume order per bulan", "Cancel rate per bulan"))
        fig.add_bar(x=monthly["label"], y=monthly["orders"], marker_color=ui.MUTED, showlegend=False, row=1, col=1)
        fig.add_scatter(x=monthly["label"], y=monthly["cr"], mode="lines+markers", line=dict(color=ui.LIME, width=3),
                        showlegend=False, row=2, col=1)
        fig.add_hline(y=cr, line_dash="dash", line_color=ui.TEXT, opacity=.6, row=2, col=1,
                      annotation_text=f"Rata-rata {ui.pct(cr)}", annotation_position="top right")
        fig.update_yaxes(rangemode="tozero", row=2, col=1, ticksuffix="%")
        fig.update_xaxes(tickangle=-45, tickvals=list(monthly["label"].iloc[::2]))
        for t in fig.layout.annotations[:2]:
            t.update(x=0, xanchor="left", font=dict(size=13, color=ui.TEXT))
        fig.update_layout(title="Tren bulanan: volume order (atas) dan cancel rate (bawah)",
                          meta="Panel atas = jumlah order tiap bulan. Panel bawah = cancel rate tiap bulan, yaitu persen order yang dibatalkan. "
                               "Garis putus-putus = rata-rata seluruh periode.")
        ui.show(fig, 430)
    with right:
        actor = cancelled.groupby("cancel_actor").size().reindex(["Pembeli", "Sistem", "Penjual"]).fillna(0)[::-1]
        fig = ui.hbar(list(actor.index), list(actor.values / max(batal, 1) * 100),
                      [ui.pct(v / max(batal, 1) * 100) for v in actor.values],
                      [ui.ACTOR_COLORS[a] for a in actor.index], "Siapa yang membatalkan?", 430,
                      baca="Panjang batang = persen pembatalan yang dilakukan tiap pelaku. Ketiganya berjumlah 100%.")
        fig.update_layout(margin=dict(r=60))
        fig.update_xaxes(range=[0, 100], ticksuffix="%")
        ui.show(fig, 430)

    big = monthly[monthly["orders"] >= 100]
    if big.empty:  # filter sangat sempit: pakai semua bulan agar tetap bisa tampil
        big = monthly
    hi, lo = big.loc[big["cr"].idxmax()], big.loc[big["cr"].idxmin()]
    top = cancelled.groupby("cancel_reason").size().sort_values(ascending=False)
    top_name, top_share = (top.index[0], top.iloc[0] / batal * 100) if batal else ("-", 0)
    buyer = (cancelled["cancel_actor"] == "Pembeli").mean() * 100 if batal else 0
    ui.insight(
        apa=f"{ui.id_num(batal)} dari {ui.id_num(n)} order batal (<b>{ui.pct(cr)}</b>). Tertinggi {ui.bulan(hi['order_month'])} "
            f"({ui.pct(hi['cr'])}), terendah {ui.bulan(lo['order_month'])} ({ui.pct(lo['cr'])}).",
        mengapa=f"Hipotesis dari pola data: {ui.pct(buyer)} pembatalan dilakukan pembeli dan alasan terbanyak adalah "
                f"<i>{top_name}</i> ({ui.pct(top_share)}). Data tidak membuktikan sebab-akibat.",
        dampak=f"Estimasi penjualan bruto tak terealisasi {ui.rp_juta(est)} (dihitung dari rata-rata order Selesai bulan yang sama).",
        rekomendasi=f"Hanya {ui.pct(prev_share)} pembatalan yang dapat dicegah langsung oleh penjual, jadi prioritaskan "
                    f"perbaikan alur pesanan (lihat halaman Alasan Pembatalan dan Segmen).")
    missing = int(df["is_time_missing"].sum())
    st.markdown(f'<p class="note">Catatan data: {ui.id_num(missing)} order ({ui.pct(missing / n * 100)}) tidak punya waktu pesanan. '
                f'Order itu tetap masuk analisis bulanan, tetapi tidak masuk analisis harian dan per jam.</p>',
                unsafe_allow_html=True)
