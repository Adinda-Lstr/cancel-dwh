"""LOAD: mengisi dimensi dan tiga tabel fakta galaxy schema dari data hasil Transform.

Dipanggil oleh etl/run_etl.py (tidak dijalankan sendiri).
Semua pemuatan bersifat idempotent: dijalankan ulang tidak membuat data ganda.
"""
import numpy as np
import pandas as pd
from sqlalchemy import text

from etl.db import log_step, timer

DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
MONTH_NAMES = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
               "Agustus", "September", "Oktober", "November", "Desember"]


def _day_part(hour):
    if hour < 5:
        return "Dini Hari"
    if hour < 11:
        return "Pagi"
    if hour < 15:
        return "Siang"
    if hour < 18:
        return "Sore"
    return "Malam"


def _is_payday(day):
    """Periode gajian (ASUMSI rancangan): tanggal 25 sampai tanggal 3 bulan berikutnya."""
    return day >= 25 or day <= 3


# ------------------------------------------------------------------ dimensi
def load_dim_date(conn, start, end):
    """Kalender lengkap dari tanggal pertama sampai terakhir data, termasuk hari libur dari ref."""
    holidays = dict(conn.execute(text("SELECT holiday_date, holiday_name FROM ref.ref_holiday")).fetchall())
    rows = []
    for d in pd.date_range(start, end, freq="D"):
        rows.append({
            "date_key": int(d.strftime("%Y%m%d")), "full_date": d.date(),
            "day_of_month": d.day, "day_name": DAY_NAMES[d.weekday()],
            "iso_week": int(d.isocalendar().week), "month_num": d.month,
            "month_name": MONTH_NAMES[d.month - 1], "month_start": d.replace(day=1).date(),
            "quarter_num": (d.month - 1) // 3 + 1, "year_num": d.year,
            "is_weekend": d.weekday() >= 5, "is_twin_date": d.day == d.month,
            "is_holiday": d.date() in holidays, "holiday_name": holidays.get(d.date()),
            "is_payday": _is_payday(d.day),
        })
    conn.execute(text("""
        INSERT INTO dw.dim_date (date_key, full_date, day_of_month, day_name, iso_week, month_num,
            month_name, month_start, quarter_num, year_num, is_weekend, is_twin_date,
            is_holiday, holiday_name, is_payday)
        VALUES (:date_key, :full_date, :day_of_month, :day_name, :iso_week, :month_num,
            :month_name, :month_start, :quarter_num, :year_num, :is_weekend, :is_twin_date,
            :is_holiday, :holiday_name, :is_payday)
        ON CONFLICT (date_key) DO UPDATE SET
            is_holiday = EXCLUDED.is_holiday, holiday_name = EXCLUDED.holiday_name,
            is_payday = EXCLUDED.is_payday"""), rows)
    return len(rows)


def load_dim_time(conn):
    rows = [{"time_key": h * 100 + m, "hour_24": h, "minute_num": m, "day_part": _day_part(h)}
            for h in range(24) for m in range(60)]
    conn.execute(text("""INSERT INTO dw.dim_time (time_key, hour_24, minute_num, day_part)
        VALUES (:time_key, :hour_24, :minute_num, :day_part) ON CONFLICT (time_key) DO NOTHING"""), rows)
    return len(rows)


def load_dim_event(conn, start, end):
    """Event = tanggal kembar (aturan: hari = bulan) + baris dari ref.ref_event_calendar bila ada.
    12.12 diberi kategori Harbolnas. Event bersifat PEMBANDING deskriptif, bukan penyebab."""
    wanted = []
    for d in pd.date_range(start, end, freq="D"):
        if d.day == d.month:
            if d.month == 12:
                wanted.append((f"12.12 (Harbolnas) {d.year}", "Harbolnas", d.date(), d.date()))
            else:
                wanted.append((f"{d.day}.{d.month} {d.year}", "Tanggal Kembar", d.date(), d.date()))
    for r in conn.execute(text("SELECT event_name, event_category, start_date, end_date FROM ref.ref_event_calendar")):
        wanted.append(tuple(r))
    existing = {(r[0], r[1]) for r in conn.execute(text("SELECT event_name, start_date FROM dw.dim_event"))}
    new = [{"n": n, "c": c, "s": s, "e": e} for n, c, s, e in wanted if (n, s) not in existing]
    if new:
        conn.execute(text("""INSERT INTO dw.dim_event (event_name, event_category, start_date, end_date)
                             VALUES (:n, :c, :s, :e)"""), new)
    return len(new)


