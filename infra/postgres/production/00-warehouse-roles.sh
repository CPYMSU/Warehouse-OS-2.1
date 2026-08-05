#!/bin/sh
set -eu

: "${WAREHOUSE_API_DB_PASSWORD:?required}"
: "${WAREHOUSE_MIGRATOR_DB_PASSWORD:?required}"

psql --set=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=api_password="$WAREHOUSE_API_DB_PASSWORD" \
  --set=migrator_password="$WAREHOUSE_MIGRATOR_DB_PASSWORD" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;

SELECT format(
  'CREATE ROLE warehouse_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION PASSWORD %L',
  :'migrator_password'
) WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'warehouse_migrator')
\gexec

SELECT format(
  'CREATE ROLE warehouse_os LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION PASSWORD %L',
  :'api_password'
) WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'warehouse_os')
\gexec

REVOKE CREATE ON DATABASE warehouse_os FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE warehouse_os TO warehouse_migrator, warehouse_os;
GRANT CREATE ON DATABASE warehouse_os TO warehouse_migrator;

CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION warehouse_migrator;
SQL
