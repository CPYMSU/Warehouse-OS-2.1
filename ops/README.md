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
- `.github/workflows/production-deploy.yml` rejects stale revisions and then
  serially deploys the Mac primary before the Vultr standby.
- `.github/workflows/production-deploy-target.yml` is the shared target job. It
  compares the clean checkout with each target's own active manifest, packages
  an immutable release only when required and invokes `ops/deploy smart`.
- The Mac target joins Tailscale as an ephemeral tagged node. It does not use a
  self-hosted runner, which would be inappropriate for this public repository.

Both the `mac-production` and `production` GitHub Environments define the same
target contract:

```text
Variables:
  WAREHOUSE_DEPLOY_HOST
  WAREHOUSE_DEPLOY_USER
  WAREHOUSE_REMOTE_DEPLOY_MANAGER
  WAREHOUSE_DEPLOY_INCOMING
  WAREHOUSE_DEPLOY_MANAGER_SUDO
  WAREHOUSE_DEPLOY_PREPARE_INCOMING
  WAREHOUSE_DEPLOY_SCP_LEGACY

Secrets:
  WAREHOUSE_DEPLOY_SSH_KEY
  WAREHOUSE_DEPLOY_KNOWN_HOSTS
```

The existing `production` environment remains the Vultr standby and keeps
`WAREHOUSE_DEPLOY_MANAGER_SUDO=1`,
`WAREHOUSE_DEPLOY_PREPARE_INCOMING=1` and
`WAREHOUSE_DEPLOY_SCP_LEGACY=0`. The `mac-production` environment uses:

```text
WAREHOUSE_DEPLOY_HOST=<Mac mini Tailscale IPv4 or MagicDNS name>
WAREHOUSE_DEPLOY_USER=<restricted Mac deployment user>
WAREHOUSE_REMOTE_DEPLOY_MANAGER=/Users/<user>/Server/bonfirework/bin/warehouse-deploy
WAREHOUSE_DEPLOY_INCOMING=/Users/<user>/Server/bonfirework/incoming
WAREHOUSE_DEPLOY_MANAGER_SUDO=0
WAREHOUSE_DEPLOY_PREPARE_INCOMING=0
WAREHOUSE_DEPLOY_SCP_LEGACY=1
```

`mac-production` additionally requires `TAILSCALE_AUTHKEY`, created as a
reusable, ephemeral, pre-approved key owned by a deployment-only tag. The
tailnet policy should allow that tag to reach only the Mac mini on TCP 22.

The Mac public key must be installed with a forced command so that the Action
cannot open a shell or forward ports:

```text
restrict,command="/Users/<user>/Server/bonfirework/actions/warehouse-deploy-ssh-gate" ssh-ed25519 AAAA...
```

The gate permits only immutable release upload plus `manifest`, `install`,
`status`, `history` and `rollback`. GitHub uses legacy SCP only for this
channel so the forced command can validate the exact upload operation.

The deployment workflow refuses stale queued commits, serializes production
changes and requires each target's active manifest.
`WAREHOUSE_DEPLOY_LOCAL_VALIDATION` is fixed to `basic`, so GitHub never runs
the standard/full pytest lanes or `ops/run-full-verification`. Both target
managers independently recompute the smart plan before installing anything.

Each deploy uploads a checksummed archive, verifies every file, builds a tagged
image and starts the inactive API slot. Nginx switches only after candidate
health, OpenAPI, WebAuthn RP and Alembic checks succeed. The former slot stays
running, making `rollback` an upstream switch rather than a rebuild.

Database migrations must remain expand/contract compatible: application
rollback never attempts an automatic database downgrade. Standard and full
deployments create a verified PostgreSQL custom-format backup before starting
the candidate.