def load_simple_dims(conn, df):
    """Dimensi yang nilainya diturunkan dari data: insert bila baru, perbarui atribut bila berubah."""
    def run(sql, frame):
        rows = frame.drop_duplicates().to_dict("records")
        if rows:
            conn.execute(text(sql), rows)
        return len(rows)

    n = {}
    n["dim_location"] = run("""INSERT INTO dw.dim_location (city_name, region_type, province_name)
        VALUES (:city_name, :region_type, :province_name)
        ON CONFLICT (province_name, city_name) DO UPDATE SET region_type = EXCLUDED.region_type""",
        df[["city_name", "region_type", "province_name"]])
    n["dim_payment"] = run("""INSERT INTO dw.dim_payment (payment_name, payment_group)
        VALUES (:payment_name, :payment_group)
        ON CONFLICT (payment_name) DO UPDATE SET payment_group = EXCLUDED.payment_group""",
        df[["payment_name", "payment_group"]])
    n["dim_shipping"] = run("""INSERT INTO dw.dim_shipping (courier, service_name, service_class)
        VALUES (:courier, :service_name, :service_class)
        ON CONFLICT (courier, service_name) DO UPDATE SET service_class = EXCLUDED.service_class""",
        df[["courier", "service_name", "service_class"]])
    # SCD Type 1: status baru atau berubah menimpa nilai lama (riwayat tidak disimpan)
    n["dim_status"] = run("""INSERT INTO dw.dim_status (status_name, is_final)
        VALUES (:status_name, :is_final)
        ON CONFLICT (status_name) DO UPDATE SET is_final = EXCLUDED.is_final""",
        df[["status_name", "status_is_final"]].rename(columns={"status_is_final": "is_final"}))
    n["dim_cancel_reason"] = run("""INSERT INTO dw.dim_cancel_reason (actor, reason_std, reason_group, is_preventable)
        VALUES (:actor, :reason_std, :reason_group, :is_preventable)
        ON CONFLICT (actor, reason_std) DO UPDATE SET
            reason_group = EXCLUDED.reason_group, is_preventable = EXCLUDED.is_preventable""",
        df[["cancel_actor", "cancel_reason", "cancel_reason_group", "is_preventable"]].rename(
            columns={"cancel_actor": "actor", "cancel_reason": "reason_std",
                     "cancel_reason_group": "reason_group"}))
    cats = pd.DataFrame({"category_name": df["categories"].explode().dropna().unique()})
    n["dim_product_category"] = run("""INSERT INTO dw.dim_product_category (category_name)
        VALUES (:category_name) ON CONFLICT (category_name) DO NOTHING""", cats)
    return n


# -------------------------------------------------------------------- kunci
def _event_lookup(conn):
    """date -> event_key. Bila ada event yang tumpang tindih, yang mulai lebih awal dipakai."""
    ev = conn.execute(text("""SELECT event_key, start_date, end_date FROM dw.dim_event
        WHERE event_key > 0 AND start_date IS NOT NULL ORDER BY start_date, event_key""")).fetchall()
    mapping, overlaps = {}, 0
    for key, s, e in ev:
        for d in pd.date_range(s, e, freq="D"):
            if d.date() in mapping:
                overlaps += 1
            else:
                mapping[d.date()] = key
    return mapping, overlaps


def _key_frame(conn, sql):
    result = conn.execute(text(sql))
    return pd.DataFrame(result.fetchall(), columns=list(result.keys()))


def attach_keys(conn, df):
    """Mengganti nilai deskriptif dengan surrogate key dimensi. Tidak ditemukan -> -1 (Unknown)."""
    out = df.copy()
    ev_map, overlaps = _event_lookup(conn)
    order_date = pd.to_datetime(out["order_ts"]).dt.date
    out["event_key"] = [(-1 if d is None or pd.isna(d) else ev_map.get(d, 0)) for d in order_date]

    def merge(left, sql, on, key):
        right = _key_frame(conn, sql)
        merged = left.merge(right, how="left", on=on)
        missing = int(merged[key].isna().sum())
        merged[key] = merged[key].fillna(-1).astype(int)
        return merged, missing

    miss = {}
    out, miss["location"] = merge(out, "SELECT location_key, province_name, city_name FROM dw.dim_location",
                                  ["province_name", "city_name"], "location_key")
    out, miss["payment"] = merge(out, "SELECT payment_key, payment_name FROM dw.dim_payment",
                                 ["payment_name"], "payment_key")
    out, miss["shipping"] = merge(out, "SELECT shipping_key, courier, service_name FROM dw.dim_shipping",
                                  ["courier", "service_name"], "shipping_key")
    out, miss["status"] = merge(out, "SELECT status_key, status_name FROM dw.dim_status",
                                ["status_name"], "status_key")
    out, miss["cancel_reason"] = merge(
        out, "SELECT cancel_reason_key, actor AS cancel_actor, reason_std AS cancel_reason FROM dw.dim_cancel_reason",
        ["cancel_actor", "cancel_reason"], "cancel_reason_key")
    return out, miss, overlaps


