"""Halaman 2: Alasan Pembatalan. Pertanyaan: apa alasan terbesar dan siapa yang melakukannya?"""
import plotly.graph_objects as go
import streamlit as st

import ui


def render(df):
    c = df[df["is_cancelled"]]
    batal = len(c)
    if batal == 0:
        st.info("Tidak ada order batal pada filter ini.")
        return
    by = (c.groupby(["cancel_reason", "cancel_actor", "is_preventable"])
           .agg(n=("order_id", "size"), est=("est_revenue_hilang", "sum")).reset_index().sort_values("n"))
    by["share"] = by["n"] / batal * 100
    by["label"] = by.apply(lambda r: f"{ui.id_num(r['n'])} ({ui.pct(r['share'])})", axis=1)

    prev = c[c["is_preventable"]]
    k1, k2, _ = st.columns([1, 1, 1.5])
    ui.kpi(k1, "Dapat dicegah penjual", ui.pct(len(prev) / batal * 100),
           f"{ui.id_num(len(prev))} order · {ui.rp_juta(prev['est_revenue_hilang'].sum())}", ui.GOOD)
    ui.kpi(k2, "Di luar kendali penjual", ui.pct((batal - len(prev)) / batal * 100),
           f"{ui.id_num(batal - len(prev))} order · pembeli dan sistem", ui.CYAN)
    with st.container():
        agg = by.groupby("cancel_reason").agg(n=("n", "sum")).reset_index()
        agg["actor"] = agg["cancel_reason"].map(by.sort_values("n").groupby("cancel_reason")["cancel_actor"].last())
        agg = agg.sort_values("n")
        _act = c.groupby("cancel_actor").size().reindex(["Pembeli", "Sistem", "Penjual"]).fillna(0)
        ui.legend({f"{n} {ui.pct(v / batal * 100)}": ui.ACTOR_COLORS[n] for n, v in _act.items()})
        ui.show(ui.hbar(list(agg["cancel_reason"]), list(agg["n"]),
                        [f"{ui.id_num(v)} ({ui.pct(v / batal * 100)})" for v in agg["n"]],
                        [ui.ACTOR_COLORS.get(a, ui.MUTED) for a in agg["actor"]], "Alasan pembatalan (warna = pelaku)", 470,
                        baca="Panjang batang = jumlah order batal untuk tiap alasan. Angka di kanan = jumlah order dan persennya dari seluruh pembatalan. Warna batang menunjukkan siapa yang membatalkan."))

    st.markdown("##### Telusuri satu alasan")
    reason = st.selectbox("Pilih alasan", by.sort_values("n", ascending=False)["cancel_reason"].unique(), key="alasan_pilih")
    r = c[c["cancel_reason"] == reason]
    a, b = st.columns(2)
    pay = r.groupby("payment_group").size().sort_values(ascending=False).reset_index(name="order")
    pay["porsi"] = (pay["order"] / len(r) * 100).map(ui.pct)
    prov = r.groupby("province_name").size().sort_values(ascending=False).head(5).reset_index(name="order")
    prov["porsi"] = (prov["order"] / len(r) * 100).map(ui.pct)
    a.markdown(f"**Menurut kelompok pembayaran** ({ui.id_num(len(r))} order)")
    a.dataframe(pay.rename(columns={"payment_group": "Pembayaran", "order": "Order", "porsi": "Porsi"}),
                hide_index=True, width="stretch")
    b.markdown("**5 provinsi teratas**")
    b.dataframe(prov.rename(columns={"province_name": "Provinsi", "order": "Order", "porsi": "Porsi"}),
                hide_index=True, width="stretch")

    top = by.sort_values("n", ascending=False).iloc[0]
    change = by[by["cancel_reason"].isin(["Ubah Pesanan", "Ubah Alamat", "Ubah Voucher"])]["share"].sum()
    unpaid = c[c["cancel_reason"] == "Belum Dibayar"]
    unpaid_share = len(unpaid) / batal * 100
    ui.insight(
        apa=f"Alasan terbesar <b>{top['cancel_reason']}</b> ({ui.pct(top['share'])}). Pembatalan akibat perubahan pesanan, alamat, "
            f"atau voucher berjumlah {ui.pct(change)}, dan <i>Belum Dibayar</i> {ui.pct(unpaid_share)}.",
        mengapa="Hipotesis: pembeli membatalkan untuk mengubah pesanan/alamat karena informasi varian atau alamat belum pasti saat "
                "checkout, dan pembayaran non-COD kedaluwarsa sebelum dibayar. Data hanya mencatat alasan, bukan motifnya.",
        dampak=f"Estimasi penjualan tak terealisasi {ui.rp_juta(c['est_revenue_hilang'].sum())}; porsi yang dapat dicegah penjual kecil "
               f"({ui.pct(len(c[c['is_preventable']]) / batal * 100)}).",
        rekomendasi="Tampilkan konfirmasi alamat dan varian sebelum pembayaran, kirim pengingat pembayaran sebelum batas waktu, "
                    "dan pertahankan respons cepat ke pembeli agar porsi yang dapat dicegah tetap rendah.")
