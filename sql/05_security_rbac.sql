-- 05_security_rbac.sql : Role-Based Access Control dengan prinsip least privilege
-- Role grup (NOLOGIN) menyimpan hak akses; user login hanya menjadi anggota role grup.
-- User dan password dibuat oleh sql/90_create_users.sh dari variabel lingkungan (.env), bukan ditulis di sini.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='role_data_engineer') THEN CREATE ROLE role_data_engineer NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='role_data_steward')  THEN CREATE ROLE role_data_steward  NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='role_data_analyst')  THEN CREATE ROLE role_data_analyst  NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='role_store_owner')   THEN CREATE ROLE role_store_owner   NOLOGIN; END IF;
END $$;

-- Cabut akses default
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA stg, ref, dw, mart, etl FROM PUBLIC;

-- Data Engineer : menjalankan ETL, menulis stg/dw/etl, membaca ref
GRANT USAGE, CREATE ON SCHEMA stg, dw, etl, mart TO role_data_engineer;
GRANT USAGE ON SCHEMA ref TO role_data_engineer;
GRANT ALL ON ALL TABLES IN SCHEMA stg, dw, etl TO role_data_engineer;
GRANT SELECT ON ALL TABLES IN SCHEMA ref, mart TO role_data_engineer;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA stg, dw, etl TO role_data_engineer;

-- Data Steward : merawat aturan pemetaan (ref) dan memantau etl_log / etl_reject
GRANT USAGE ON SCHEMA ref, etl, dw, mart TO role_data_steward;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA ref TO role_data_steward;
GRANT SELECT ON ALL TABLES IN SCHEMA etl, dw, mart TO role_data_steward;

-- Data Analyst / Dashboard : hanya baca schema mart
GRANT USAGE ON SCHEMA mart TO role_data_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO role_data_analyst;

-- Pemilik toko : hanya baca schema mart (sama dengan analyst; dipisah agar bisa dibedakan di audit)
GRANT USAGE ON SCHEMA mart TO role_store_owner;
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO role_store_owner;

-- View baru di mart otomatis dapat dibaca analyst dan owner
ALTER DEFAULT PRIVILEGES IN SCHEMA mart GRANT SELECT ON TABLES TO role_data_analyst, role_store_owner, role_data_steward;
