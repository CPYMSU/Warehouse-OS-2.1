-- This file runs only when Compose initializes an empty development volume.
-- warehouse_admin is the container bootstrap superuser; the API never uses it.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE ROLE warehouse_migrator
  LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION
  PASSWORD 'local-only-migration-change-me';
CREATE ROLE warehouse_os
  LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION
  PASSWORD 'local-only-change-me';

REVOKE CREATE ON DATABASE warehouse_os FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE warehouse_os TO warehouse_migrator, warehouse_os;
GRANT CREATE ON DATABASE warehouse_os TO warehouse_migrator;
CREATE SCHEMA app AUTHORIZATION warehouse_migrator;
