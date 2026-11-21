-- 08_seed_calendar.sql : kalender hari libur dan event (data eksternal E1 dan E2)
-- SEMUA tanggal diambil dari sumber resmi pada kolom source_url, bukan dari ingatan.
--   Libur nasional dan cuti bersama : SKB 3 Menteri (Kemenko PMK / Setkab)
--       2023: SKB 1066/2022, 3/2022, 3/2022 (hanya Desember 2023 yang dipakai, sesuai rentang data)
--       2024: SKB 855/2023, 3/2023, 4/2023      2025: SKB 1017/2024, 2/2024, 2/2024
--   Awal Ramadan : penetapan sidang isbat Kemenag (1 Ramadan 1445 H = 12 Mar 2024; 1446 H = 1 Mar 2025).
--       Akhir Ramadan = sehari sebelum 1 Syawal (Idul Fitri) menurut SKB: DITURUNKAN, bukan dikutip.
--   Libur Lebaran = DEFINISI rancangan: dari hari pertama Idul Fitri/cuti bersama Idul Fitri sampai hari terakhir
--       cuti bersama Idul Fitri pada SKB. Jendela 2025 (31 Mar-7 Apr) menghasilkan 116 order, sama dengan UTS.
-- Idempotent: aman dijalankan berulang; koreksi tanggal cukup mengubah file ini lalu menjalankannya lagi.

INSERT INTO ref.ref_holiday (holiday_date, holiday_name, holiday_type, source_url) VALUES
 ('2023-12-25', 'Hari Raya Natal', 'Libur Nasional', 'https://kemenkopmk.go.id/node/3188'),
 ('2023-12-26', 'Cuti Bersama Hari Raya Natal', 'Cuti Bersama', 'https://kemenkopmk.go.id/node/3188'),
 ('2024-01-01', 'Tahun Baru 2024 Masehi', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-02-08', 'Isra Mikraj Nabi Muhammad SAW', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-02-09', 'Cuti Bersama Tahun Baru Imlek', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-02-10', 'Tahun Baru Imlek 2575 Kongzili', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-03-11', 'Hari Suci Nyepi Tahun Baru Saka 1946', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-03-12', 'Cuti Bersama Hari Suci Nyepi', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-03-29', 'Wafat Isa Almasih', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-03-31', 'Hari Paskah', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-04-08', 'Cuti Bersama Idul Fitri 1445H', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-04-09', 'Cuti Bersama Idul Fitri 1445H', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-04-10', 'Hari Raya Idul Fitri 1445H', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-04-11', 'Hari Raya Idul Fitri 1445H', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-04-12', 'Cuti Bersama Idul Fitri 1445H', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-04-15', 'Cuti Bersama Idul Fitri 1445H', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-05-01', 'Hari Buruh Internasional', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-05-09', 'Kenaikan Isa Almasih', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-05-10', 'Cuti Bersama Kenaikan Isa Almasih', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-05-23', 'Hari Raya Waisak 2568 BE', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-05-24', 'Cuti Bersama Hari Raya Waisak', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-06-01', 'Hari Lahir Pancasila', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-06-17', 'Hari Raya Idul Adha 1445H', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-06-18', 'Cuti Bersama Idul Adha 1445H', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-07-07', 'Tahun Baru Islam 1446H', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-08-17', 'Hari Kemerdekaan RI', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-09-16', 'Maulid Nabi Muhammad SAW', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-12-25', 'Hari Raya Natal', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2024-12-26', 'Cuti Bersama Hari Raya Natal', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024'),
 ('2025-01-01', 'Tahun Baru 2025 Masehi', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-01-27', 'Isra Mikraj Nabi Muhammad SAW', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-01-28', 'Cuti Bersama Tahun Baru Imlek 2576', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-01-29', 'Tahun Baru Imlek 2576 Kongzili', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-03-28', 'Cuti Bersama Hari Suci Nyepi', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-03-29', 'Hari Suci Nyepi Tahun Baru Saka 1947', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-03-31', 'Idul Fitri 1446 Hijriah', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-04-01', 'Idul Fitri 1446 Hijriah', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-04-02', 'Cuti Bersama Idul Fitri 1446 Hijriah', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-04-03', 'Cuti Bersama Idul Fitri 1446 Hijriah', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-04-04', 'Cuti Bersama Idul Fitri 1446 Hijriah', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-04-07', 'Cuti Bersama Idul Fitri 1446 Hijriah', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-04-18', 'Wafat Yesus Kristus', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-04-20', 'Kebangkitan Yesus Kristus (Paskah)', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-05-01', 'Hari Buruh Internasional', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-05-12', 'Hari Raya Waisak 2569 BE', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-05-13', 'Cuti Bersama Hari Raya Waisak 2569 BE', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-05-29', 'Kenaikan Yesus Kristus', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-05-30', 'Cuti Bersama Kenaikan Yesus Kristus', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-06-01', 'Hari Lahir Pancasila', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-06-06', 'Idul Adha 1446 Hijriah', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-06-09', 'Cuti Bersama Idul Adha 1446 Hijriah', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-06-27', '1 Muharam Tahun Baru Islam 1447 Hijriah', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-08-17', 'Proklamasi Kemerdekaan', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-09-05', 'Maulid Nabi Muhammad SAW', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-12-25', 'Kelahiran Yesus Kristus', 'Libur Nasional', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025'),
 ('2025-12-26', 'Cuti Bersama Kelahiran Yesus Kristus', 'Cuti Bersama', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025')
ON CONFLICT (holiday_date) DO UPDATE SET holiday_name = EXCLUDED.holiday_name,
    holiday_type = EXCLUDED.holiday_type, source_url = EXCLUDED.source_url;

INSERT INTO ref.ref_event_calendar (event_name, event_category, start_date, end_date, source_url, verified) VALUES
 ('Ramadan 1445 H', 'Ramadan', '2024-03-12', '2024-04-09', 'https://setkab.go.id/pemerintah-tetapkan-1-ramadan-1445h-jatuh-pada-selasa-12-maret-2024/', TRUE),
 ('Ramadan 1446 H', 'Ramadan', '2025-03-01', '2025-03-30', 'https://www.detik.com/jabar/jabar-gaskeun/d-7800729/hasil-sidang-isbat-pemerintah-tetapkan-1-ramadhan-2025-jatuh-pada-1-maret', TRUE),
 ('Libur Lebaran 2024', 'Libur Lebaran', '2024-04-08', '2024-04-15', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2024', TRUE),
 ('Libur Lebaran 2025', 'Libur Lebaran', '2025-03-31', '2025-04-07', 'https://kemenkopmk.go.id/pemerintah-tetapkan-hari-libur-nasional-dan-cuti-bersama-tahun-2025', TRUE)
ON CONFLICT (event_name, start_date) DO UPDATE SET end_date = EXCLUDED.end_date,
    event_category = EXCLUDED.event_category, source_url = EXCLUDED.source_url, verified = EXCLUDED.verified;
