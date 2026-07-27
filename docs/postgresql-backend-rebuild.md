# PostgreSQL backend rebuild brief

## Boundary

Warehouse OS 2.1 retains the client applications and deliberately starts with
no inherited application server or database. The legacy `/api/...` calls are an
interface inventory, not an implementation to copy.

## Target

- PostgreSQL is the sole system-of-record database.
- A new versioned API replaces the legacy `/api/...` implementation, with a
  compatibility layer only where the retained frontend needs a staged migration.
- Authentication, tenant isolation, authorization, audit events, and migrations
  are designed before inventory, ERP, collaboration, and AI features.
- Every schema change is versioned and applied through migrations; application
  code does not create or alter production tables at runtime.

## First implementation slice

1. Establish the service runtime, configuration validation, health checks, and
   a local PostgreSQL development environment.
2. Implement migrations for tenants, users, roles, memberships, sessions, and
   immutable audit events.
3. Publish an OpenAPI contract for authentication, the bootstrap payload, and
   tenant selection; point the web application at that versioned contract.
4. Add warehouses, locations, product catalog, inventory balances, and
   append-only stock movements with database constraints and transactional tests.
5. Bring in purchasing, outbound operations, ERP, reporting, collaboration, and
   AI workflows one bounded module at a time.

## Decisions still needed

- Backend runtime and API framework.
- Authentication provider and token/session model.
- Whether existing production data requires a one-time migration or Warehouse
  OS 2.1 starts empty.
- Hosting, backups, retention period, and recovery objectives.

Until those decisions are made, this repository intentionally contains no
placeholder tables or ORM models that could become accidental production design.
