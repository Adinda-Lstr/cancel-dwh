"""TRANSFORM: membersihkan, menstandarkan, memetakan, dan memvalidasi data staging.

Jalankan dari folder proyek:  python -m etl.transform
Keluaran: DataFrame bersih (juga disimpan di data/processed/orders_clean.csv)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

from etl.db import get_engine, log_step, timer

PROCESSED_PATH = Path("data/processed/orders_clean.csv")
WEIGHT_OUTLIER_GR = 20_000  # di atas 20 kg ditandai outlier, TIDAK dihapus

NUM_INT = ["total_qty", "total_weight_gr", "total_returned_qty", "num_product_categories"]
NUM_MONEY = ["total_diskon", "ongkir_dibayar_pembeli", "estimasi_potongan_ongkir",
             "total_pembayaran", "perkiraan_ongkir"]
TEXT_COLS = ["order_id", "product_categories", "status_pesanan", "alasan_pembatalan",
             "opsi_pengiriman", "metode_pembayaran", "kota_kabupaten", "provinsi", "source_file"]
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}


# ---------------------------------------------------------------- referensi
def load_refs(engine):
    """Membaca kamus pemetaan dari schema ref."""
    q = lambda t: pd.read_sql(text(f"SELECT * FROM ref.{t}"), engine)
    return {
        "status": q("ref_status_map"),
        "payment": q("ref_payment_map").set_index("raw_text"),
        "reason": q("ref_cancel_reason_map").set_index("raw_text"),
        "shipping": q("ref_shipping_map").set_index("raw_text"),
    }


def map_status(value, status_ref):
    """Mencocokkan status dengan pola LIKE di ref_status_map ('%' = sembarang teks)."""
    for _, row in status_ref.iterrows():
        pattern = "^" + re.escape(row["raw_pattern"]).replace("%", ".*") + "$"
        if re.match(pattern, value):
            return row["status_std"], bool(row["is_final"])
    return "Unknown", False


def month_from_source_file(name):
    """'DecemberSales2024.xlsx' -> 2024-12-01. Dipakai bila waktu pesanan kosong."""
    m = re.match(r"([A-Za-z]+)Sales(\d{4})", str(name))
    if not m or m.group(1) not in MONTHS:
        return pd.NaT
    return pd.Timestamp(int(m.group(2)), MONTHS[m.group(1)], 1)


# ---------------------------------------------------------------- transform
def transform(engine, batch_id):
    refs = load_refs(engine)
    raw = pd.read_sql(text("SELECT * FROM stg.stg_order_raw WHERE batch_id = :b"),
                      engine, params={"b": batch_id})
    n_in = len(raw)
    df = raw.copy()

    # 1) Rapikan teks: buang spasi di tepi, teks kosong menjadi NULL
    for c in TEXT_COLS:
        df[c] = df[c].str.strip().replace("", np.nan)

    # 2) Konversi tipe data (nilai yang tidak bisa dikonversi menjadi NaN lalu ditolak)
    for c in NUM_INT + NUM_MONEY:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["order_ts"] = pd.to_datetime(df["waktu_pesanan_dibuat"], errors="coerce")
    df["order_month"] = df["order_ts"].dt.to_period("M").dt.to_timestamp()
    from_file = df["source_file"].map(month_from_source_file)
    df["order_month"] = df["order_month"].fillna(from_file)

    # 3) Aturan validasi: baris yang melanggar dipindah ke etl_reject
    rules = {
        "ORDER_ID_KOSONG": df["order_id"].isna(),
        "ORDER_ID_DUPLIKAT": df["order_id"].notna() & df["order_id"].duplicated(keep="first"),
        "ANGKA_TIDAK_VALID": df[NUM_INT + NUM_MONEY].isna().any(axis=1),
        "ANGKA_NEGATIF": (df[NUM_INT + NUM_MONEY] < 0).any(axis=1),
        "WAKTU_TIDAK_VALID": df["waktu_pesanan_dibuat"].notna() & df["order_ts"].isna(),
        "BULAN_TIDAK_DIKETAHUI": df["order_month"].isna(),
    }
    reject_mask = pd.Series(False, index=df.index)
    reject_rows = []
    for rule, mask in rules.items():
        new = mask & ~reject_mask  # satu baris dicatat satu kali, dengan aturan pertama yang dilanggar
        for _, r in raw[new].iterrows():
            reject_rows.append({"batch_id": batch_id, "source_file": r["source_file"],
                                "order_id": r["order_id"], "reject_rule": rule,
                                "reject_detail": f"Melanggar aturan {rule}",
                                "raw_row": json.dumps(r.drop(["batch_id", "loaded_at"]).astype(object)
                                                      .where(r.notna(), None).to_dict(), default=str)})
        reject_mask |= mask
    if reject_rows:
        with engine.begin() as conn:
            conn.execute(text("""INSERT INTO etl.etl_reject
                (batch_id, source_file, order_id, reject_rule, reject_detail, raw_row)
                VALUES (:batch_id, :source_file, :order_id, :reject_rule, :reject_detail,
                        CAST(:raw_row AS jsonb))"""), reject_rows)
    df = df[~reject_mask].copy()

    # 4) Standardisasi memakai kamus di schema ref
    st = df["status_pesanan"].map(lambda v: map_status(v, refs["status"]) if pd.notna(v) else ("Unknown", False))
    df["status_name"] = st.map(lambda x: x[0])
    df["status_is_final"] = st.map(lambda x: x[1])

    df["payment_name"] = df["metode_pembayaran"].where(df["metode_pembayaran"].isin(refs["payment"].index), "Unknown")
    df["payment_group"] = df["payment_name"].map(refs["payment"]["payment_group"]).fillna("Unknown")

    ship = refs["shipping"]
    known = df["opsi_pengiriman"].isin(ship.index)
    df["courier"] = np.where(known, df["opsi_pengiriman"].map(ship["courier"]), "Unknown")
    df["service_name"] = np.where(known, df["opsi_pengiriman"].map(ship["service_name"]), "Unknown")
    df["service_class"] = np.where(known, df["opsi_pengiriman"].map(ship["service_class"]), "Unknown")

    df["is_cancelled"] = df["status_name"].eq("Batal")
    rs = refs["reason"]
    has_reason = df["alasan_pembatalan"].isin(rs.index)
    df["cancel_actor"] = np.where(~df["is_cancelled"], "Tidak Ada",
                          np.where(has_reason, df["alasan_pembatalan"].map(rs["actor"]), "Unknown"))
    df["cancel_reason"] = np.where(~df["is_cancelled"], "Tidak Dibatalkan",
                          np.where(has_reason, df["alasan_pembatalan"].map(rs["reason_std"]), "Unknown"))
    df["cancel_reason_group"] = np.where(~df["is_cancelled"], "Tidak Dibatalkan",
                          np.where(has_reason, df["alasan_pembatalan"].map(rs["reason_group"]), "Unknown"))
    df["is_preventable"] = np.where(df["is_cancelled"] & has_reason,
                                    df["alasan_pembatalan"].map(rs["is_preventable"]), False).astype(bool)

    df["city_name"] = df["kota_kabupaten"].fillna("Unknown")
    df["province_name"] = df["provinsi"].fillna("Unknown")
    df["region_type"] = np.select([df["city_name"].str.startswith("KOTA"),
                                   df["city_name"].str.startswith("KAB")], ["Kota", "Kabupaten"], "Unknown")

    # 5) Kategori produk: satu sel berisi banyak kategori -> daftar (dipakai fact_order_category)
    df["categories"] = df["product_categories"].fillna("Unknown").str.split(", ")
    cat_mismatch = (df["categories"].str.len() != df["num_product_categories"]).sum()

    # 6) Kunci waktu dan flag
    has_ts = df["order_ts"].notna()
    df["date_key"] = np.where(has_ts, df["order_ts"].dt.strftime("%Y%m%d").fillna("0").astype(int), -1)
    df["time_key"] = np.where(has_ts, (df["order_ts"].dt.hour.fillna(0) * 100
                                       + df["order_ts"].dt.minute.fillna(0)).astype(int), -1)
    df["is_time_missing"] = ~has_ts
    df["is_returned"] = df["total_returned_qty"] > 0
    df["is_problem_order"] = df["is_cancelled"] | df["is_returned"]
    df["is_weight_outlier"] = df["total_weight_gr"] > WEIGHT_OUTLIER_GR

    # 7) Estimasi revenue hilang = rata-rata Total Pembayaran order Selesai (> Rp0) pada bulan yang sama.
    #    Order Selesai bernilai Rp0 dikeluarkan dari rata-rata (dicatat sebagai temuan kualitas data).
    basis = df[df["status_name"].eq("Selesai") & (df["total_pembayaran"] > 0)]
    avg_month = basis.groupby("order_month")["total_pembayaran"].mean()
    df["est_revenue_hilang"] = np.where(df["is_cancelled"], df["order_month"].map(avg_month).fillna(0), 0.0)
    no_basis = int((df["is_cancelled"] & df["order_month"].map(avg_month).isna()).sum())

    # 8) Catat temuan yang bukan penolakan (nilai tak terpetakan -> Unknown)
    warnings = {
        "status tak terpetakan": int((df["status_name"] == "Unknown").sum()),
        "metode bayar tak terpetakan": int((df["payment_name"] == "Unknown").sum()),
        "opsi pengiriman tak terpetakan": int((df["courier"] == "Unknown").sum()),
        "order batal tanpa alasan terpetakan": int((df["is_cancelled"] & ~has_reason).sum()),
        "kurir tidak tercatat": int((df["courier"] == "Tidak Tercatat").sum()),
        "order Selesai dengan pembayaran Rp0": int((df["status_name"].eq("Selesai") & (df["total_pembayaran"] == 0)).sum()),
        "jumlah kategori tidak cocok": int(cat_mismatch),
        "order batal tanpa dasar estimasi bulan itu": no_basis,
    }
    return df.reset_index(drop=True), len(reject_rows), warnings, n_in


def save_processed(df):
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = df.drop(columns=["waktu_pesanan_dibuat"]).copy()
    out["categories"] = out["categories"].str.join(" | ")
    out.to_csv(PROCESSED_PATH, index=False, encoding="utf-8")


def main():
    engine = get_engine()
    with engine.connect() as conn:
        batch_id = conn.execute(text("SELECT max(batch_id) FROM stg.stg_order_raw")).scalar()
    if batch_id is None:
        print("GAGAL: staging kosong. Jalankan dulu: python -m etl.extract")
        sys.exit(1)
    try:
        with timer() as t:
            df, n_rej, warnings, n_in = transform(engine, batch_id)
            save_processed(df)
        log_step(engine, batch_id, "transform", "SUCCESS", "Transformasi selesai",
                 target_table="data/processed/orders_clean.csv",
                 rows_read=n_in, rows_loaded=len(df), rows_rejected=n_rej, duration_ms=t())
        for name, count in warnings.items():
            if count:
                log_step(engine, batch_id, "transform", "WARNING", f"{name}: {count} baris")
        print(f"Transform selesai (batch {batch_id}): {n_in} masuk, {len(df)} lolos, {n_rej} ditolak")
        for name, count in warnings.items():
            print(f"  temuan - {name}: {count}")
    except Exception as exc:
        log_step(engine, batch_id, "transform", "ERROR", str(exc))
        print(f"GAGAL: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