# -------------------------------------------------------------------- fakta
FACT_ORDER_COLS = [
    "order_id", "date_key", "time_key", "event_key", "location_key", "payment_key", "shipping_key",
    "status_key", "cancel_reason_key", "total_qty", "total_weight_gr", "total_returned_qty",
    "total_diskon", "ongkir_pembeli", "est_potongan_ongkir", "total_pembayaran", "perkiraan_ongkir",
    "num_categories", "est_revenue_hilang", "is_cancelled", "is_returned", "is_problem_order",
    "is_time_missing", "is_weight_outlier", "order_month", "source_file", "batch_id"]


def load_fact_order(conn, df, batch_id):
    f = df.rename(columns={"ongkir_dibayar_pembeli": "ongkir_pembeli",
                           "estimasi_potongan_ongkir": "est_potongan_ongkir",
                           "num_product_categories": "num_categories"}).copy()
    f["batch_id"] = batch_id
    f["order_month"] = pd.to_datetime(f["order_month"]).dt.strftime("%Y-%m-%d")
    for c in ["total_qty", "total_weight_gr", "total_returned_qty", "num_categories"]:
        f[c] = f[c].astype(int)
    f[FACT_ORDER_COLS].to_sql("tmp_fact_order", conn, schema="stg", if_exists="replace",
                              index=False, chunksize=2000)
    cols = ", ".join(FACT_ORDER_COLS)
    selects = ", ".join("CAST(order_month AS date)" if c == "order_month" else c for c in FACT_ORDER_COLS)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in FACT_ORDER_COLS if c != "order_id")
    existing = conn.execute(text("""SELECT count(*) FROM dw.fact_order o
                                    JOIN stg.tmp_fact_order t USING (order_id)""")).scalar()
    # Upsert: order yang sudah ada diperbarui (status, flag, estimasi), order baru ditambahkan
    conn.execute(text(f"""INSERT INTO dw.fact_order ({cols}) SELECT {selects} FROM stg.tmp_fact_order
                          ON CONFLICT (order_id) DO UPDATE SET {updates}, loaded_at = now()"""))
    conn.execute(text("DROP TABLE stg.tmp_fact_order"))
    return len(f), len(f) - existing, existing


def _split_evenly(total_units, n, rank):
    """Membagi total (bilangan bulat) rata ke n baris tanpa sisa: selisih dibagi ke baris pertama."""
    base, rem = np.divmod(total_units, n)
    return base + (rank < rem).astype(int)


def load_fact_order_category(conn, f, batch_id):
    """Satu order x satu kategori. Nilai dialokasikan merata sehingga jumlahnya = nilai order (tanpa hitung ganda)."""
    keys = pd.DataFrame(conn.execute(text("SELECT order_key, order_id FROM dw.fact_order")).fetchall(),
                        columns=["order_key", "order_id"])
    c = f[["order_id", "categories", "date_key", "event_key", "location_key", "payment_key",
           "status_key", "cancel_reason_key", "is_cancelled", "order_month",
           "total_pembayaran", "est_revenue_hilang"]].explode("categories").rename(
        columns={"categories": "category_name"})
    c = c.drop_duplicates(["order_id", "category_name"]).merge(keys, on="order_id", how="left")
    cat_keys = pd.DataFrame(conn.execute(text("SELECT category_key, category_name FROM dw.dim_product_category")).fetchall(),
                            columns=["category_key", "category_name"])
    c = c.merge(cat_keys, on="category_name", how="left")
    c["category_key"] = c["category_key"].fillna(-1).astype(int)
    c["n"] = c.groupby("order_id")["category_name"].transform("size")
    c["rank"] = c.groupby("order_id").cumcount()
    c["weight_factor"] = (1.0 / c["n"]).round(6)
    # Alokasi memakai satuan bulat (sen dan mikro) agar penjumlahan tepat
    c["allocated_orders"] = _split_evenly(np.full(len(c), 1_000_000), c["n"].values, c["rank"].values) / 1e6
    pay_cents = np.round(c["total_pembayaran"].values * 100).astype(np.int64)
    est_cents = np.round(c["est_revenue_hilang"].values * 100).astype(np.int64)
    c["allocated_payment"] = _split_evenly(pay_cents, c["n"].values, c["rank"].values) / 100
    c["allocated_est_hilang"] = _split_evenly(est_cents, c["n"].values, c["rank"].values) / 100
    c["order_month"] = pd.to_datetime(c["order_month"]).dt.strftime("%Y-%m-%d")
    c["batch_id"] = batch_id
    cols = ["order_key", "category_key", "date_key", "event_key", "location_key", "payment_key",
            "status_key", "cancel_reason_key", "weight_factor", "allocated_orders",
            "allocated_payment", "allocated_est_hilang", "is_cancelled", "order_month", "batch_id"]
    c[cols].to_sql("tmp_fact_order_category", conn, schema="stg", if_exists="replace",
                   index=False, chunksize=2000)
    # Hapus lalu isi ulang kategori untuk order yang sedang dimuat (set kategori bisa berubah)
    conn.execute(text("""DELETE FROM dw.fact_order_category WHERE order_key IN
                         (SELECT order_key FROM stg.tmp_fact_order_category)
                         OR order_key IN (SELECT order_key FROM dw.fact_order WHERE batch_id = :b)"""),
                 {"b": batch_id})
    selects = ", ".join("CAST(order_month AS date)" if x == "order_month" else x for x in cols)
    conn.execute(text(f"INSERT INTO dw.fact_order_category ({', '.join(cols)}) "
                      f"SELECT {selects} FROM stg.tmp_fact_order_category"))
    conn.execute(text("DROP TABLE stg.tmp_fact_order_category"))
    return len(c)


