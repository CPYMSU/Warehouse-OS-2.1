# Warehouse OS deployment control plane

The deployment and database channels are deliberately separate. Web/API
containers never run Alembic and never receive the migration DSN:

- `warehouse-sync` can only forward local TCP `55432` to server PostgreSQL
  `5432`.
- `warehouse-deploy` can upload release archives and invoke the root-owned,
  argument-validating release manager through one sudo command.

The deploy key cannot forward ports, start a PTY, read production secrets or
run arbitrary root commands.

## Mac portable storage

Preflight a dedicated mirrored data volume before moving either PostgreSQL
cluster:

```bash
ops/storage/macos-storage check
ops/storage/macos-storage plan
```

The guard refuses the internal system disk, non-`/Volumes` paths, unknown RAID
protection, and undersized targets. See
`docs/macos-portable-storage.zh-TW.md` for the maintenance-window procedure.

## Commands

```bash
ops/deploy smart
ops/deploy quick
ops/deploy standard
ops/deploy full
ops/deploy status
ops/deploy history
ops/deploy rollback
ops/deploy migration-start RELEASE
ops/deploy migration-status RELEASE
ops/deploy migration-wait RELEASE
ops/deploy migration-reconcile RELEASE
```

The dual-node PostgreSQL control plane is intentionally separate from release
deployment:

```bash
ops/cluster/configure-control-publication
ops/cluster/configure-hosted-publications
ops/cluster/reconcile-hosted-databases-macos
ops/cluster/initialize-hosted-subscriber-macos
ops/cluster/sync-sequences-macos all
ops/cluster/set-macos-write-policy standby
ops/cluster/verify-replication-macos
ops/cluster/verify-nodes.py --inventory ops/cluster/nodes.json
```

The reconciler mirrors newly provisioned hosted database topology and schema,
while each database receives its own logical subscription. It refuses local-
only databases and schema drift, and never rebuilds a subscribed database.
Logical replication does not copy DDL or sequence state. The detached database
controller applies standby-safe schema revisions first, then runs the verified
primary backup/data phase and waits for replication before activation.
Sequence levels are synchronized at cutover. See
`docs/database-migration-controller.md`.

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
- `.github/workflows/production-deploy.yml` rejects stale revisions and invokes
  the single coordinated `ops/cluster/rolling-deploy` route.
- `ops/fast-deploy` lets any authenticated computer dispatch and watch that
  workflow without receiving server SSH keys.
- The production job uses the dedicated Mac mini runner labels
  `self-hosted`, `macOS`, `ARM64` and `warehouse-production`. GitHub remains the
  scheduler and audit UI; all checkout, planning, packaging and deployment
  compute runs on the Mac mini.
- Pull-request workflows remain on GitHub-hosted runners and must never request
  the `warehouse-production` label. The production runner accepts only the
  `main` push/dispatch workflow and its Environments are restricted to `main`.

The runner invokes the Mac manager through local transport and the Vultr
manager through its existing restricted SSH identity. Those credentials live
only on the runner host; GitHub and dispatching terminals never receive them.

The existing Mac forced-command key remains available for audited operator
access, but GitHub Actions no longer depends on it:

```text
restrict,command="/Users/<user>/Server/bonfirework/actions/warehouse-deploy-ssh-gate" ssh-ed25519 AAAA...
```

The gate permits only immutable release upload plus the fixed release and
database-controller status commands; it never permits arbitrary SQL or a
general shell.

The deployment workflow refuses stale queued commits, serializes production
changes and requires each target's active manifest.

The Mac mini also runs `warehouse-clash-route-optimizer` every five minutes.
It probes only Singapore routes against Cloudflare, applies hysteresis before
switching, reconnects the Tunnel, and automatically restores the former route
if the public health check fails. See `docs/clash-route-optimizer.md`.
The workflow fixes the activation preflight to `basic`, so GitHub never reruns
the standard/full pytest lanes or `ops/run-full-verification`. Both target
managers independently recompute the smart plan before installing anything.

Each deploy uploads a checksummed archive, verifies every file and builds a
tagged image. Database jobs finish before the inactive API slot is eligible for
activation. Nginx switches only after candidate health, OpenAPI and schema
gates succeed. The former slot stays running, making `rollback` an upstream
switch rather than a rebuild.

Database migrations must remain expand/contract compatible: application
rollback never attempts an automatic database downgrade. The background
primary controller, not the deploy process, creates and verifies the
PostgreSQL custom-format backup before changing schema or data.
