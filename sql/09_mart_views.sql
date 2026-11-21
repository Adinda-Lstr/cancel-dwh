-- 09_mart_views.sql : DATA MART "Pembatalan Order" (schema mart)
-- Dashboard hanya membaca view di sini (user dashboard_user tidak punya akses ke schema dw).
-- Semua view dibangun dari tabel fakta + dimensi di schema dw, jadi setiap angka dapat ditelusuri.
-- Aman dijalankan berulang (CREATE OR REPLACE).

-- 1) Detail per order, sudah digabung dengan dimensi (untuk filter bebas dan drill-down) ---------
CREATE OR REPLACE VIEW mart.v_order_flat AS
SELECT o.order_id,
       o.order_month,
       d.full_date                      AS order_date,
       d.year_num, d.month_num, d.month_name, d.day_name,
       d.is_weekend, d.is_holiday, d.holiday_name, d.is_payday, d.is_twin_date,
       t.hour_24, t.day_part,
       e.event_name, e.event_category,
       l.province_name, l.city_name, l.region_type,
       p.payment_name, p.payment_group,
       s.courier, s.service_name, s.service_class,
       st.status_name,
       cr.actor          AS cancel_actor,
       cr.reason_std     AS cancel_reason,
       cr.reason_group   AS cancel_reason_group,
       cr.is_preventable,
       o.total_qty, o.total_weight_gr, o.total_returned_qty, o.num_categories,
       o.total_pembayaran, o.est_revenue_hilang,
       o.is_cancelled, o.is_returned, o.is_problem_order, o.is_time_missing, o.is_weight_outlier,
       o.source_file, o.batch_id
FROM dw.fact_order o
JOIN dw.dim_date d             ON d.date_key = o.date_key
JOIN dw.dim_time t             ON t.time_key = o.time_key
JOIN dw.dim_event e            ON e.event_key = o.event_key
JOIN dw.dim_location l         ON l.location_key = o.location_key
JOIN dw.dim_payment p          ON p.payment_key = o.payment_key
JOIN dw.dim_shipping s         ON s.shipping_key = o.shipping_key
JOIN dw.dim_status st          ON st.status_key = o.status_key
JOIN dw.dim_cancel_reason cr   ON cr.cancel_reason_key = o.cancel_reason_key;

-- 2) KPI bulanan (kartu KPI dan tren) ---------------------------------------------------------
CREATE OR REPLACE VIEW mart.v_kpi_monthly AS
SELECT order_month,
       count(*)                                            AS total_orders,
       count(*) FILTER (WHERE is_cancelled)                AS cancelled_orders,
       round(100.0 * count(*) FILTER (WHERE is_cancelled) / count(*), 2) AS cancel_rate_pct,
       count(*) FILTER (WHERE is_returned)                 AS returned_orders,
       count(*) FILTER (WHERE is_problem_order)            AS problem_orders,
       sum(total_pembayaran)                               AS realized_revenue,
       sum(est_revenue_hilang)                             AS est_revenue_hilang,
       count(*) FILTER (WHERE is_time_missing)             AS time_missing_orders
FROM dw.fact_order
GROUP BY order_month;

-- 3) Alasan pembatalan (hanya order batal) ----------------------------------------------------
CREATE OR REPLACE VIEW mart.v_cancel_reason AS
SELECT o.order_month, cr.actor, cr.reason_std, cr.reason_group, cr.is_preventable,
       count(*)                  AS cancelled_orders,
       sum(o.est_revenue_hilang) AS est_revenue_hilang
FROM dw.fact_order o
JOIN dw.dim_cancel_reason cr ON cr.cancel_reason_key = o.cancel_reason_key
WHERE o.is_cancelled
GROUP BY o.order_month, cr.actor, cr.reason_std, cr.reason_group, cr.is_preventable;

-- 4) Metode pembayaran ------------------------------------------------------------------------
CREATE OR REPLACE VIEW mart.v_cancel_payment AS
SELECT o.order_month, p.payment_name, p.payment_group,
       count(*)                             AS total_orders,
       count(*) FILTER (WHERE o.is_cancelled) AS cancelled_orders,
       round(100.0 * count(*) FILTER (WHERE o.is_cancelled) / count(*), 2) AS cancel_rate_pct
FROM dw.fact_order o JOIN dw.dim_payment p ON p.payment_key = o.payment_key
GROUP BY o.order_month, p.payment_name, p.payment_group;

-- 5) Wilayah (provinsi -> kota/kabupaten untuk drill-down) ---------------------------------------
CREATE OR REPLACE VIEW mart.v_cancel_location AS
SELECT o.order_month, l.province_name, l.city_name, l.region_type,
       count(*)                             AS total_orders,
       count(*) FILTER (WHERE o.is_cancelled) AS cancelled_orders,
       round(100.0 * count(*) FILTER (WHERE o.is_cancelled) / count(*), 2) AS cancel_rate_pct
FROM dw.fact_order o JOIN dw.dim_location l ON l.location_key = o.location_key
GROUP BY o.order_month, l.province_name, l.city_name, l.region_type;

