# Warehouse OS 2.1 production deployment

## Runtime topology

- `https://bonfirework.org` terminates TLS at Nginx. A one-line upstream file
  atomically points traffic at the active FastAPI slot: blue on loopback port
  `18081` or green on `18082`.
- The SSD control PostgreSQL 18 stores platform state. A second PostgreSQL 18
  instance stores user-software databases under the mounted HDD. The internal
  research executor runs with Docker Compose. The API is managed as two
  independently versioned Docker slots by the deployment control plane.
- A single-purpose research executor consumes PostgreSQL-backed jobs on an
  internal-only Docker network. It has no public port or internet route and
  never receives the API container's JWT or integration secrets.
- PostgreSQL is the single writable primary and is bound only to
  `127.0.0.1:5432` on the server.
- The local development backend reaches that same primary through the
  restricted `warehouse-sync` SSH key and a LaunchAgent-managed local forward:
  `127.0.0.1:55432 -> server 127.0.0.1:5432`.
- This is live shared-primary connectivity, not unsafe bidirectional
  multi-primary replication. Writes made through either backend are committed
  to the same database and become visible to both after transaction commit.

## Production services

```text
docker.service
nginx.service
certbot.timer
warehouse-postgres-backup.timer
```

Inspect the application release channel from the project checkout:

```bash
ops/deploy status
ops/deploy history
```

Healthy production state includes `postgres`, `research-executor`, and two API
slots named `warehouse-os-api-blue` and `warehouse-os-api-green`. Only the
active slot receives public traffic; the other remains ready for immediate
rollback. Execution packages and verified artifacts live in the named
`warehouse-research-executions` volume; promoted artifacts are copied into the
ordinary content-addressed research asset store.

Production secrets live only in
`/opt/warehouse-os/shared/.env.production` with mode `0600`. Credential RTF
files and local environment backups are ignored by Git and excluded from
release archives.

## Fixed deployment channel

The database and deployment identities are intentionally separate. The
`warehouse-deploy` account accepts only its Ed25519 deployment key, has no PTY
or port forwarding, cannot read production secrets, and may invoke only the
root-owned argument-validating release manager. Root password access is an
emergency fallback, not part of routine deployment.

Run deployments from the repository root:

```bash
ops/deploy                 # defaults to smart
ops/deploy smart
ops/deploy quick
ops/deploy standard
ops/deploy full
ops/deploy rollback
ops/deploy storage-activate
ops/deploy hosted-db-activate
ops/deploy hosted-db-migrate
```

- `smart` compares the candidate tree with the active release manifest. A
  versioned impact policy establishes security and migration guardrails, while
  the Python reverse-import graph discovers the tests affected by application
  code. Documentation-only changes stop locally; unknown files receive the
  conservative server lane. The server independently recomputes the plan with
  the trusted active planner.
- `quick` rebuilds the frontend and runs contract tests. The server refuses it
  if migrations, dependencies, infrastructure, authentication, security,
  configuration, or tenant templates changed.
- `standard` runs the normal backend suite and creates a verified database
  backup before deployment.
- `full` additionally creates a disposable PostgreSQL 18 database, migrates it
  from zero, runs the complete integration suite, and verifies candidate
  restart recovery before switching traffic.

Smart deployments also avoid unrelated work: backups run only for changes that
can affect persistent data, OpenAPI/WebAuthn/storage probes run only for their
affected components, unchanged Browser/API images are reused where safe, and a
healthy Runtime Controller stays in service unless its code or contract
changed. Docker build context is allow-listed and the Python dependency layer
precedes documentation/frontend layers, so those changes retain the dependency
cache. The first release onto an older manager conservatively bootstraps through
the selected legacy lane; later releases use the active-manifest contract.

Every release is an immutable, checksummed archive with a per-file SHA-256
manifest and release metadata. The inactive slot must pass health, OpenAPI,
WebAuthn RP, and Alembic checks before Nginx switches. A public TLS smoke test
then runs; any failure restores the former upstream and removes the candidate.
Deployment and rollback events are recorded as JSON Lines on the server,
including `duration_seconds`. `ops/deploy history` therefore shows whether a
specific change class is getting slower instead of hiding all work behind one
total timeout.

## GitHub Actions deployment

Pull requests run syntax, generated-frontend and deployment-planner checks with
a five-minute ceiling. They do not install application dependencies, start
PostgreSQL, run pytest or build a Compose stack. Pushes to `main` use
`.github/workflows/production-deploy.yml`, which first deploys the Mac primary
through the `mac-production` Environment and then deploys the Vultr standby
through `production`. Both jobs run with read-only repository permissions and
share the target-neutral `.github/workflows/production-deploy-target.yml`.

