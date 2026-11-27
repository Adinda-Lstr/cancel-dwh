"""Halaman 3: Segmen. Pertanyaan: kelompok order mana yang paling rentan batal?"""
import plotly.graph_objects as go
import streamlit as st

import ui

JAWA = {"DKI JAKARTA", "JAWA BARAT", "JAWA TENGAH", "JAWA TIMUR", "DI YOGYAKARTA", "BANTEN"}


def _rate_table(df, by):
    g = df.groupby(by).agg(n=("order_id", "size"), batal=("is_cancelled", "sum")).reset_index()
    g["cr"] = g["batal"] / g["n"] * 100
    return g


def _bar(g, label, title, overall, top=12, height=380):
    g = g.sort_values("cr", ascending=False).head(top).sort_values("cr")
    text = [f"{ui.pct(r.cr)} · {ui.id_num(r.n)} order" for r in g.itertuples()]
    return ui.hbar(list(g[label]), list(g["cr"]), text, [ui.PRIMARY if c > overall else ui.MUTED for c in g["cr"]],
                   title, height, overall, f"Rata-rata {ui.pct(overall)}", "Cancel rate (%)", ui.BACA_RATE)


def render(df, cat_df):
    overall = df["is_cancelled"].mean() * 100
    tab_pay, tab_ship, tab_loc, tab_cat = st.tabs(["Pembayaran", "Pengiriman", "Wilayah", "Kategori produk"])

    # ------------------------------------------------------------ pembayaran
    with tab_pay:
        min_n = st.slider("Minimum order per metode (menyaring sampel kecil)", 20, 500, 100, 10, key="min_pay")
        g = _rate_table(df, "payment_name")
        g = g[g["n"] >= min_n]
        if g.empty:
            st.info("Tidak ada metode yang memenuhi minimum order.")
        else:
            ui.show(_bar(g, "payment_name", "Cancel rate per metode pembayaran", overall))
            hi, lo = g.loc[g["cr"].idxmax()], g.loc[g["cr"].idxmin()]
            c = df[df["is_cancelled"]]
            unpaid = c[c["cancel_reason"] == "Belum Dibayar"]
            cod_unpaid = int((unpaid["payment_group"] == "COD").sum())
            ui.insight(
                apa=f"<b>{hi['payment_name']}</b> tertinggi {ui.pct(hi['cr'])} ({ui.id_num(hi['n'])} order); <b>{lo['payment_name']}</b> "
                    f"terendah {ui.pct(lo['cr'])} ({ui.id_num(lo['n'])} order); rata-rata {ui.pct(overall)}.",
                mengapa=f"Hipotesis: {ui.id_num(len(unpaid))} order batal karena <i>Belum Dibayar</i> "
                        + ("dan seluruhnya pada metode non-COD, " if cod_unpaid == 0 else "")
                        + "yaitu pembayaran tidak diselesaikan sebelum batas waktu.",
                dampak=f"Order <i>Belum Dibayar</i> menyumbang estimasi {ui.rp_juta(unpaid['est_revenue_hilang'].sum())} penjualan tak terealisasi.",
                rekomendasi=f"Dorong metode dengan cancel rate rendah ({lo['payment_name']}) lewat promo/voucher khusus, dan kirim pengingat "
                            f"pembayaran untuk metode yang cancel rate-nya tinggi.")

    # ------------------------------------------------------------ pengiriman
    with tab_ship:
        a, b = st.columns(2)
        min_n = a.slider("Minimum order per layanan", 20, 500, 150, 10, key="min_ship")
        incl = b.checkbox("Sertakan kurir 'Tidak Tercatat'", value=False, key="incl_unrec")
        d = df if incl else df[df["courier"] != "Tidak Tercatat"]
        d = d.assign(layanan=d["courier"] + " · " + d["service_class"])
        g = _rate_table(d, "layanan")
        g = g[g["n"] >= min_n]
        if g.empty:
            st.info("Tidak ada layanan yang memenuhi minimum order.")
        else:
            ui.show(_bar(g, "layanan", "Cancel rate per kurir dan kelas layanan", overall))
            known = g[~g["layanan"].str.startswith("Tidak Tercatat")]
            if known.empty:
                known = g
            hi, lo = known.loc[known["cr"].idxmax()], known.loc[known["cr"].idxmin()]
            unrec = df[df["courier"] == "Tidak Tercatat"]
            unrec_cancel = unrec["is_cancelled"].mean() * 100 if len(unrec) else 0
            total_cancel = int(df["is_cancelled"].sum())
            w = df[df["status_name"].isin(["Batal", "Selesai"])].groupby("is_cancelled")["total_weight_gr"].mean() / 1000
            hi_rows = d[d["layanan"] == hi["layanan"]]
            ui.insight(
                apa=f"Cancel rate tertinggi <b>{hi['layanan']}</b> {ui.pct(hi['cr'])} ({ui.id_num(hi['n'])} order), terendah "
                    f"<b>{lo['layanan']}</b> {ui.pct(lo['cr'])}. Order batal rata-rata {ui.id_num(w.get(True, 0), 2)} kg vs "
                    f"{ui.id_num(w.get(False, 0), 2)} kg pada order selesai.",
                mengapa=f"Hipotesis: paket lebih berat/besar berongkos lebih mahal sehingga pembeli lebih sering membatalkan. "
                        f"{ui.id_num(len(unrec))} order tanpa kurir tercatat, {ui.pct(unrec_cancel, 0)} di antaranya batal "
                        f"({ui.pct(len(unrec) / max(total_cancel, 1) * 100, 0)} dari seluruh pembatalan). Kemungkinan dicatat "
                        f"sebelum kurir ditetapkan, jadi tidak dipakai menilai kinerja kurir.",
                dampak=f"{hi['layanan']} menyumbang {ui.id_num(int(hi['batal']))} pembatalan "
                       f"(estimasi {ui.rp_juta(hi_rows.loc[hi_rows['is_cancelled'], 'est_revenue_hilang'].sum())} tak terealisasi).",
                rekomendasi="Tinjau layanan dengan cancel rate tertinggi, tampilkan estimasi ongkir sebelum checkout, dan validasi "
                            "pencatatan kurir 'Tidak Tercatat' ke sumber data.")

    # ---------------------------------------------------------------- wilayah
    with tab_loc:
        min_n = st.slider("Minimum order per provinsi", 20, 1000, 200, 20, key="min_prov")
        g = _rate_table(df, "province_name")
        gf = g[g["n"] >= min_n]
        if gf.empty:
            st.info("Tidak ada provinsi yang memenuhi minimum order.")
        else:
            ui.show(_bar(gf, "province_name", "10 provinsi dengan cancel rate tertinggi", overall, top=10))
            jawa = df[df["province_name"].isin(JAWA)]
            luar = df[~df["province_name"].isin(JAWA) & (df["province_name"] != "Unknown")]
            top = gf.loc[gf["cr"].idxmax()]
            cj, cl = jawa["is_cancelled"].mean() * 100, luar["is_cancelled"].mean() * 100
            ui.insight(
                apa=f"Pulau Jawa {ui.pct(cj)} ({ui.id_num(len(jawa))} order) vs luar Jawa {ui.pct(cl)} ({ui.id_num(len(luar))} order). "
                    f"Provinsi tertinggi: <b>{top['province_name']}</b> {ui.pct(top['cr'])} ({ui.id_num(top['n'])} order).",
                mengapa="Hipotesis: jarak pengiriman, ongkir, dan estimasi tiba lebih panjang untuk wilayah di luar Jawa. "
                        "Data tidak memuat lama pengiriman, jadi hubungan ini belum teruji.",
                dampak=f"Order luar Jawa menyumbang {ui.id_num(int(luar['is_cancelled'].sum()))} pembatalan "
                       f"({ui.rp_juta(luar.loc[luar['is_cancelled'], 'est_revenue_hilang'].sum())} estimasi tak terealisasi).",
                rekomendasi="Pertimbangkan gratis ongkir bersyarat atau estimasi tiba yang jelas untuk provinsi dengan cancel rate tinggi, "
                            "lalu pantau apakah angkanya turun.")
        st.markdown("##### Telusuri satu provinsi")
        prov = st.selectbox("Pilih provinsi", g.sort_values("n", ascending=False)["province_name"], key="prov_pilih")
        cities = _rate_table(df[df["province_name"] == prov], "city_name").sort_values("n", ascending=False).head(15)
        cities["cr"] = cities["cr"].round(1)
        st.dataframe(ui.idf(cities.rename(columns={"city_name": "Kota/Kabupaten", "n": "Order", "batal": "Batal", "cr": "Cancel %"}), {"Cancel %": 1}),
                     hide_index=True, width="stretch")

    # --------------------------------------------------------------- kategori
    with tab_cat:
        st.caption("Dihitung dari fakta kedua (order × kategori). Order multi-kategori dialokasikan merata sehingga tidak terhitung ganda.")
        min_n = st.slider("Minimum order teralokasi per kategori", 50, 1000, 200, 50, key="min_cat")
        g = cat_df.groupby("category_name").agg(n=("allocated_orders", "sum"),
                                                 batal=("allocated_orders", lambda s: s[cat_df.loc[s.index, "is_cancelled"]].sum()),
                                                 est=("allocated_est_hilang", "sum")).reset_index()
        g["cr"] = g["batal"] / g["n"] * 100
        gf = g[g["n"] >= min_n]
        if gf.empty:
            st.info("Tidak ada kategori yang memenuhi minimum order.")
        else:
            overall_cat = g["batal"].sum() / g["n"].sum() * 100
            ui.show(_bar(gf, "category_name", "10 kategori dengan cancel rate tertinggi", overall_cat, top=10))
            hi, lo = gf.loc[gf["cr"].idxmax()], gf.loc[gf["cr"].idxmin()]
            ui.insight(
                apa=f"Kategori <b>{hi['category_name']}</b> tertinggi {ui.pct(hi['cr'])} (≈{ui.id_num(hi['n'])} order), "
                    f"<b>{lo['category_name']}</b> terendah {ui.pct(lo['cr'])}.",
                mengapa="Hipotesis: produk berukuran besar atau berongkos tinggi lebih sering dibatalkan setelah pembeli melihat total biaya. "
                        "Data tidak memuat nama produk, hanya kategori.",
                dampak=f"Estimasi penjualan tak terealisasi pada kategori ini ≈ {ui.rp_juta(hi['est'])}.",
                rekomendasi="Lengkapi deskripsi ukuran dan ongkir pada kategori dengan cancel rate tinggi, dan uji paket ongkir atau "
                            "bundling untuk menurunkannya.")
