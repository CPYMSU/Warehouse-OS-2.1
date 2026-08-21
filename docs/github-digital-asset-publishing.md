# GitHub → Warehouse digital-asset publishing on Mac mini

This channel keeps GitHub as the source-of-code boundary and Warehouse OS as the
custody, release, runtime, database, and routing boundary.

## Topology

```text
GitHub source repository
        |
        | HTTPS clone (read only)
        v
Warehouse-OS-2.1 GitHub Actions
        |
        | self-hosted / macOS / ARM64 / warehouse-production
        v
Mac mini runner
        |
        | workspace-scoped wak_ credential over HTTPS only
        v
Warehouse source version
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

The source repository does **not** need a self-hosted runner. This matters for a
personal GitHub account, where self-hosted runners are normally repository
scoped. The only Actions workflow that performs publishing lives in
`Warehouse-OS-2.1`, so the existing Mac mini runner can execute every publish.

The publisher never needs Mac SSH, the Docker socket, PostgreSQL credentials, or
host filesystem paths. It can affect only the workspace represented by its
`wak_` key.

## Configure linked assets

Create the following Actions secret in `CPYMSU/Warehouse-OS-2.1`:

`WAREHOUSE_ASSET_LINKS_JSON`

Example:

```json
{
  "links": [
    {
      "repository": "CPYMSU/MK7",
      "ref": "main",
      "workspace_key": "wak_REDACTED",
      "runtime_type": "auto",
      "component": "",
      "activate": true,
      "timeout_seconds": 3600
    }
  ]
}
```

Fields:

- `repository`: exact `owner/repository`.
- `ref`: branch or tag to follow. Defaults to `main`.
- `workspace_key`: the target workspace's `wak_` key. Store it only in the
  GitHub Actions secret; never commit it.
- `runtime_type`: usually `auto`. It may also be `static`, `web`, `api`,
  `worker`, `agent`, `container`, or `compose`.
- `component`: optional existing Warehouse component name.
- `activate`: defaults to `true`. When false, the candidate is built and
  accepted but stays at `awaiting_activation`.
- `timeout_seconds`: 60–7200, default 3600.
- `enabled`: optional. Set to `false` to keep an entry without publishing it.

For **public** source repositories this is the only required secret.

For **private** source repositories also create
`WAREHOUSE_ASSET_GITHUB_TOKEN`. Use a fine-grained GitHub token with read-only
Contents access only to the source repositories that Warehouse must clone. Do
not grant administration or write access.

`WAREHOUSE_BASE_URL` may be set as a repository variable. It defaults to
`https://bonfirework.org`.

## What happens on each check

`.github/workflows/digital-asset-publish.yml` runs every five minutes and can
also be started manually. Every job uses:

```yaml
runs-on: [self-hosted, macOS, ARM64, warehouse-production]
```

For each enabled link, `ops/macos/publish-digital-assets.py`:

1. shallow-clones the configured ref on the Mac mini;
2. resolves the exact 40-character commit SHA;
3. checks whether that commit is already a Warehouse Source Version;
4. if needed, creates a Git archive and uploads it through the workspace API;
5. creates or reuses an idempotent governed Release for that commit;
6. lets the Runtime Controller build the candidate;
7. runs declared lifecycle jobs and acceptance checks;
8. if `activate=true`, activates only after acceptance;
9. waits for public-route verification; Warehouse retains its normal rollback
   behavior if the new revision cannot be verified.

Unchanged commits are safe to re-check. Source registration and Release creation
are idempotent, so the five-minute schedule does not create a new release every
time.

## Manual publish

Open the **Digital asset publish** workflow in the Warehouse repository and run
it. Leave `repository` blank to check all configured assets, or enter an exact
value such as `CPYMSU/MK7` to publish only that link.

## Existing Hosting Fabric repository sync

Warehouse's Runtime Controller already supports `repository` resources with
`auto_sync` and can register immutable source versions from GitHub/GitLab. The
Mac-runner publisher intentionally uses the public workspace API and the newer
Release orchestration layer for the final build/accept/activate path. Both paths
remain workspace-scoped and can coexist; source SHA/version idempotency prevents
duplicate custody records for identical content.

## Mac-only Actions policy

Warehouse workflows use the production Mac mini runner labels. The PR contract
workflow has an additional same-repository guard: fork PR code is not executed
on the Mac mini. A maintainer can run the contract workflow manually after
review when needed.
