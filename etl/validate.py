"""VALIDASI end-to-end: Source (CSV) -> Staging -> Data Warehouse -> Data Mart.

Angka dihitung ULANG dari file CSV mentah dengan kode terpisah (pandas), lalu dibandingkan
dengan angka di setiap lapisan. Hasilnya dicatat di etl.etl_log (step 'validate').

Jalankan:  python -m etl.validate        Kode keluar 0 = semua cocok, 1 = ada selisih.
"""
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from etl.db import get_engine, log_step

CSV_PATH = Path("data/raw/all_months_clean.csv")
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}
MONEY_TOL = 0.01


def source_numbers():
    """Angka acuan, dihitung langsung dari CSV mentah."""
    df = pd.read_csv(CSV_PATH, sep=";", encoding="utf-8-sig", dtype=str)
    for c in ["total_weight_gr", "total_returned_qty", "Total Pembayaran"]:
        df[c] = pd.to_numeric(df[c])
    ts = pd.to_datetime(df["Waktu Pesanan Dibuat"], errors="coerce")
    m = df["source_file"].str.extract(r"([A-Za-z]+)Sales(\d{4})")
    from_file = pd.to_datetime(dict(year=m[1].astype(int), month=m[0].map(MONTHS), day=1))
    month = ts.dt.to_period("M").dt.to_timestamp().fillna(from_file)
    cancelled = df["Status Pesanan"].str.strip().eq("Batal")
    done = df["Status Pesanan"].str.strip().eq("Selesai") & (df["Total Pembayaran"] > 0)
    avg = df[done].groupby(month[done])["Total Pembayaran"].mean()
    est = float(month[cancelled].map(avg).fillna(0).sum())
    return {
        "rows": len(df), "unique_ids": df["order_id"].nunique(), "cancelled": int(cancelled.sum()),
        "returned": int((df["total_returned_qty"] > 0).sum()),
        "revenue": float(df["Total Pembayaran"].sum()), "time_missing": int(ts.isna().sum()),
        "outliers": int((df["total_weight_gr"] > 20000).sum()), "est": est,
        "known_date": int(ts.notna().sum()),
    }


def scalar(conn, sql):
    value = conn.execute(text(sql)).scalar()
    return 0 if value is None else float(value)


