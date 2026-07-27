# Local Mac runtime and Cloudflare Tunnel

## Intended boundary

```text
Cloudflare Access + WAF
  -> api-dev.bonfirework.org
  -> Cloudflare Tunnel (outbound-only from this Mac)
  -> 127.0.0.1:8080 FastAPI
  -> 127.0.0.1:5432 PostgreSQL 18 + pgvector
```

The root `bonfirework.org` website is not changed. Use the dedicated API subdomain
until the service is stable. PostgreSQL must remain bound to loopback only.

## One-time local preparation

```sh
brew install cloudflared
cd /Users/peiyuancai/Desktop/Warehouse-OS-2.1/backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
```

Install PostgreSQL 18 and pgvector for the native Mac runtime:

```sh
brew install postgresql@18 pgvector
brew services stop postgresql@16
brew services start postgresql@18
/opt/homebrew/opt/postgresql@18/bin/createdb warehouse_os
/opt/homebrew/opt/postgresql@18/bin/psql -d warehouse_os -c 'CREATE EXTENSION vector'
/opt/homebrew/opt/postgresql@18/bin/createuser --pwprompt --no-superuser --no-createdb --no-createrole warehouse_migrator
/opt/homebrew/opt/postgresql@18/bin/createuser --pwprompt --no-superuser --no-createdb --no-createrole warehouse_os
/opt/homebrew/opt/postgresql@18/bin/psql -d postgres -c 'GRANT CREATE ON DATABASE warehouse_os TO warehouse_migrator'
/opt/homebrew/opt/postgresql@18/bin/psql -d warehouse_os -c 'CREATE SCHEMA app AUTHORIZATION warehouse_migrator'
```

Alternatively, `docker compose up -d postgres` starts the pinned PostgreSQL 18
+ pgvector image. Its development password is `local-only-change-me`, matching
`backend/.env.example`. Change it before any non-local use. Set
`WAREHOUSE_DATABASE_URL` in `backend/.env` to the selected local PostgreSQL 18
instance, set `WAREHOUSE_MIGRATION_DATABASE_URL` to the migration role, then run
`alembic upgrade head`. The API role must never be a superuser or have
`BYPASSRLS`.

## Cloudflare publication

1. Authenticate the connector: `cloudflared tunnel login`.
2. Create a named tunnel: `cloudflared tunnel create warehouse-os-dev`.
3. Copy `cloudflared/config.example.yml` to `~/.cloudflared/config.yml` and replace
   the tunnel UUID.
4. Create the DNS route: `cloudflared tunnel route dns warehouse-os-dev api-dev.bonfirework.org`.
5. Run the connector: `cloudflared tunnel run warehouse-os-dev`.
6. In Cloudflare Zero Trust, protect `api-dev.bonfirework.org` with Access before
   sharing it. Add WAF and rate-limit rules as well.

Do not publish the API before `WAREHOUSE_ENVIRONMENT=production`, a unique JWT
secret, an application database role without `BYPASSRLS`, backups, and Access
policy are configured.
