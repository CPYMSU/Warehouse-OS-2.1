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

`smart` is the default local release lane. It compares the exact candidate tree
with the active server manifest, discovers affected tests through the Python
import graph and lets the trusted server planner independently confirm the
required safety checks. Unknown changes receive the conservative server lane.
Explicit `quick`, `standard` and `full` remain local operator commands.

## GitHub production deployment

GitHub automation is deliberately small because complete verification runs
locally before a Draft PR is created:

- `.github/workflows/backend-contract.yml` only compiles Python sources, checks
  shell syntax, verifies the committed frontend bundles and parses one sample
  deployment plan. It does not start PostgreSQL, install the backend, run
  pytest or build a Compose stack.
- `.github/workflows/production-deploy.yml` repeats the basic checks, packages
  the immutable release and invokes the restricted production deployment
  channel for each deployable push to `main` or manual dispatch.

The `production` GitHub Environment must define:

```text
Variables:
  WAREHOUSE_DEPLOY_HOST
  WAREHOUSE_DEPLOY_USER
  WAREHOUSE_REMOTE_DEPLOY_MANAGER

Secrets:
  WAREHOUSE_DEPLOY_SSH_KEY
  WAREHOUSE_DEPLOY_KNOWN_HOSTS
```

The deployment workflow refuses stale queued commits, serializes production
changes and requires the active manifest. `WAREHOUSE_DEPLOY_LOCAL_VALIDATION`
is fixed to `basic`, so GitHub never selects or runs the standard/full pytest
lanes or `ops/run-full-verification`. The impact plan is used only to skip
non-runtime changes and to tell the trusted server which backup and health
checks are required. The SSH key remains the same restricted, no-PTY
deployment identity; it does not grant a general server shell or access to
production secrets.

Each deploy uploads a checksummed archive, verifies every file, builds a tagged
image and starts the inactive API slot. Nginx switches only after candidate
health, OpenAPI, WebAuthn RP and Alembic checks succeed. The former slot stays
running, making `rollback` an upstream switch rather than a rebuild.

Database migrations must remain expand/contract compatible: application
rollback never attempts an automatic database downgrade. Standard and full
deployments create a verified PostgreSQL custom-format backup before starting
the candidate.