def rebuild_snapshot(conn, batch_id):
    """Periodic snapshot: dibentuk ulang dari fact_order setiap batch (tanggal x metode bayar x layanan kirim)."""
    conn.execute(text("TRUNCATE dw.fact_daily_cancel_snapshot"))
    conn.execute(text("""
        INSERT INTO dw.fact_daily_cancel_snapshot
            (date_key, event_key, payment_key, shipping_key, order_month, total_orders,
             cancelled_orders, returned_orders, realized_payment, est_revenue_hilang, batch_id)
        SELECT date_key, event_key, payment_key, shipping_key, order_month, count(*),
               count(*) FILTER (WHERE is_cancelled), count(*) FILTER (WHERE is_returned),
               sum(total_pembayaran), sum(est_revenue_hilang), :b
        FROM dw.fact_order
        GROUP BY date_key, event_key, payment_key, shipping_key, order_month"""), {"b": batch_id})
    return conn.execute(text("SELECT count(*) FROM dw.fact_daily_cancel_snapshot")).scalar()


# --------------------------------------------------------------------- utama
def load(engine, batch_id, df):
    """Seluruh Load berjalan dalam SATU transaksi: gagal di tengah = tidak ada yang berubah."""
    dated = pd.to_datetime(df["order_ts"]).dropna()
    start, end = dated.min().normalize(), dated.max().normalize()
    with timer() as t, engine.begin() as conn:
        n = {"dim_date": load_dim_date(conn, start, end), "dim_time": load_dim_time(conn),
             "dim_event (baru)": load_dim_event(conn, start, end)}
        n.update(load_simple_dims(conn, df))
        for name, count in n.items():
            log_step(engine, batch_id, "load", "INFO", f"Dimensi dimuat: {name}",
                     target_table=f"dw.{name.split(' ')[0]}", rows_loaded=count)

        keyed, miss, overlaps = attach_keys(conn, df)
        for dim, count in miss.items():
            if count:
                log_step(engine, batch_id, "load", "WARNING",
                         f"{count} baris tidak punya pasangan di dim_{dim}, dipetakan ke Unknown (-1)")
        if overlaps:
            log_step(engine, batch_id, "load", "WARNING", f"{overlaps} tanggal tercakup lebih dari satu event")

        total, inserted, updated = load_fact_order(conn, keyed, batch_id)
        n_cat = load_fact_order_category(conn, keyed, batch_id)
        n_snap = rebuild_snapshot(conn, batch_id)
    ms = t()
    log_step(engine, batch_id, "load", "SUCCESS",
             f"fact_order: {inserted} baru, {updated} diperbarui", target_table="dw.fact_order",
             rows_read=total, rows_loaded=total, duration_ms=ms)
    log_step(engine, batch_id, "load", "SUCCESS", "fact_order_category dimuat",
             target_table="dw.fact_order_category", rows_loaded=n_cat)
    log_step(engine, batch_id, "load", "SUCCESS", "fact_daily_cancel_snapshot dibentuk ulang",
             target_table="dw.fact_daily_cancel_snapshot", rows_loaded=n_snap)
    return {"fact_order": total, "inserted": inserted, "updated": updated,
            "fact_order_category": n_cat, "fact_daily_cancel_snapshot": n_snap}
