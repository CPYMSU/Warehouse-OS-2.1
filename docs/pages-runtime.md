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

The isolated hostname is runtime infrastructure, not the default public URL.
`public_alias_enabled` defaults to `false`; when explicitly enabled the same
hostname may also be advertised as an independent public alias. Database browser
access always requires the exact isolated HTTPS origin in the project's
allowlist; there is no wildcard database-origin permission.

## Cloudflare and origin prerequisites

Production requires all of the following before Pages smoke testing, even when
the independent alias is not advertised, because the Warehouse OS shell uses
the isolated origin as its browser security boundary:

- A proxied wildcard DNS record for `*.apps.bonfirework.org` targeting the
  Warehouse origin or tunnel.
- An edge certificate that explicitly covers `*.apps.bonfirework.org`.
- The original `Host` header forwarded to FastAPI.
- `WAREHOUSE_PAGES_ROOT_DOMAIN=apps.bonfirework.org` and
  `WAREHOUSE_PAGES_SCHEME=https`.

The origin nginx template accepts both `/apps/...` and `*.apps.bonfirework.org`.
The `/apps/...` shell is never cached. HTML and service workers in the isolated
runtime revalidate immediately, fingerprinted assets are immutable, and other
static files use bounded CDN caching with release-specific ETags. If the
platform later moves untrusted runtimes to a separate registrable domain, only
the internal frame origin and exact database allowlists need to change; user
entry URLs stay stable.

## API and AI workflow

Workspace-key APIs:

```text
GET /api/workspaces/v1/pages
PUT /api/workspaces/v1/pages
GET /api/workspaces/v1/pages/design
GET /api/workspaces/v1/pages/files/{path}
```

Hosting sessions expose the same operations below
`/api/hosting/v2/sessions/{session_id}/pages`. The design endpoint lists the
active source's code and design files, excludes secret paths, and returns
evidence-based recommendations. The file endpoint only returns bounded UTF-8
code/design files or bounded base64 image assets.

The signed-in Warehouse OS UI reads the non-secret control-plane aggregate at:

```text
GET /api/workspaces/{workspace_ref}/pages-console
```

It returns the canonical URL, isolated runtime policy, current release, bounded
release history, database binding count, storage usage and account capabilities.
It never returns a `wak_`, database password, internal Runtime URL or object-store
path. Mutations in the control console are handed to the governed AI/action
workflow for confirmation and audit.

`PUT .../pages` accepts `site_key` and optional `public_alias_enabled`; the
canonical URL remains `/apps/{site_key}/` in both cases.

Neither endpoint edits the active release. A user or AI must upload a new
immutable source version, create and verify a deployment, then activate that
healthy deployment. Configuring a Pages site adds or replaces its isolated exact
origin in an attached browser database project; renaming also revokes sessions
bound to the old origin.

## Release order

1. Back up PostgreSQL and apply Alembic through `20260805_0077`.
2. Deploy the API and Runtime Controller together.
3. Configure wildcard DNS and TLS at Cloudflare.
4. Verify one existing workspace through `/apps/{site_key}/`, its isolated
   runtime origin, and the fallback path.
5. Verify ETag revalidation, database exact-origin enforcement, activation and
   rollback before enabling site-name changes for all users.
