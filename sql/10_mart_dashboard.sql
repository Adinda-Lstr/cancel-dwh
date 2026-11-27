-- 10_mart_dashboard.sql : view tambahan untuk dashboard (kategori terfilter, jejak ETL, hasil validasi)
-- Dashboard tetap hanya membaca schema mart; view ini membuka jejak audit tanpa membuka schema etl/dw.
-- Aman dijalankan berulang.

-- 1) Order x kategori produk (FAKTA KEDUA) dengan atribut untuk filter dashboard ---------------------
CREATE OR REPLACE VIEW mart.v_order_category_flat AS
SELECT c.order_month, pc.category_name,
       p.payment_name, p.payment_group,
       l.province_name, e.event_category,
       c.allocated_orders, c.allocated_payment, c.allocated_est_hilang,
       c.is_cancelled
FROM dw.fact_order_category c
JOIN dw.dim_product_category pc ON pc.category_key = c.category_key
JOIN dw.dim_payment p           ON p.payment_key   = c.payment_key
JOIN dw.dim_location l          ON l.location_key  = c.location_key
JOIN dw.dim_event e             ON e.event_key     = c.event_key;

-- 2) Riwayat proses ETL (audit trail) ------------------------------------------------------------
CREATE OR REPLACE VIEW mart.v_etl_runs AS
SELECT b.batch_id, b.started_at, b.finished_at,
       round(extract(epoch FROM (b.finished_at - b.started_at))::numeric, 1) AS durasi_detik,
       b.triggered_by, b.status,
       max(l.rows_loaded)   FILTER (WHERE l.target_table = 'dw.fact_order') AS order_dimuat,
       sum(l.rows_rejected) FILTER (WHERE l.step = 'transform')            AS baris_ditolak,
       count(*)             FILTER (WHERE l.status = 'WARNING')            AS peringatan
FROM etl.etl_batch b
LEFT JOIN etl.etl_log l ON l.batch_id = b.batch_id
GROUP BY b.batch_id, b.started_at, b.finished_at, b.triggered_by, b.status;

-- 3) Hasil validasi terakhir (ditulis oleh python -m etl.validate; satu proses = satu penanda di source_file)
CREATE OR REPLACE VIEW mart.v_validation_latest AS
SELECT l.batch_id, l.logged_at,
       split_part(l.message, ' | ', 1) AS lapisan,
       split_part(l.message, ' | ', 2) AS pemeriksaan,
       split_part(l.message, ' | ', 3) AS acuan_csv,
       split_part(l.message, ' | ', 4) AS aktual,
       CASE l.status WHEN 'SUCCESS' THEN 'LULUS' ELSE 'GAGAL' END AS hasil
FROM etl.etl_log l
WHERE l.step = 'validate'
  AND l.message LIKE '% | % | % | %'
  AND l.source_file = (SELECT source_file FROM etl.etl_log
                       WHERE step = 'validate' AND source_file LIKE 'validate-%'
                       ORDER BY log_id DESC LIMIT 1);

GRANT USAGE ON SCHEMA mart TO role_data_analyst, role_store_owner, role_data_steward, role_data_engineer;
GRANT SELECT ON ALL TABLES IN SCHEMA mart
      TO role_data_analyst, role_store_owner, role_data_steward, role_data_engineer;