def run_checks(engine):
    src = source_numbers()
    checks = []  # (lapisan, pemeriksaan, nilai acuan, nilai aktual, toleransi)

    def add(layer, name, expected, sql, tol=0.0):
        with engine.connect() as conn:
            checks.append((layer, name, expected, scalar(conn, sql), tol))

    # --- Source -> Staging
    add("Staging", "Jumlah baris = CSV", src["rows"], "SELECT count(*) FROM stg.stg_order_raw")
    add("Staging", "order_id unik = CSV", src["unique_ids"], "SELECT count(DISTINCT order_id) FROM stg.stg_order_raw")
    # --- Source -> Data Warehouse (fakta 1)
    add("DWH fact_order", "Jumlah order", src["rows"], "SELECT count(*) FROM dw.fact_order")
    add("DWH fact_order", "Order batal", src["cancelled"], "SELECT count(*) FROM dw.fact_order WHERE is_cancelled")
    add("DWH fact_order", "Order retur", src["returned"], "SELECT count(*) FROM dw.fact_order WHERE is_returned")
    add("DWH fact_order", "Order tanpa waktu", src["time_missing"], "SELECT count(*) FROM dw.fact_order WHERE is_time_missing")
    add("DWH fact_order", "Outlier berat > 20 kg", src["outliers"], "SELECT count(*) FROM dw.fact_order WHERE is_weight_outlier")
    add("DWH fact_order", "Total pembayaran (Rp)", src["revenue"], "SELECT sum(total_pembayaran) FROM dw.fact_order", MONEY_TOL)
    add("DWH fact_order", "Est. revenue hilang (Rp)", src["est"], "SELECT sum(est_revenue_hilang) FROM dw.fact_order", 1.0)
    # --- Fakta 1 -> Fakta 2 dan 3 (galaxy: tiga fakta harus konsisten)
    add("DWH fact_order_category", "Jumlah order teralokasi", src["rows"], "SELECT sum(allocated_orders) FROM dw.fact_order_category", 0.001)
    add("DWH fact_order_category", "Total pembayaran teralokasi (Rp)", src["revenue"], "SELECT sum(allocated_payment) FROM dw.fact_order_category", MONEY_TOL)
    add("DWH fact_order_category", "Est. hilang teralokasi (Rp)", src["est"], "SELECT sum(allocated_est_hilang) FROM dw.fact_order_category", 1.0)
    add("DWH snapshot", "Jumlah order", src["rows"], "SELECT sum(total_orders) FROM dw.fact_daily_cancel_snapshot")
    add("DWH snapshot", "Order batal", src["cancelled"], "SELECT sum(cancelled_orders) FROM dw.fact_daily_cancel_snapshot")
    add("DWH snapshot", "Total pembayaran (Rp)", src["revenue"], "SELECT sum(realized_payment) FROM dw.fact_daily_cancel_snapshot", MONEY_TOL)
    # --- Data Warehouse -> Data Mart (yang dibaca dashboard)
    add("Mart v_order_flat", "Jumlah order", src["rows"], "SELECT count(*) FROM mart.v_order_flat")
    add("Mart v_kpi_monthly", "Jumlah order", src["rows"], "SELECT sum(total_orders) FROM mart.v_kpi_monthly")
    add("Mart v_kpi_monthly", "Order batal", src["cancelled"], "SELECT sum(cancelled_orders) FROM mart.v_kpi_monthly")
    add("Mart v_kpi_monthly", "Total pembayaran (Rp)", src["revenue"], "SELECT sum(realized_revenue) FROM mart.v_kpi_monthly", MONEY_TOL)
    add("Mart v_kpi_monthly", "Est. revenue hilang (Rp)", src["est"], "SELECT sum(est_revenue_hilang) FROM mart.v_kpi_monthly", 1.0)
    add("Mart v_cancel_reason", "Order batal", src["cancelled"], "SELECT sum(cancelled_orders) FROM mart.v_cancel_reason")
    add("Mart v_cancel_payment", "Jumlah order", src["rows"], "SELECT sum(total_orders) FROM mart.v_cancel_payment")
    add("Mart v_cancel_payment", "Order batal", src["cancelled"], "SELECT sum(cancelled_orders) FROM mart.v_cancel_payment")
    add("Mart v_cancel_location", "Jumlah order", src["rows"], "SELECT sum(total_orders) FROM mart.v_cancel_location")
    add("Mart v_cancel_shipping", "Jumlah order", src["rows"], "SELECT sum(total_orders) FROM mart.v_cancel_shipping")
    add("Mart v_cancel_category", "Total pembayaran teralokasi (Rp)", src["revenue"], "SELECT sum(alloc_revenue) FROM mart.v_cancel_category", MONEY_TOL)
    add("Mart v_event_comparison", "Order bertanggal", src["known_date"], "SELECT sum(total_orders) FROM mart.v_event_comparison WHERE event_category <> 'Unknown'")
    add("Mart v_daily_trend", "Order bertanggal", src["known_date"], "SELECT sum(total_orders) FROM mart.v_daily_trend")
    # --- Integritas
    add("Integritas", "Order tanpa baris kategori", 0,
        "SELECT count(*) FROM dw.fact_order o WHERE NOT EXISTS (SELECT 1 FROM dw.fact_order_category c WHERE c.order_key = o.order_key)")
    add("Integritas", "Order dengan key Unknown (status/pembayaran/kurir/lokasi/alasan)", 0,
        "SELECT count(*) FROM dw.fact_order WHERE status_key=-1 OR payment_key=-1 OR shipping_key=-1 OR location_key=-1 OR cancel_reason_key=-1")
    return checks


def main():
    engine = get_engine()
    with engine.connect() as conn:
        batch_id = conn.execute(text("SELECT max(batch_id) FROM etl.etl_batch WHERE status = 'SUCCESS'")).scalar()
    if batch_id is None:
        print("GAGAL: belum ada batch ETL yang sukses. Jalankan dulu: python -m etl.run_etl")
        sys.exit(1)

    checks = run_checks(engine)
    failed = 0
    print(f"VALIDASI Source -> Staging -> DWH -> Mart (batch {batch_id})")
    print(f"{'Lapisan':26} {'Pemeriksaan':48} {'Acuan CSV':>16} {'Aktual':>16}  Status")
    for layer, name, expected, actual, tol in checks:
        ok = abs(expected - actual) <= tol
        failed += not ok
        fmt = (lambda v: f"{v:,.2f}") if (tol >= MONEY_TOL or expected != int(expected)) else (lambda v: f"{int(v):,}")
        print(f"{layer:26} {name[:48]:48} {fmt(expected):>16} {fmt(actual):>16}  {'LULUS' if ok else 'GAGAL'}")
        if not ok:
            log_step(engine, batch_id, "validate", "ERROR",
                     f"{layer} - {name}: acuan {expected}, aktual {actual}")
    status = "SUCCESS" if not failed else "ERROR"
    log_step(engine, batch_id, "validate", status,
             f"{len(checks) - failed}/{len(checks)} pemeriksaan lulus", rows_read=len(checks),
             rows_rejected=failed)
    print(f"\nHasil: {len(checks) - failed}/{len(checks)} lulus" + ("" if not failed else f", {failed} GAGAL"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