The production workflow requests a dedicated Mac mini self-hosted runner with
the labels `self-hosted`, `macOS`, `ARM64` and `warehouse-production` for every
job. GitHub supplies scheduling and audit logs, while checkout, comparison,
packaging and deployment consume only Mac mini compute. Pull-request checks
stay on GitHub-hosted runners and never request the production label.
The runner host provides Homebrew Python 3.12–3.14 and Node.js 20 or newer
under `/opt/homebrew/bin`; production jobs reuse those installations instead
of downloading a fresh toolchain for every deployment.

The Mac-primary job uses the deploy client's `local` transport: the runner
invokes `/Users/<user>/Server/bonfirework/bin/warehouse-deploy` directly and
places the immutable archive in the local incoming directory. No Tailscale or
SSH credential is involved. After Mac health and the public endpoint pass, the
same runner executes the Vultr job over its existing restricted SSH channel.
Its known-hosts file is isolated under `RUNNER_TEMP`, so the job never replaces
the Mac user's personal SSH configuration.

The workflow refuses stale queued revisions, serializes the entire two-target
release and requires each node's live manifest. It fixes
`WAREHOUSE_DEPLOY_LOCAL_VALIDATION=basic`, so GitHub performs only Python
compilation, shell parsing, committed frontend-bundle verification, packaging
and deployment. Standard/full pytest and disposable-database verification are
local pre-Draft responsibilities and are never selected by GitHub. Each target
manager independently recomputes the impact plan and remains responsible for
checksummed extraction, required backups, candidate health, database revision
and automatic restoration on failure. Vultr is not updated unless the Mac
primary has already passed its target and public health checks.

## Hosted-data disk activation

The production storage channel requires `/dev/vdb1` to be mounted read-write
at `/mnt/warehouse-data` as ext4 with label `warehouse-data`. Activate it with:

```bash
ops/deploy storage-activate
```

Activation creates `hosted/digital-assets`, `hosted/runtime-volumes`,
`hosted/postgres-data` and `hosted/archive`, then additively copies the legacy
Docker object volume. It never deletes the legacy volume; releases mount that
volume read-only as a temporary fallback. Standard/full deployments repeat the
validation before starting a candidate.

Production mounts use the HDD for default code, all hosted object data and all
runtime-persistent volumes. The optional `warehouse-code-ssd` Docker volume is
used only for workspaces whose `code_storage=ssd` was explicitly selected.
The `warehouse-os-hosted-postgres` container has no public port and stores its
PGDATA on the HDD. Run `hosted-db-migrate` only after both blue and green API
slots understand the HDD provider; migration verifies legacy records before
atomically changing each binding and retains the SSD source for rollback.

The digital-asset guide and `dam.py` are packaged with the API release. A
documentation or command-contract change therefore requires an API deployment,
not only a static frontend upload. After switching traffic, verify both formal
downloads and the injected public base URL:

```bash
curl -fsS https://bonfirework.org/api/digital-assets/guide/download | shasum -a 256
curl -fsS https://bonfirework.org/api/digital-assets/cli | head -n 30
```

Rollback changes only the Nginx upstream and current-release symlink; it does
not rebuild an image or automatically downgrade the database. Migrations must
therefore follow expand/contract compatibility.

## Backups

`warehouse-postgres-backup.timer` backs up both PostgreSQL planes every night
at 02:30 UTC. The SSD control database remains a compressed custom-format dump
with a SHA-256 sidecar in `/opt/warehouse-os/backups`. The HDD hosted-database
cluster is exported as globals plus one independently restorable custom dump
per `whdb_*` workspace database, with a manifest and checksums in
`/mnt/warehouse-data/hosted/archive/database-backups`. Both retain 14 days.

Run and verify an immediate backup:

```bash
systemctl start warehouse-postgres-backup.service
systemctl status warehouse-postgres-backup.service
ls -lh /opt/warehouse-os/backups
find /mnt/warehouse-data/hosted/archive/database-backups -maxdepth 2 -type f -print
```

The fixed deployment channel can run the same backup and verify both checksum
sets without a general-purpose server shell:

```bash
ops/deploy backup-now
```

Hosted-database backup bytes are platform protection data and are not charged
to a workspace's logical quota. These backups protect against database
corruption and operator mistakes but remain on the same server and physical
HDD. Add an encrypted off-site copy before treating the deployment as
disaster-recovery complete.

## Local database tunnel

The macOS service definition is:

```text
~/Library/LaunchAgents/org.bonfire.warehouse-db-tunnel.plist
```

Check it with:

```bash
launchctl print gui/$(id -u)/org.bonfire.warehouse-db-tunnel
lsof -nP -iTCP:55432 -sTCP:LISTEN
```

The server-side key is restricted to TCP forwarding and may open only
`127.0.0.1:5432`; it cannot start a shell or forward arbitrary ports.
