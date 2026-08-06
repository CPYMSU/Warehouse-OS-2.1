# Pages Runtime

Pages Runtime gives every hosted workspace one stable platform URL while the
active release remains an immutable deployment pointer.

## Warehouse OS route

The default site key is the workspace key when that DNS label is globally
available:

```text
https://bonfirework.org/apps/workspace-key/
```

`platform.pages_routes` owns the globally unique site key and points to the
workspace's current healthy deployment. Activating or rolling back a release
updates this pointer in the same database transaction. The compatibility route
`/assets/{tenant_slug}/{workspace_key}/` remains available as an origin-health
and rollback path.

The `/apps/{site_key}/` response is a minimal Warehouse OS shell. It fills the
page with a sandboxed, cross-origin frame backed by the site's isolated Pages
runtime origin. The browser address bar therefore stays on the short Warehouse
OS URL while project code cannot read Warehouse OS LocalStorage or execute as
the signed-in management UI. Root-relative assets and APIs continue to work
inside the isolated frame.

The isolated runtime hostname is one DNS level below the platform root:
`https://workspace-key.bonfirework.org/`. It is frame infrastructure, not the
default public URL. Every site receives a distinct browser Origin, so code,
storage, service workers and browser-database permissions remain isolated
between workspaces.

`public_alias_enabled` defaults to `false`. When explicitly enabled, the
separate `workspace-key.apps.bonfirework.org` alias may also be advertised.
Database browser access always requires the exact runtime HTTPS origin in the
project's allowlist; there is no wildcard database-origin permission.

## Cloudflare and origin prerequisites

Production requires all of the following before Pages smoke testing because the
Warehouse OS shell uses a distinct per-site origin as its browser security
boundary:

- A proxied wildcard DNS record for `*.bonfirework.org` targeting the Warehouse
  origin or tunnel. Explicit infrastructure records continue to take
  precedence over the wildcard.
- A standard edge certificate covering `*.bonfirework.org` (Cloudflare
  Universal SSL covers this one-level wildcard).
- The original `Host` header forwarded to FastAPI.
- `WAREHOUSE_PAGES_ROOT_DOMAIN=apps.bonfirework.org` and
  `WAREHOUSE_PAGES_RUNTIME_ROOT_DOMAIN=bonfirework.org` and
  `WAREHOUSE_PAGES_SCHEME=https`.

The origin nginx template accepts `/apps/...`, `*.bonfirework.org`, and the
optional `*.apps.bonfirework.org` alias.
The `/apps/...` shell is never cached. HTML and service workers in the isolated
runtime revalidate immediately, fingerprinted assets are immutable, and other
static files use bounded CDN caching with release-specific ETags. If the
platform later moves untrusted runtimes to a separate registrable domain, only
the internal frame origin and exact database allowlists need to change; user
entry URLs stay stable.

## Runtime memory policy

Static releases are served directly from immutable files and never reserve a
workspace container. Dynamic Python, Node and Compose releases use
request-driven scale-to-zero: after 30 minutes without routed traffic, the
Runtime Controller stops their containers while retaining images, release files
and persistent data on SSD/HDD. A later request changes the deployment state to
`wake_requested`; the controller starts the same containers and the gateway
holds the request until the application passes its health check.

The public lifecycle is `running → suspending → suspended → wake_requested →
waking → running`. Stopped containers are intentional and therefore excluded
from drift repair and CPU autoscaling. Missing containers remain failures and
are handled by the existing rebuild/self-heal path. Controller events record
successful suspend, wake and internal failure evidence without exposing Docker
names or failure text through the public gateway.

Defaults can be adjusted with
`WAREHOUSE_RUNTIME_IDLE_TIMEOUT_SECONDS`,
`WAREHOUSE_RUNTIME_WAKE_TIMEOUT_SECONDS`, and
`WAREHOUSE_RUNTIME_WAKE_HEALTH_TIMEOUT_SECONDS`. Disabling
`WAREHOUSE_RUNTIME_IDLE_SUSPEND_ENABLED` stops new idle suspensions but still
allows already-suspended applications to wake on demand.

