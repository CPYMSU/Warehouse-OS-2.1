# Warehouse OS 2.1

Warehouse OS 2.1 begins as a clean separation of the user-facing products from
the legacy runtime. The frontend designs are preserved here while the backend
and data layer are rebuilt independently for PostgreSQL.

## Included frontend products

| Path | Product |
| --- | --- |
| `frontend/v2/` | Warehouse OS 2.0 web application (the current Swiss/Bonfire design system) |
| `frontend/` | Classic web application and mobile web variants |
| `mobile/` | React Native mobile application |
| `wechat-miniapp/` | WeChat Mini Program |
| `screenshots/` | Visual design references |

`frontend/v2/` is self-contained and includes its versioned browser assets and
precompiled bundles. Rebuild or verify the V2 bundles with:

```sh
node scripts/build_v2_frontend.cjs
node scripts/build_v2_frontend.cjs --check
```

The applications still call the former `/api/...` contract. That is intentional:
no legacy service code, SQLite databases, secrets, deployment configuration, or
database migrations were copied into this repository. The new API contract will
be implemented by the backend rewrite and backed exclusively by PostgreSQL.

See [the rebuild brief](docs/postgresql-backend-rebuild.md) for the proposed
starting boundary.
