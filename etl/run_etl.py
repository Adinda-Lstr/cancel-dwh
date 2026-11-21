"""Orkestrator: menjalankan Extract -> Transform -> Load dalam SATU batch.

Jalankan dari folder proyek:   python -m etl.run_etl
Untuk penjadwalan (cron):       python -m etl.run_etl --triggered-by cron
Kode keluar: 0 = sukses, 1 = gagal/dihentikan, 2 = database tidak terhubung.
"""
import argparse
import sys

from sqlalchemy.exc import OperationalError

from etl.db import finish_batch, get_engine, log_step, start_batch, timer
from etl.extract import extract
from etl.load import load
from etl.transform import save_processed, transform

REJECT_TOLERANCE = 0.05  # bila baris ditolak > 5%, pemuatan dihentikan untuk diperiksa


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--triggered-by", default="manual", choices=["manual", "cron"])
    args = parser.parse_args()

    engine = get_engine()
    try:
        batch_id = start_batch(engine, args.triggered_by)
    except OperationalError:
        print("GAGAL: tidak bisa terhubung ke database. Cek Docker Desktop dan isi file .env.")
        sys.exit(2)
    print(f"Batch {batch_id} dimulai ({args.triggered_by})")

    try:
        with timer() as total:
            n_extract = extract(engine, batch_id)
            print(f"[1/3] Extract : {n_extract} baris ke staging")

            df, n_rej, warnings, n_in = transform(engine, batch_id)
            log_step(engine, batch_id, "transform", "SUCCESS", "Transformasi selesai",
                     rows_read=n_in, rows_loaded=len(df), rows_rejected=n_rej)
            for name, count in warnings.items():
                if count:
                    log_step(engine, batch_id, "transform", "WARNING", f"{name}: {count} baris")
            print(f"[2/3] Transform: {len(df)} lolos, {n_rej} ditolak")

            if n_in and n_rej / n_in > REJECT_TOLERANCE:
                msg = f"Baris ditolak {n_rej}/{n_in} melebihi toleransi {REJECT_TOLERANCE:.0%}; load dihentikan"
                log_step(engine, batch_id, "validate", "ERROR", msg)
                finish_batch(engine, batch_id, "HALTED")
                print("DIHENTIKAN:", msg)
                sys.exit(1)

            save_processed(df)
            result = load(engine, batch_id, df)
            print(f"[3/3] Load     : fact_order={result['fact_order']} "
                  f"(baru {result['inserted']}, diperbarui {result['updated']}), "
                  f"fact_order_category={result['fact_order_category']}, "
                  f"snapshot={result['fact_daily_cancel_snapshot']}")
        finish_batch(engine, batch_id, "SUCCESS")
        log_step(engine, batch_id, "load", "INFO", "Batch selesai", duration_ms=total())
        print(f"Selesai dalam {total() / 1000:.1f} detik. Batch {batch_id} = SUCCESS")
    except SystemExit:
        raise
    except Exception as exc:
        log_step(engine, batch_id, "load", "ERROR", str(exc)[:1000])
        finish_batch(engine, batch_id, "FAILED")
        print(f"GAGAL: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
