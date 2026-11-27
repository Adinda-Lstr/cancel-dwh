"""Halaman 5: Validasi & Lineage. Bukti bahwa angka dashboard dapat ditelusuri ke sumber."""
import pandas as pd
import streamlit as st

import data
import ui

LINEAGE = """
digraph G {
  rankdir=LR; bgcolor="transparent";
  node [shape=box, style="rounded,filled", fillcolor="#F1F5F9", fontcolor="#111827", fontname="Helvetica", fontsize=11, color="#94A3B8"];
  edge [fontname="Helvetica", fontsize=10, color="#7C93B2", fontcolor="#5B6475"];
  csv  [label="CSV mentah\\nall_months_clean.csv\\n(24 file bulanan)"];
  stg  [label="stg.stg_order_raw\\nStaging (salinan apa adanya)"];
  ref  [label="ref\\nkamus status, alasan,\\nkurir, bayar, event, libur", fillcolor="#FEF3C7"];
  dw   [label="dw\\nfact_order · fact_order_category\\nfact_daily_cancel_snapshot\\n+ 9 dimensi"];
  mart [label="mart\\n13 view KPI"];
  dash [label="Dashboard\\nStreamlit", fillcolor="#E0E7FF"];
  etl  [label="etl\\netl_batch · etl_log · etl_reject\\n(audit trail)", fillcolor="#DCFCE7"];
  csv -> stg [label="Extract"];
  stg -> dw  [label="Transform + Load"];
  ref -> dw  [label="pemetaan"];
  dw -> mart; mart -> dash;
  stg -> etl [style=dashed]; dw -> etl [style=dashed];
}
"""


def _num(text):
    try:
        return float(str(text).replace(",", ""))
    except ValueError:
        return float("nan")


