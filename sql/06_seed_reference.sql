-- 06_seed_reference.sql : mengisi tabel referensi (aturan pemetaan)
-- Idempotent: aman dijalankan berulang (ON CONFLICT DO NOTHING).
-- Nilai ini diturunkan dari data sumber; definisi 'is_preventable' adalah USULAN yang perlu disetujui.

-- 1) Status pesanan (dicocokkan dengan LIKE)
INSERT INTO ref.ref_status_map (raw_pattern, status_std, is_final) VALUES
 ('Selesai',        'Selesai',        TRUE),
 ('Batal',          'Batal',          TRUE),
 ('Sedang Dikirim', 'Sedang Dikirim', FALSE),
 ('Telah Dikirim',  'Telah Dikirim',  FALSE),
 ('Pesanan diterima, namun Pembeli masih dapat mengajukan pengembalian%', 'Masa Retur', FALSE)
ON CONFLICT DO NOTHING;

-- 2) Metode pembayaran
INSERT INTO ref.ref_payment_map (raw_text, payment_group) VALUES
 ('COD (Bayar di Tempat)','COD'),
 ('Saldo ShopeePay','E-Wallet'),
 ('SPayLater','PayLater'),
 ('Online Payment','Transfer'),
 ('SeaBank Bayar Instan','Transfer'),
 ('BCA OneKlik','Transfer'),
 ('Kartu Kredit/Debit','Kartu'),
 ('Cicilan Kartu Kredit','Kartu'),
 ('Indomaret/i.Saku','Gerai'),
 ('Alfamart/Alfamidi/Dan+Dan','Gerai'),
 ('Pembayaran dibebaskan','Lainnya'),
 ('Mitra Shopee','Lainnya')
ON CONFLICT DO NOTHING;

-- 3) Alasan pembatalan: 18 teks mentah -> alasan baku, kelompok, pelaku, dan penanda dapat dicegah
INSERT INTO ref.ref_cancel_reason_map (raw_text, actor, reason_std, reason_group, is_preventable) VALUES
 ('Dibatalkan oleh Pembeli. Alasan: Lainnya', 'Pembeli', 'Lainnya', 'Lainnya', FALSE),
 ('Dibatalkan oleh Pembeli. Alasan: Lainnya/ berubah pikiran', 'Pembeli', 'Berubah Pikiran', 'Keputusan Pembeli', FALSE),
 ('Dibatalkan oleh Pembeli. Alasan: Menemukan yang lebih murah', 'Pembeli', 'Menemukan Lebih Murah', 'Keputusan Pembeli', FALSE),
 ('Dibatalkan oleh Pembeli. Alasan: Need to change delivery address', 'Pembeli', 'Ubah Alamat', 'Perubahan Pesanan', FALSE),
 ('Dibatalkan oleh Pembeli. Alasan: Penjual tidak responsif terhadap pertanyaan Pembeli', 'Pembeli', 'Penjual Tidak Responsif', 'Layanan Penjual', TRUE),
 ('Dibatalkan oleh Pembeli. Alasan: Perlu mengubah Voucher', 'Pembeli', 'Ubah Voucher', 'Perubahan Pesanan', FALSE),
 ('Dibatalkan oleh Pembeli. Alasan: Perlu mengubah alamat pengiriman', 'Pembeli', 'Ubah Alamat', 'Perubahan Pesanan', FALSE),
 ('Dibatalkan oleh Pembeli. Alasan: Perlu mengubah pesanan', 'Pembeli', 'Ubah Pesanan', 'Perubahan Pesanan', FALSE),
 ('Dibatalkan oleh Pembeli. Alasan: Proses pembayaran sulit', 'Pembeli', 'Kesulitan Pembayaran', 'Pembayaran', FALSE),
 ('Dibatalkan oleh Pembeli. Alasan: Tidak ingin membeli lagi', 'Pembeli', 'Berubah Pikiran', 'Keputusan Pembeli', FALSE),
 ('Dibatalkan oleh Pembeli. Alasan: Ubah Pesanan yang Ada', 'Pembeli', 'Ubah Pesanan', 'Perubahan Pesanan', FALSE),
 ('Dibatalkan oleh Penjual. Alasan: Produk habis', 'Penjual', 'Produk Habis', 'Layanan Penjual', TRUE),
 ('Dibatalkan secara otomatis oleh sistem. Alasan: Lainnya', 'Sistem', 'Lainnya', 'Lainnya', FALSE),
 ('Dibatalkan secara otomatis oleh sistem. Alasan: Paket hilang di perjalanan. Kompensasi yang memenuhi syarat telah dikreditkan ke Saldo Penjual-mu.', 'Sistem', 'Paket Hilang', 'Pengiriman', FALSE),
 ('Dibatalkan secara otomatis oleh sistem. Alasan: Pengiriman gagal', 'Sistem', 'Pengiriman Gagal', 'Pengiriman', FALSE),
 ('Dibatalkan secara otomatis oleh sistem. Alasan: Penjual gagal mengirimkan pesanan tepat waktu', 'Sistem', 'Penjual Terlambat Kirim', 'Layanan Penjual', TRUE),
 ('Dibatalkan secara otomatis oleh sistem. Alasan: Penjual tidak mengatur pengiriman tepat waktu', 'Sistem', 'Penjual Terlambat Kirim', 'Layanan Penjual', TRUE),
 ('Dibatalkan secara otomatis oleh sistem. Alasan: Pesanan belum dibayar', 'Sistem', 'Belum Dibayar', 'Pembayaran', FALSE)
ON CONFLICT DO NOTHING;