-- 6) Layanan pengiriman. 'Tidak Tercatat' = order batal sebelum kurir ditetapkan (diduga artefak data)
CREATE OR REPLACE VIEW mart.v_cancel_shipping AS
SELECT o.order_month, s.courier, s.service_class, s.service_name,
       count(*)                             AS total_orders,
       count(*) FILTER (WHERE o.is_cancelled) AS cancelled_orders,
       round(100.0 * count(*) FILTER (WHERE o.is_cancelled) / count(*), 2) AS cancel_rate_pct,
       round(avg(o.total_weight_gr) / 1000.0, 2) AS avg_weight_kg
FROM dw.fact_order o JOIN dw.dim_shipping s ON s.shipping_key = o.shipping_key
GROUP BY o.order_month, s.courier, s.service_class, s.service_name;

-- 7) Kategori produk: dari FAKTA KEDUA (fact_order_category), nilai dialokasikan agar tidak terhitung ganda
CREATE OR REPLACE VIEW mart.v_cancel_category AS
SELECT c.order_month, pc.category_name,
       round(sum(c.allocated_orders), 2)                                  AS alloc_orders,
       round(sum(c.allocated_orders) FILTER (WHERE c.is_cancelled), 2)    AS alloc_cancelled,
       round(100.0 * sum(c.allocated_orders) FILTER (WHERE c.is_cancelled)
             / NULLIF(sum(c.allocated_orders), 0), 2)                     AS cancel_rate_pct,
       sum(c.allocated_payment)                                           AS alloc_revenue,
       sum(c.allocated_est_hilang)                                        AS alloc_est_hilang
FROM dw.fact_order_category c
JOIN dw.dim_product_category pc ON pc.category_key = c.category_key
GROUP BY c.order_month, pc.category_name;

-- 8) Event vs hari biasa (DESKRIPTIF, bukan sebab-akibat). sample_note menandai jumlah order kecil --------
CREATE OR REPLACE VIEW mart.v_event_comparison AS
SELECT e.event_category, e.event_name,
       count(*)                                                    AS total_orders,
       count(*) FILTER (WHERE o.is_cancelled)                      AS cancelled_orders,
       round(100.0 * count(*) FILTER (WHERE o.is_cancelled) / count(*), 2) AS cancel_rate_pct,
       round(100.0 * count(*) FILTER (WHERE p.payment_group = 'COD') / count(*), 1) AS cod_share_pct,
       CASE WHEN count(*) < 150 THEN 'Sampel kecil (<150 order)' ELSE 'Sampel memadai' END AS sample_note
FROM dw.fact_order o
JOIN dw.dim_event e   ON e.event_key = o.event_key
JOIN dw.dim_payment p ON p.payment_key = o.payment_key
WHERE o.event_key <> -1
GROUP BY e.event_category, e.event_name;

-- 9) Faktor kalender: akhir pekan, hari libur, periode gajian (order dengan tanggal diketahui) ------
CREATE OR REPLACE VIEW mart.v_cancel_calendar AS
SELECT x.faktor, x.nilai, count(*) AS total_orders,
       count(*) FILTER (WHERE x.is_cancelled) AS cancelled_orders,
       round(100.0 * count(*) FILTER (WHERE x.is_cancelled) / count(*), 2) AS cancel_rate_pct
FROM (
    SELECT 'Akhir pekan' AS faktor, CASE WHEN d.is_weekend THEN 'Ya' ELSE 'Tidak' END AS nilai, o.is_cancelled
      FROM dw.fact_order o JOIN dw.dim_date d USING (date_key) WHERE o.date_key > 0
    UNION ALL
    SELECT 'Hari libur/cuti bersama', CASE WHEN d.is_holiday THEN 'Ya' ELSE 'Tidak' END, o.is_cancelled
      FROM dw.fact_order o JOIN dw.dim_date d USING (date_key) WHERE o.date_key > 0
    UNION ALL
    SELECT 'Periode gajian (tgl 25-3)', CASE WHEN d.is_payday THEN 'Ya' ELSE 'Tidak' END, o.is_cancelled
      FROM dw.fact_order o JOIN dw.dim_date d USING (date_key) WHERE o.date_key > 0
    UNION ALL
    SELECT 'Waktu pesan', t.day_part, o.is_cancelled
      FROM dw.fact_order o JOIN dw.dim_time t USING (time_key) WHERE o.time_key > 0
) x
GROUP BY x.faktor, x.nilai;

-- 10) Tren harian dari FAKTA KETIGA (snapshot). Hanya tanggal yang diketahui. -----------------------
CREATE OR REPLACE VIEW mart.v_daily_trend AS
SELECT d.full_date, d.year_num, d.month_num, d.day_name, d.is_holiday,
       sum(f.total_orders)      AS total_orders,
       sum(f.cancelled_orders)  AS cancelled_orders,
       round(100.0 * sum(f.cancelled_orders) / NULLIF(sum(f.total_orders), 0), 2) AS cancel_rate_pct
FROM dw.fact_daily_cancel_snapshot f
JOIN dw.dim_date d ON d.date_key = f.date_key
WHERE f.date_key > 0
GROUP BY d.full_date, d.year_num, d.month_num, d.day_name, d.is_holiday;

-- Hak akses: dashboard dan pemilik hanya membaca mart (least privilege) ---------------------------
GRANT USAGE ON SCHEMA mart TO role_data_analyst, role_store_owner, role_data_steward, role_data_engineer;
GRANT SELECT ON ALL TABLES IN SCHEMA mart
      TO role_data_analyst, role_store_owner, role_data_steward, role_data_engineer;