def render(orders):
    n, batal = len(orders), int(orders["is_cancelled"].sum())
    revenue, est = orders["total_pembayaran"].sum(), orders["est_revenue_hilang"].sum()
    mart = data.query("SELECT sum(total_orders) o, sum(cancelled_orders) b, sum(realized_revenue) r, "
                      "sum(est_revenue_hilang) e FROM mart.v_kpi_monthly").iloc[0]
    val = data.query("SELECT * FROM mart.v_validation_latest")

    def ref(layer, name):
        row = val[(val["lapisan"] == layer) & (val["pemeriksaan"] == name)]
        return _num(row["acuan_csv"].iloc[0]) if len(row) else float("nan")

    st.markdown("#### 1. Rekonsiliasi: dashboard = data mart = acuan CSV")
    items = [("Jumlah order", n, mart["o"], ref("DWH fact_order", "Jumlah order"), 0),
             ("Order batal", batal, mart["b"], ref("DWH fact_order", "Order batal"), 0),
             ("Total pembayaran (Rp)", revenue, mart["r"], ref("DWH fact_order", "Total pembayaran (Rp)"), 0.01),
             ("Est. revenue hilang (Rp)", est, mart["e"], ref("DWH fact_order", "Est. revenue hilang (Rp)"), 1.0)]
    rows = []
    for name, dash, mt, csv, tol in items:
        ok = abs(dash - mt) <= tol and abs(mt - csv) <= max(tol, 1.0 if "Est." in name else tol)
        rows.append({"Ukuran": name, "Dashboard (v_order_flat)": ui.id_num(dash), "Data mart (v_kpi_monthly)": ui.id_num(float(mt)),
                     "Acuan CSV (hasil validasi)": "-" if pd.isna(csv) else ui.id_num(csv), "Status": "✅ Cocok" if ok else "❌ Selisih"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Angka dashboard tanpa filter dihitung dari v_order_flat, lalu dibandingkan dengan v_kpi_monthly dan dengan angka "
               "yang dihitung ulang dari CSV oleh `python -m etl.validate`.")

    with st.expander("2. Hasil validasi ETL terakhir"):
        if val.empty:
            st.info("Belum ada hasil validasi. Jalankan: python -m etl.validate")
        else:
            passed = int((val["hasil"] == "LULUS").sum())
            st.success(f"{passed} dari {len(val)} pemeriksaan lulus · batch {int(val['batch_id'].iloc[0])} · "
                       f"{pd.Timestamp(val['logged_at'].iloc[0]):%d-%m-%Y %H:%M}") if passed == len(val) \
                else st.error(f"{len(val) - passed} pemeriksaan GAGAL dari {len(val)}")
            st.dataframe(val[["lapisan", "pemeriksaan", "acuan_csv", "aktual", "hasil"]]
                         .assign(acuan_csv=lambda d: d["acuan_csv"].map(ui.id_text), aktual=lambda d: d["aktual"].map(ui.id_text))
                         .rename(columns={"lapisan": "Lapisan", "pemeriksaan": "Pemeriksaan", "acuan_csv": "Acuan CSV",
                                          "aktual": "Aktual", "hasil": "Hasil"}),
                         hide_index=True, width="stretch", height=280)

    with st.expander("3. Jejak proses ETL (audit trail)"):
        runs = data.query("SELECT batch_id, started_at, durasi_detik, triggered_by, status, order_dimuat, baris_ditolak, peringatan "
                          "FROM mart.v_etl_runs ORDER BY batch_id DESC LIMIT 10")
        st.dataframe(runs.rename(columns={"batch_id": "Batch", "started_at": "Mulai", "durasi_detik": "Durasi (dtk)",
                                          "triggered_by": "Dipicu oleh", "status": "Status", "order_dimuat": "Order dimuat",
                                          "baris_ditolak": "Ditolak", "peringatan": "Peringatan"}),
                     hide_index=True, width="stretch")

    with st.expander("4. Data lineage"):
        st.graphviz_chart(LINEAGE, width="stretch")

    with st.expander("5. Telusuri angka ke file sumber"):
        month = st.selectbox("Pilih bulan", sorted(orders["order_month"].unique()),
                             format_func=lambda d: ui.bulan(pd.Timestamp(d), True), key="trace_month")
        m = orders[orders["order_month"] == month]
        c1, c2, c3 = st.columns(3)
        ui.kpi(c1, "Order bulan ini", ui.id_num(len(m)), "baris pada v_order_flat", ui.SLATE)
        ui.kpi(c2, "Order batal", ui.id_num(int(m["is_cancelled"].sum())), "", ui.PRIMARY)
        ui.kpi(c3, "File sumber", ", ".join(sorted(m["source_file"].unique())), "kolom source_file di tabel fakta", ui.GOOD)
        st.write("")
        q = st.text_input("Cari order_id (opsional)", key="trace_id")
        shown = m[m["order_id"].str.contains(q.strip(), case=False, regex=False)] if q.strip() else m
        st.dataframe(ui.idf(shown[["order_id", "status_name", "cancel_reason", "payment_name", "province_name", "total_pembayaran", "source_file", "batch_id"]]
                     .head(15).rename(columns={"order_id": "Order ID", "status_name": "Status", "cancel_reason": "Alasan",
                                               "payment_name": "Pembayaran", "province_name": "Provinsi",
                                               "total_pembayaran": "Total bayar", "source_file": "File sumber", "batch_id": "Batch"})),
                     hide_index=True, width="stretch")

    with st.expander("6. Catatan kualitas data"):
        q1 = int(orders["is_time_missing"].sum())
        q2 = int(orders["is_weight_outlier"].sum())
        q3 = int(((orders["status_name"] == "Selesai") & (orders["total_pembayaran"] == 0)).sum())
        q4 = int((orders["courier"] == "Tidak Tercatat").sum())
        st.dataframe(ui.idf(pd.DataFrame([
            {"Temuan": "Order tanpa waktu pesanan", "Jumlah": q1, "Penanganan": "Bulan diturunkan dari nama file; tidak ikut analisis harian dan per jam"},
            {"Temuan": "Berat paket di atas 20 kg", "Jumlah": q2, "Penanganan": "Ditandai sebagai outlier, tidak dihapus"},
            {"Temuan": "Order Selesai bernilai Rp0", "Jumlah": q3, "Penanganan": "Dikeluarkan dari rata-rata penjualan untuk estimasi"},
            {"Temuan": "Kurir tidak tercatat", "Jumlah": q4, "Penanganan": "Seluruhnya batal; tidak dipakai menilai kurir"}])),
            hide_index=True, width="stretch")
