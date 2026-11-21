"""Koneksi database dan pencatatan audit (etl_batch, etl_log) untuk seluruh proses ETL."""
import os
import time
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()  # membaca file .env di folder proyek


def get_engine():
    """Engine untuk user ETL (hak akses: tulis stg/dw/etl, baca ref). Password dari .env."""
    url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("ETL_DB_USER", "etl_user"),
        password=os.environ["DWH_ENGINEER_PASSWORD"],
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )
    return create_engine(url)


def start_batch(engine, triggered_by="manual"):
    """Membuat satu baris di etl_batch dan mengembalikan batch_id-nya."""
    with engine.begin() as conn:
        return conn.execute(
            text("INSERT INTO etl.etl_batch (triggered_by) VALUES (:t) RETURNING batch_id"),
            {"t": triggered_by},
        ).scalar_one()


def finish_batch(engine, batch_id, status):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE etl.etl_batch SET finished_at = now(), status = :s WHERE batch_id = :b"),
            {"s": status, "b": batch_id},
        )


def log_step(engine, batch_id, step, status, message=None, source_file=None,
             target_table=None, rows_read=None, rows_loaded=None,
             rows_rejected=None, duration_ms=None):
    """Mencatat satu kejadian ke etl.etl_log."""
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO etl.etl_log
                    (batch_id, step, status, message, source_file, target_table,
                     rows_read, rows_loaded, rows_rejected, duration_ms)
                    VALUES (:b,:st,:ss,:m,:sf,:tt,:rr,:rl,:rj,:d)"""),
            {"b": batch_id, "st": step, "ss": status, "m": message, "sf": source_file,
             "tt": target_table, "rr": rows_read, "rl": rows_loaded,
             "rj": rows_rejected, "d": duration_ms},
        )


@contextmanager
def timer():
    """Mengukur durasi dalam milidetik: with timer() as t: ... lalu t()"""
    start = time.perf_counter()
    yield lambda: int((time.perf_counter() - start) * 1000)
