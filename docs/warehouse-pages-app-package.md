# Warehouse Pages Application Package v1

The Warehouse Pages application package is the portable boundary between an
immutable source version and the four execution planes used by Pages:

1. Static web files execute in the user's browser.
2. Collections use the platform database API and optional cursor sync into
   IndexedDB.
3. Small privileged operations use scale-to-zero serverless functions.
4. Device capabilities are optional and must never be required by an ordinary
   mobile browser session.

The package does not replace `warehouse.hosting.json`. That existing manifest
continues to describe dedicated/server Runtime compatibility. A source archive
may contain both manifests while it is being migrated.

## Manifest

Place `warehouse.pages.json` at the application root:

```json
{
  "schema": "warehouse.pages-application.v1",
  "name": "Question Studio",
  "version": "2.1.0",
  "web": {
    "root": "web",
    "entry": "index.html",
    "compute": "browser",
    "navigation_fallback": "index",
    "service_worker": "sw.js"
  },
  "data": {
    "mode": "platform_api",
    "default_access": {"read": "deny", "write": "deny"},
    "collections": [
      {
        "name": "questions",
        "access": {"read": "session", "write": "owner"},
        "offline": true
      }
    ],
    "sync": {
      "mode": "cursor",
      "offline_store": "indexeddb",
      "cursor_field": "updated_at",
      "pull_limit": 500
    }
  },
  "functions": [
    {
      "name": "questions.resolve",
      "route": "/api/questions/resolve",
      "methods": ["POST"],
      "runtime": "serverless_node",
      "source": "functions/resolve",
      "handler": "index.resolve",
      "auth": "session",
      "secret_refs": ["AI_PROVIDER_KEY"],
      "timeout_seconds": 30
    }
  ],
  "device": {"mode": "disabled", "capabilities": []},
  "design": {
    "roots": ["web", "design"],
    "api_schema": "design/openapi.json",
    "components": "design/components.json"
  }
}
```

The machine-readable authoring schema is
[`warehouse-pages-app-v1.schema.json`](warehouse-pages-app-v1.schema.json).
Unknown fields fail validation. Every declared web, function and design path
must exist in the same immutable source archive.

`secret_refs` contains names only. Warehouse resolves those names inside the
serverless execution boundary; values are never written into the manifest or
download metadata. The exporter also omits known environment, credential and
private-key paths. Source authors must still avoid hard-coded credentials in
ordinary JavaScript, HTML or other source files.

## Legacy compatibility

If an older project has no `warehouse.pages.json`, Warehouse generates a
conservative contract only when it can find `index.html`. A browser-only source
declares no database collections, functions or Local Agent. If the same source
also contains a recognizable Python or Node server, the generated contract
declares `/api/*` as one scale-to-zero compatibility function and marks the
device runtime optional. This prevents a mixed legacy application from being
misreported as fully static. The result can be downloaded, split into smaller
Data API/functions boundaries and committed as an explicit manifest.

## Deterministic ZIP

The exported ZIP contains:

```text
application files
warehouse.pages.json
.warehouse/package.json
.warehouse/checksums.json
```

Entries are sorted and assigned fixed metadata. `checksums.json` records the
SHA-256 of every payload file, and the response exposes the SHA-256 of the
complete ZIP. Exporting the same immutable source and contract therefore
produces the same bytes.

Package creation is read-only. It does not deploy code, update a database,
change browser origins or start a Runtime. Database schema and browser-rule
reconciliation belong to the asynchronous control plane and never block this
export or an ordinary code release.

## API and AI

Signed-in Warehouse OS account:

```text
GET /api/workspaces/{workspace_ref}/pages/package
GET /api/workspaces/{workspace_ref}/pages/package/download
```

Workspace key:

```text
GET /api/workspaces/v1/pages/package
GET /api/workspaces/v1/pages/package/download
```

All four endpoints accept an optional `source_ref`. The JSON endpoint gives AI
the normalized manifest, immutable source identity, design-file API and ZIP
download address without returning source bytes or credentials. The shared
terminal capability is `dm pages package --workspace <workspace>`.

The Pages control console receives the same capability as the read-only
`pages.package.download` action. The default public address remains
`https://bonfirework.org/apps/{site_key}/`; exporting a package does not create
or enable a separate subdomain alias.
