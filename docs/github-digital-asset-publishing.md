# GitHub → Warehouse digital-asset publishing on Mac mini

This channel keeps GitHub as the source-of-code boundary and Warehouse OS as the
custody, release, runtime, database, and routing boundary.

## Topology

```text
Digital-asset source repositories
        |
        | read-only HTTPS clone
        v
CPYMSU/registry
        |
        | registry.json only; no wak_ credentials
        v
Warehouse-OS-2.1 GitHub Actions
        |
        | self-hosted / macOS / ARM64 / warehouse-production
        v
Mac mini runner
        |
        | resolve workspace_key_ref from Actions secret
        | use workspace-scoped wak_ over HTTPS only
        v
Warehouse Source Version
        |
        v
Release candidate -> lifecycle jobs -> acceptance
        |
        v
explicit pre-authorized activation
        |
        v
public-route verification -> automatic rollback on failure
```

The source repositories and the registry repository do **not** need self-hosted
runners. Publishing Actions live only in `Warehouse-OS-2.1`, so the existing
Mac mini production runner executes every publish.

The publisher never needs Mac SSH, the Docker socket, PostgreSQL credentials, or
host filesystem paths. It can affect only the workspace represented by each
resolved `wak_` key.

## Dedicated publishing registry

The dedicated private registry is:

`CPYMSU/registry`

It contains declarative bindings only; it must never contain a `wak_` key or
database/server credential.

At the repository root, `registry.json` uses this shape:

```json
{
  "schema": "warehouse.digital-asset-registry.v1",
  "links": [
    {
      "repository": "CPYMSU/MK7",
      "ref": "main",
      "workspace_key_ref": "mk7",
      "runtime_type": "auto",
      "component": "",
      "activate": true,
      "timeout_seconds": 3600,
      "enabled": true
    }
  ]
}
```

A committed example also lives at `docs/digital-asset-registry.example.json`.
The registry repository itself contains `registry.schema.json` for editor and
review validation.

Fields:

- `repository`: exact source `owner/repository`.
- `ref`: branch or tag to follow.
- `source_path`: optional repository-relative subtree, for example `assets/mk7`; only that subtree is archived as the asset source.
- `workspace_key_ref`: non-secret lookup name for the target Warehouse
  Workspace credential.
- `runtime_type`: normally `auto`; may also be `static`, `web`, `api`, `worker`,
  `agent`, `container`, or `compose`.
- `component`: optional existing Warehouse component name.
- `activate`: defaults to `true`. When false the release may stop at
  `awaiting_activation` after verification.
- `timeout_seconds`: 60–7200, normally 3600.
- `enabled`: optional; set `false` to retain the declaration without publishing.

The resolver rejects any registry entry containing `workspace_key`; secrets are
not allowed in Git history.

## Warehouse Actions secrets

Create `WAREHOUSE_ASSET_WORKSPACE_KEYS_JSON` in
`CPYMSU/Warehouse-OS-2.1` Actions secrets. It maps registry references to real
workspace credentials:

```json
{
  "mk7": "wak_REDACTED",
  "another-app": "wak_REDACTED"
}
```

Because `CPYMSU/registry` is private, create
`WAREHOUSE_ASSET_GITHUB_TOKEN` as well. Use a fine-grained token with
**Contents: Read** for `CPYMSU/registry` and any private source repositories the
Mac runner must clone. Do not grant repository administration or write access.

Optional repository variables:

- `WAREHOUSE_ASSET_REGISTRY_REPOSITORY` — defaults to `CPYMSU/registry`.
- `WAREHOUSE_ASSET_REGISTRY_REF` — defaults to `main`.
- `WAREHOUSE_ASSET_REGISTRY_PATH` — defaults to `registry.json`.
- `WAREHOUSE_BASE_URL` — defaults to `https://bonfirework.org`.
- `WAREHOUSE_ASSET_REGISTRY_ENABLED` — must be `true` before scheduled/manual
  registry publishing jobs execute.

## What happens on each check

`.github/workflows/digital-asset-publish.yml` runs every five minutes and can
also be started manually. Every job uses:

```yaml
runs-on: [self-hosted, macOS, ARM64, warehouse-production]
```

`ops/macos/publish-digital-assets-from-registry.py` first:

1. read-only clones `CPYMSU/registry`;
2. validates `registry.json` and rejects committed `wak_` credentials;
3. resolves every `workspace_key_ref` from
   `WAREHOUSE_ASSET_WORKSPACE_KEYS_JSON`;
4. passes the resolved in-memory bindings to the publisher. The resolved JSON is
   never written back to Git.

For each enabled binding, `ops/macos/publish-digital-assets.py` then:

1. shallow-clones the configured source ref on the Mac mini and, when `source_path` is set, selects only that subtree;
2. resolves the exact 40-character commit SHA;
3. checks whether that commit is already a Warehouse Source Version;
4. if needed, creates a deterministic Git archive and uploads it through the
   workspace API;
5. creates or reuses an idempotent governed Release for that commit;
6. lets the Runtime Controller build the candidate;
7. runs declared lifecycle jobs and acceptance checks;
8. if `activate=true`, activates only after acceptance;
9. waits for public-route verification; Warehouse retains its normal rollback
   behavior if the new revision cannot be verified.

Unchanged commits are safe to re-check. Source registration and Release creation
are idempotent, so the schedule does not create a new release every five minutes.

## Manual publish

Open **Digital asset publish** in the Warehouse repository and run it. Leave the
`repository` input blank to check all registry entries, or enter an exact value
such as `CPYMSU/MK7` to publish only that binding.

## Mac-only Actions policy

Warehouse workflows use the production Mac mini runner labels. The PR contract
workflow has an additional same-repository guard: fork PR code is not executed
on the Mac mini. Publishing remains centralized in Warehouse rather than
registering the production runner independently in every source repository.