## API and AI workflow

Workspace-key APIs:

```text
GET /api/workspaces/v1/pages
PUT /api/workspaces/v1/pages
GET /api/workspaces/v1/pages/design
GET /api/workspaces/v1/pages/files/{path}
GET /api/workspaces/v1/pages/package
GET /api/workspaces/v1/pages/package/download
```

Hosting sessions expose the same operations below
`/api/hosting/v2/sessions/{session_id}/pages`. The design endpoint lists the
active source's code and design files, excludes secret paths, and returns
evidence-based recommendations. The file endpoint only returns bounded UTF-8
code/design files or bounded base64 image assets.
The package endpoint exposes the normalized `warehouse.pages-application.v1`
contract to users and AI clients; its download endpoint builds a deterministic,
secret-free ZIP from the same immutable source. This read-only operation never
runs a database migration. See
[`warehouse-pages-app-package.md`](warehouse-pages-app-package.md).

The signed-in Warehouse OS UI reads the non-secret control-plane aggregate at:

```text
GET /api/workspaces/{workspace_ref}/pages-console
```

It returns the canonical URL, isolated runtime policy, current release, bounded
release history, database binding and browser-origin state, storage usage and a
state-aware action catalogue.
It never returns a `wak_`, database password, internal Runtime URL or object-store
path. Mutations in the control console are handed to the governed AI/action
workflow for confirmation and audit.

### Unified Pages action protocol

The console response includes `actions.schema = warehouse.pages-actions.v1`.
Every button is rendered from this server-owned catalogue instead of embedding
its own workflow prompt in the browser. Stable action keys cover status refresh,
canonical entry open/copy, site and alias configuration, design review, release
publication, browser-database origins and activation of eligible historical
releases.

An action selects one of three presentation-neutral invocation modes:

- `client` performs a local refresh, open or copy operation.
- `typed_action` opens the ordinary capability confirmation boundary with an
  exact `tool_name` and typed arguments.
- `auto_runtime` opens the shared Warehouse Intelligence Runtime with a bounded
  `warehouse.pages-action-context.v1` hint.

The action context is navigation only. The API accepts only the Pages namespace,
bounded workspace/release references and active registered capability names.
The top router may accept, ignore or supplement the suggested capabilities; it
must still observe current state and can never treat the hint as evidence,
authorization, completion or a replacement for capability confirmation.

The matching terminal/external-AI contracts are:

```text
dm pages status
dm pages configure
dm pages design
dm pages package
dm pages file
dm pages release activate
```

`dm pages status` is the preferred observation when no intelligent-hosting
session exists. `dm pages configure` creates a governed hosting session and
submits `desired_state.pages`, so every control surface uses the same site
configuration service and exact-origin synchronization behavior.

`PUT .../pages` accepts `site_key` and optional `public_alias_enabled`; the
canonical URL remains `/apps/{site_key}/` in both cases.

Neither endpoint edits the active release. A user or AI must upload a new
immutable source version, create and verify a deployment, then activate that
healthy deployment. Configuring a Pages site adds or replaces its isolated exact
origin in an attached browser database project; renaming also revokes sessions
bound to the old origin.

## Release order

1. Back up PostgreSQL and apply Alembic through `20260805_0078`.
2. Deploy the API and Runtime Controller together.
3. Configure the one-level wildcard DNS and TLS at Cloudflare. Configure an
   advanced `*.apps.bonfirework.org` certificate only if independent aliases
   are enabled.
4. Verify one existing workspace through `/apps/{site_key}/`, its isolated
   runtime origin, and the fallback path.
5. Verify ETag revalidation, database exact-origin enforcement, activation and
   rollback before enabling site-name changes for all users.
