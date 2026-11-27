"""Halaman 4: Event & Kalender. Perbandingan DESKRIPTIF periode event vs hari biasa (bukan bukti sebab-akibat)."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui


def _rate(g):
    return pd.Series({"order": len(g), "batal": int(g["is_cancelled"].sum()),
                      "cr": g["is_cancelled"].mean() * 100,
                      "cod": (g["payment_group"] == "COD").mean() * 100})


def render(df):
    st.caption("Perbandingan ini bersifat deskriptif: event hanya konteks waktu dan bukan bukti penyebab pembatalan.")
    known = df[df["event_category"] != "Unknown"]
    if known.empty:
        st.info("Tidak ada order dengan tanggal diketahui pada filter ini.")
        return
    ev = known.groupby("event_category").apply(_rate, include_groups=False).reset_index().sort_values("cr")
    base = known[known["event_category"] == "Biasa"]
    base_cr = base["is_cancelled"].mean() * 100 if len(base) else None
    ev["kecil"] = ev["order"] < ui.MIN_SAMPLE
    ev["label"] = ev.apply(lambda r: f"{ui.pct(r['cr'])} · {ui.id_num(r['order'])} order" + (" ⚠" if r["kecil"] else ""), axis=1)

    left, right = st.columns([1.15, 1])
    with left:
        ui.show(ui.hbar(list(ev["event_category"]), list(ev["cr"]), list(ev["label"]),
                        [ui.MUTED if k else (ui.PRIMARY if c > (base_cr or 0) else ui.CYAN) for k, c in zip(ev["kecil"], ev["cr"])],
                        "Cancel rate per kategori event", 340, base_cr,
                        f"Hari biasa {ui.pct(base_cr)}" if base_cr is not None else "", "Cancel rate (%)",
                        baca="Panjang batang = cancel rate pada kategori event itu. Angka \"... order\" di kanan = jumlah order kategori itu. Garis putus-putus = cancel rate hari biasa; koral = di atasnya. Abu-abu dan tanda ⚠ = sampel kecil (kurang dari 150 order), jadi belum cukup kuat untuk disimpulkan."))
    with right:
        names = (known[known["event_category"] != "Biasa"].groupby(["event_category", "event_name"])
                 .apply(_rate, include_groups=False).reset_index().sort_values("order", ascending=False))
        names["Event"] = names.apply(lambda r: (r["event_name"] if r["event_category"].split()[-1] in r["event_name"]
                                                else f'{r["event_category"]} {r["event_name"]}') + (" ⚠" if r["order"] < ui.MIN_SAMPLE else ""), axis=1)
        show = ui.idf(names[["Event", "order", "cr", "cod"]].rename(columns={"order": "Order", "cr": "Cancel %", "cod": "COD %"}),
                      {"Cancel %": 1, "COD %": 1})
        st.markdown("**Rincian per event**")
        st.dataframe(show, hide_index=True, width="stretch", height=340)

    dated = df[df["order_date"].notna()]
    rows = []
    for faktor, col in [("Akhir pekan", "is_weekend"), ("Hari libur", "is_holiday"), ("Periode gajian", "is_payday")]:
        for val, g in dated.groupby(col):
            rows.append({"faktor": faktor, "nilai": "Ya" if val else "Tidak", "cr": g["is_cancelled"].mean() * 100, "n": len(g)})
    if dated.empty:
        st.info("Tidak ada order bertanggal untuk analisis faktor kalender.")
        return
    part = dated[dated["day_part"] != "Unknown"]
    order_part = ["Dini Hari", "Pagi", "Siang", "Sore", "Malam"]
    for val, g in part.groupby("day_part"):
        rows.append({"faktor": "Waktu pesan", "nilai": val, "cr": g["is_cancelled"].mean() * 100, "n": len(g)})
    cal = pd.DataFrame(rows)
    cal["label"] = cal.apply(lambda r: f"{ui.pct(r['cr'])}<br>{ui.id_num(r['n'])} order", axis=1)
    with st.expander("Faktor kalender lainnya: akhir pekan, hari libur, gajian, dan jam pesan"):
        cal3, calw = cal[cal["faktor"] != "Waktu pesan"], cal[cal["faktor"] == "Waktu pesan"]
        ymax = max(cal["cr"].max() * 1.45, 5)
        with st.container():
            fig = px.bar(cal3, x="nilai", y="cr", facet_col="faktor", text="label", color_discrete_sequence=[ui.CYAN],
                         category_orders={"nilai": ["Tidak", "Ya"]})
            fig.update_xaxes(matches=None, title=None)
            fig.update_yaxes(title=None, range=[0, ymax], ticksuffix="%")
            fig.update_yaxes(title="Cancel rate", col=1)
            fig.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
            fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
            fig.update_layout(title="Faktor kalender (order dengan waktu pesan diketahui)",
                              meta="Tiap panel membandingkan cancel rate saat kondisinya Ya dan Tidak. Hari libur = libur nasional dan cuti bersama; "
                                   "periode gajian = tanggal 25 sampai 3. Angka di atas batang = cancel rate dan jumlah order kelompok itu.")
            ui.show(fig, 380)
        with st.container():
            fw = px.bar(calw, x="nilai", y="cr", text="label", color_discrete_sequence=[ui.CYAN], category_orders={"nilai": order_part})
            fw.update_xaxes(title=None, tickangle=0, tickfont_size=11)
            fw.update_yaxes(title=None, range=[0, ymax], ticksuffix="%")
            fw.update_traces(textposition="outside", cliponaxis=False, textfont_size=11)
            fw.update_layout(title="Waktu pesan",
                             meta="Cancel rate menurut waktu pesan dibuat. Angka di atas batang = cancel rate dan jumlah order pada waktu itu.")
            ui.show(fw, 380)

    leb = ev[ev["event_category"] == "Libur Lebaran"]
    ram = ev[ev["event_category"] == "Ramadan"]
    hol = cal[(cal["faktor"] == "Hari libur")].set_index("nilai")["cr"]
    dini = cal[(cal["faktor"] == "Waktu pesan") & (cal["nilai"] == "Dini Hari")]
    if len(leb) and base_cr is not None:
        apa = (f"Cancel rate libur Lebaran {ui.pct(leb['cr'].iloc[0])} ({ui.id_num(leb['order'].iloc[0])} order) dan Ramadan "
               f"{ui.pct(ram['cr'].iloc[0]) if len(ram) else '-'} dibanding hari biasa {ui.pct(base_cr)}.")
    else:
        apa = "Pilih periode yang mencakup Ramadan atau Lebaran untuk melihat perbandingannya."
    extra = f" Hari libur {ui.pct(hol.get('Ya', 0))} vs hari lain {ui.pct(hol.get('Tidak', 0))}." if "Ya" in hol else ""
    ui.insight(
        apa=apa + extra,
        mengapa="Hipotesis: pada periode libur panjang pengiriman melambat dan pembeli lebih sering mengubah pesanan, sehingga "
                "pembatalan naik. Pola ini baru indikasi awal karena sampel kecil dan komposisi pembayaran berbeda.",
        dampak="Pembatalan di periode ramai membuat stok dan kapasitas pengemasan terpakai untuk order yang tidak selesai.",
        rekomendasi="Siapkan stok dan kurir lebih awal sebelum Lebaran, pantau cancel rate harian saat event, dan jangan menyimpulkan "
                    "pengaruh event sebelum ada data beberapa periode lagi.")
    st.markdown('<p class="note">Catatan data: 12.12 Harbolnas 2024 dan 7.7 2025 tidak punya order bertanggal karena waktu pesanan '
                'file Desember 2024 dan Juli 2025 kosong, sehingga dua kampanye itu tidak dapat dianalisis.</p>', unsafe_allow_html=True)
