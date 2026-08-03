# Warehouse OS deployment control plane

The deployment and database channels are deliberately separate:

- `warehouse-sync` can only forward local TCP `55432` to server PostgreSQL
  `5432`.
- `warehouse-deploy` can upload release archives and invoke the root-owned,
  argument-validating release manager through one sudo command.

The deploy key cannot forward ports, start a PTY, read production secrets or
run arbitrary root commands.

## Commands

```bash
ops/deploy smart
ops/deploy quick
ops/deploy standard
ops/deploy full
ops/deploy status
ops/deploy history
ops/deploy rollback
```

The root-owned release manager also exposes one host-specific, idempotent data
disk command through the restricted deployment channel:

```bash
ssh warehouse-deploy@HOST 'sudo -n /usr/local/sbin/warehouse-deploy init-data-disk'
ssh warehouse-deploy@HOST 'sudo -n /usr/local/sbin/warehouse-deploy benchmark-data-disk'
```

It only accepts an empty 40 GiB `/dev/vdb`, creates one GPT partition with an
`ext4` filesystem labelled `warehouse-data`, mounts it at
`/mnt/warehouse-data`, and adds a UUID-based `nofail` entry to `/etc/fstab`.
Any unexpected device size, partition layout, filesystem, label, mount, or
existing `fstab` entry causes the command to stop without replacing it.
The benchmark command is pinned to the initialized filesystem UUID and performs
one bounded 1 GiB direct-I/O sequential write/read test before removing its
temporary file.

`smart` is the default release lane. It compares the exact candidate tree with
the active server manifest, discovers affected tests through the Python import
graph and lets the trusted server planner independently confirm the lane.
Unknown changes fail closed to `full`. Explicit `quick`, `standard` and `full`
remain available as operator overrides.

## GitHub production deployment

`.github/workflows/production-deploy.yml` runs the same `smart` contract for
every deployable push to `main` and for manual dispatches. The `production`
GitHub Environment must define:

```text
Variables:
  WAREHOUSE_DEPLOY_HOST
  WAREHOUSE_DEPLOY_USER
  WAREHOUSE_REMOTE_DEPLOY_MANAGER

Secrets:
  WAREHOUSE_DEPLOY_SSH_KEY
  WAREHOUSE_DEPLOY_KNOWN_HOSTS
```

The workflow refuses stale queued commits, serializes production changes,
requires the active manifest, uses a disposable PostgreSQL 18 service for full
integration verification and uploads the plan plus deployment log as evidence.
The SSH key remains the same restricted, no-PTY deployment identity; it does
not grant a general server shell or access to production secrets.

The disposable database uses separate migration and application identities;
the runner refuses an application role with `SUPERUSER` or `BYPASSRLS`. CI
environments that provide a database must set both
`WAREHOUSE_TEST_DATABASE_URL` (restricted application role) and
`WAREHOUSE_TEST_MIGRATION_DATABASE_URL` (schema owner), plus
`WAREHOUSE_TEST_HOSTED_DATABASE_ADMIN_URL` for disposable workspace database
and role provisioning. The hosted-database administrator is used only inside
the disposable CI PostgreSQL service and is never forwarded to production.

Each deploy uploads a checksummed archive, verifies every file, builds a tagged
image and starts the inactive API slot. Nginx switches only after candidate
health, OpenAPI, WebAuthn RP and Alembic checks succeed. The former slot stays
running, making `rollback` an upstream switch rather than a rebuild.

Database migrations must remain expand/contract compatible: application
rollback never attempts an automatic database downgrade. Standard and full
deployments create a verified PostgreSQL custom-format backup before starting
the candidate.
