"""EXTRACT: membaca CSV mentah lalu menyalinnya apa adanya ke stg.stg_order_raw.

Jalankan dari folder proyek:  python -m etl.extract
"""
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from etl.db import finish_batch, get_engine, log_step, start_batch, timer

CSV_PATH = Path("data/raw/all_months_clean.csv")

# Urutan dan nama kolom yang diharapkan di CSV  ->  nama kolom di tabel staging
COLUMN_MAP = {
    "order_id": "order_id",
    "total_qty": "total_qty",
    "total_weight_gr": "total_weight_gr",
    "total_returned_qty": "total_returned_qty",
    "Total Diskon": "total_diskon",
    "product_categories": "product_categories",
    "num_product_categories": "num_product_categories",
    "Status Pesanan": "status_pesanan",
    "Alasan Pembatalan": "alasan_pembatalan",
    "Opsi Pengiriman": "opsi_pengiriman",
    "Metode Pembayaran": "metode_pembayaran",
    "Kota/Kabupaten": "kota_kabupaten",
    "Provinsi": "provinsi",
    "Ongkos Kirim Dibayar oleh Pembeli": "ongkir_dibayar_pembeli",
    "Estimasi Potongan Biaya Pengiriman": "estimasi_potongan_ongkir",
    "Total Pembayaran": "total_pembayaran",
    "Perkiraan Ongkos Kirim": "perkiraan_ongkir",
    "Waktu Pesanan Dibuat": "waktu_pesanan_dibuat",
    "source_file": "source_file",
}


def extract(engine, batch_id):
    # 1) Baca file. dtype=str: semua kolom dibaca sebagai teks, TIDAK ada konversi di tahap ini.
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"File sumber tidak ditemukan: {CSV_PATH}")
    with timer() as t:
        df = pd.read_csv(CSV_PATH, sep=";", encoding="utf-8-sig", dtype=str)
        log_step(engine, batch_id, "extract", "INFO", f"CSV dibaca dari {CSV_PATH}",
                 source_file=CSV_PATH.name, rows_read=len(df), duration_ms=t())

    # 2) Validasi struktur kolom (skenario error: struktur kolom tidak sesuai)
    missing = set(COLUMN_MAP) - set(df.columns)
    extra = set(df.columns) - set(COLUMN_MAP)
    if missing or extra:
        raise ValueError(f"Struktur kolom tidak sesuai. Hilang: {missing or '-'}; berlebih: {extra or '-'}")

    # 3) Ganti nama kolom dan tambah metadata batch
    df = df[list(COLUMN_MAP)].rename(columns=COLUMN_MAP)
    df["batch_id"] = batch_id

    # 4) Kosongkan staging lalu isi. Staging hanya menampung batch yang sedang diproses.
    with timer() as t:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE stg.stg_order_raw"))
            df.to_sql("stg_order_raw", conn, schema="stg", if_exists="append",
                      index=False, chunksize=2000)
        log_step(engine, batch_id, "extract", "SUCCESS", "Data mentah dimuat ke staging",
                 target_table="stg.stg_order_raw", rows_read=len(df),
                 rows_loaded=len(df), duration_ms=t())
    return len(df)


def main():
    engine = get_engine()
    try:
        batch_id = start_batch(engine)
    except OperationalError:
        # Skenario error: database tidak bisa dihubungi. Belum ada batch, jadi cukup pesan jelas.
        print("GAGAL: tidak bisa terhubung ke database. Cek Docker Desktop dan isi file .env.")
        sys.exit(2)
    print(f"Batch {batch_id} dimulai")
    try:
        n = extract(engine, batch_id)
        finish_batch(engine, batch_id, "SUCCESS")
        print(f"Extract selesai: {n} baris masuk ke stg.stg_order_raw")
    except Exception as exc:  # semua kegagalan dicatat, lalu proses dihentikan
        log_step(engine, batch_id, "extract", "ERROR", str(exc))
        finish_batch(engine, batch_id, "FAILED")
        print(f"GAGAL: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
