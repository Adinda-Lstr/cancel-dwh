-- 01_schemas.sql : lapisan data warehouse
-- stg  = staging (salinan mentah)      ref  = tabel referensi & aturan pemetaan
-- dw   = galaxy schema                 mart = view KPI untuk dashboard
-- etl  = log, reject, dan audit trail proses
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS ref;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS etl;
