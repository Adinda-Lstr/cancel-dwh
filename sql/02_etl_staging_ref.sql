-- 02_etl_staging_ref.sql : audit trail, staging, dan referensi

-- ---------- ETL control / audit trail ----------
CREATE TABLE IF NOT EXISTS etl.etl_batch (
    batch_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ,
    triggered_by TEXT NOT NULL DEFAULT 'manual',          -- manual | cron
    status       TEXT NOT NULL DEFAULT 'RUNNING'
                 CHECK (status IN ('RUNNING','SUCCESS','FAILED','HALTED'))
);

CREATE TABLE IF NOT EXISTS etl.etl_log (
    log_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_id      BIGINT NOT NULL REFERENCES etl.etl_batch(batch_id),
    logged_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    step          TEXT NOT NULL,                           -- extract|transform|load|validate|mart
    source_file   TEXT,
    target_table  TEXT,
    rows_read     INTEGER,
    rows_loaded   INTEGER,
    rows_rejected INTEGER,
    duration_ms   INTEGER,
    status        TEXT NOT NULL CHECK (status IN ('INFO','SUCCESS','WARNING','ERROR')),
    message       TEXT
);

CREATE TABLE IF NOT EXISTS etl.etl_reject (
    reject_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_id      BIGINT NOT NULL REFERENCES etl.etl_batch(batch_id),
    rejected_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_file   TEXT,
    order_id      TEXT,
    reject_rule   TEXT NOT NULL,
    reject_detail TEXT,
    raw_row       JSONB
);

-- ---------- Staging: salinan apa adanya, semua TEXT ----------
CREATE TABLE IF NOT EXISTS stg.stg_order_raw (
    order_id TEXT, total_qty TEXT, total_weight_gr TEXT, total_returned_qty TEXT,
    total_diskon TEXT, product_categories TEXT, num_product_categories TEXT,
    status_pesanan TEXT, alasan_pembatalan TEXT, opsi_pengiriman TEXT,
    metode_pembayaran TEXT, kota_kabupaten TEXT, provinsi TEXT,
    ongkir_dibayar_pembeli TEXT, estimasi_potongan_ongkir TEXT,
    total_pembayaran TEXT, perkiraan_ongkir TEXT, waktu_pesanan_dibuat TEXT,
    source_file TEXT, batch_id BIGINT, loaded_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_stg_order_batch ON stg.stg_order_raw(batch_id);

CREATE TABLE IF NOT EXISTS stg.stg_event   (raw JSONB, source_file TEXT, batch_id BIGINT, loaded_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS stg.stg_libur   (raw JSONB, source_file TEXT, batch_id BIGINT, loaded_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS stg.stg_wilayah (raw JSONB, source_file TEXT, batch_id BIGINT, loaded_at TIMESTAMPTZ DEFAULT now());

-- ---------- Referensi & aturan pemetaan ----------
CREATE TABLE IF NOT EXISTS ref.ref_status_map (
    raw_pattern TEXT PRIMARY KEY,                          -- dicocokkan dengan LIKE
    status_std  TEXT NOT NULL,
    is_final    BOOLEAN NOT NULL
);
CREATE TABLE IF NOT EXISTS ref.ref_cancel_reason_map (
    raw_text       TEXT PRIMARY KEY,
    actor          TEXT NOT NULL,                          -- Pembeli | Sistem | Penjual
    reason_std     TEXT NOT NULL,
    reason_group   TEXT NOT NULL,
    is_preventable BOOLEAN NOT NULL                        -- dapat dicegah penjual
);
CREATE TABLE IF NOT EXISTS ref.ref_shipping_map (
    raw_text      TEXT PRIMARY KEY,
    courier       TEXT NOT NULL,
    service_name  TEXT NOT NULL,
    service_class TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ref.ref_payment_map (
    raw_text      TEXT PRIMARY KEY,
    payment_group TEXT NOT NULL                            -- COD|E-Wallet|PayLater|Gerai|Kartu|Transfer|Lainnya
);
CREATE TABLE IF NOT EXISTS ref.ref_event_calendar (
    event_name TEXT NOT NULL, event_category TEXT NOT NULL,
    start_date DATE NOT NULL, end_date DATE NOT NULL,
    source_url TEXT, verified BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (event_name, start_date)
);
CREATE TABLE IF NOT EXISTS ref.ref_holiday (
    holiday_date DATE PRIMARY KEY, holiday_name TEXT NOT NULL,
    holiday_type TEXT NOT NULL,                            -- Libur Nasional|Cuti Bersama|Ramadan|Hari Besar
    source_url TEXT
);
CREATE TABLE IF NOT EXISTS ref.ref_wilayah (
    province_name TEXT NOT NULL, city_name TEXT NOT NULL,
    region_type TEXT NOT NULL,                             -- Kota | Kabupaten
    island TEXT, bps_code TEXT,
    PRIMARY KEY (province_name, city_name)
);
