#!/bin/bash
# 90_create_users.sh : membuat user login dan memasukkannya ke role grup.
# Password dibaca dari variabel lingkungan (file .env), tidak pernah ditulis di repo.
set -euo pipefail

: "${DWH_ENGINEER_PASSWORD:?DWH_ENGINEER_PASSWORD belum diisi di .env}"
: "${DWH_STEWARD_PASSWORD:?DWH_STEWARD_PASSWORD belum diisi di .env}"
: "${DWH_ANALYST_PASSWORD:?DWH_ANALYST_PASSWORD belum diisi di .env}"
: "${DWH_OWNER_PASSWORD:?DWH_OWNER_PASSWORD belum diisi di .env}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v eng_pw="$DWH_ENGINEER_PASSWORD" -v stw_pw="$DWH_STEWARD_PASSWORD" \
  -v ana_pw="$DWH_ANALYST_PASSWORD"  -v own_pw="$DWH_OWNER_PASSWORD" <<'SQL'
CREATE ROLE etl_user      LOGIN PASSWORD :'eng_pw' IN ROLE role_data_engineer;
CREATE ROLE steward_user  LOGIN PASSWORD :'stw_pw' IN ROLE role_data_steward;
CREATE ROLE dashboard_user LOGIN PASSWORD :'ana_pw' IN ROLE role_data_analyst;
CREATE ROLE owner_user    LOGIN PASSWORD :'own_pw' IN ROLE role_store_owner;
SQL
echo "User login dibuat: etl_user, steward_user, dashboard_user, owner_user"
