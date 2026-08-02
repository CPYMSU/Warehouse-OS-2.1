# Research custody API

Warehouse Research Vault accepts terminal uploads through the same tenant and
permission boundary as the web workspace. A successful upload is not an
attachment write: it verifies SHA-256, stores immutable content, creates the
next file version, makes a native Git commit, and records an audit event.

## 1. Issue a scoped Runtime API Key

Every active company user who currently holds `research.read`,
`research.write`, or `research.review` can ask the Company Secretary to issue
a self-scoped key, or run the same capability from Super Terminal:

```text
請給我一枚科研 API Key

research key issue --label Research-CLI --days 30
```

The equivalent authenticated session request uses the research-only endpoint:

```sh
curl --fail-with-body -X POST "$WAREHOUSE_BASE_URL/api/research/api-keys" \
  -H "Authorization: Bearer $WAREHOUSE_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"label":"Research-CLI","expires_in_days":30}'
```

Store the returned `wsk_…` value as `WAREHOUSE_RESEARCH_KEY`. Runtime keys are
tenant-bound, expire, can be revoked independently, and reload the owner's live
permissions on every request. This endpoint always forces the `research`
audience; callers cannot add AI Secretary or Super Terminal scope.

The secretary delivers plaintext through a one-time credential card. The value
is excluded from conversation history, Runtime snapshots, model reflection,
and command audit records.

```text
research key list
research key revoke --key-id 7
```

## 2. Install the official headless CLI

The Research key does not need the broad `terminal` audience. The official CLI
calls `/api/research/*` directly, so it can automate every research operation
while remaining unable to operate warehouse, finance, IAM, or platform APIs.

```sh
export WAREHOUSE_RESEARCH_KEY='wsk_…'
export WAREHOUSE_BASE_URL='https://bonfirework.org'

mkdir -p "$HOME/.local/bin"
curl --fail-with-body \
  -H "Authorization: Bearer $WAREHOUSE_RESEARCH_KEY" \
  "$WAREHOUSE_BASE_URL/api/research/cli/download" \
  -o "$HOME/.local/bin/bonfire-research"
chmod 700 "$HOME/.local/bin/bonfire-research"

bonfire-research whoami
bonfire-research --help
```

`research cli show` or `GET /api/research/cli/manifest` returns the current CLI
version, download SHA-256, credential variable, and command groups. The client
uses only the Python standard library and emits structured JSON, including
structured errors and stable non-zero exit codes for HTTP, network, execution,
and watch-timeout failures.

For unattended services, inject `WAREHOUSE_RESEARCH_KEY` from the service's
secret manager. Alternatively use `--key-file`; on POSIX the CLI rejects a key
file readable by group or other users. There is deliberately no `--key` option,
so plaintext credentials do not appear in shell history or process listings.
The client also rejects remote plain HTTP and refuses redirects before sending
the bearer credential.

The key authorizes all research operations that its owner can perform at the
time of each request. Removing the owner's research permission, disabling the
membership, expiry, or revocation takes effect immediately. A Research key
cannot mint or rotate credentials; key lifecycle remains behind an interactive
session or the Secretary's one-time credential flow.

## 3. Create and inspect projects from CLI

```sh
bonfire-research project list
bonfire-research project create \
  --title "Laboratory simulator" \
  --area COMPUTATIONAL-SCIENCE \
  --summary "Versioned simulation inputs, code, runs, and evidence"
bonfire-research project show --project PROJECT_ID
bonfire-research project commits --project PROJECT_ID --limit 80
```

JSON objects and arrays accept inline JSON or an `@file.json` reference. This
makes DMPs, protocol specifications, Run environments, and execution manifests
safe to generate from scripts without brittle shell quoting.

## 4. Discover projects and upload contract

```sh
curl --fail-with-body "$WAREHOUSE_BASE_URL/api/research/projects" \
  -H "Authorization: Bearer $WAREHOUSE_RESEARCH_KEY"

curl --fail-with-body \
  "$WAREHOUSE_BASE_URL/api/research/projects/PROJECT_ID/upload-contract" \
  -H "Authorization: Bearer $WAREHOUSE_RESEARCH_KEY"
```

The second response supplies the concrete multipart endpoint, byte limit,
field contract, and a safe curl template. The same information is available in
Super Terminal:

```text
research upload contract --project PROJECT_ID
```

## 5. Stream a file into custody

The CLI streams multipart bytes rather than encoding them as JSON or Base64.
By default it calculates local SHA-256 first and asks the server to verify the
same digest before accepting the immutable version.

```sh
bonfire-research file upload \
  --project PROJECT_ID \
  --file ./manuscript.docx \
  --path manuscript/manuscript.docx \
  --message "Revise methods and uncertainty analysis"
```

```sh
curl --fail-with-body -X POST \
  "$WAREHOUSE_BASE_URL/api/research/projects/PROJECT_ID/files" \
  -H "Authorization: Bearer $WAREHOUSE_RESEARCH_KEY" \
  -F "file=@./manuscript.docx" \
  -F "logical_path=manuscript/manuscript.docx" \
  -F "commit_message=Revise methods and uncertainty analysis"
```

Uploading another file to the same `logical_path` creates the next immutable
version. To verify a local artifact during ingestion, add:

```sh
-F "expected_sha256=LOCAL_SHA256"
```

The upload is streamed in bounded chunks and never encoded into JSON or
Base64. The default maximum is 250 MB and the live value is returned by
`GET /api/research/formats`.

## 6. Read, diff, download, and audit revisions

```sh
bonfire-research file versions --project PROJECT_ID --file FILE_ID
bonfire-research file preview --project PROJECT_ID --file FILE_ID
bonfire-research file diff --project PROJECT_ID --file FILE_ID --from 1 --to 2
bonfire-research file download \
  --project PROJECT_ID --file FILE_ID --version 2 --output ./manuscript-v2.docx
```

Downloads are written through a temporary file and atomically moved into place
only after the server-provided SHA-256 has been verified. Existing targets are
not replaced unless `--force` is explicit.

```sh
curl --fail-with-body \
  "$WAREHOUSE_BASE_URL/api/research/projects/PROJECT_ID/files/FILE_ID/versions" \
  -H "Authorization: Bearer $WAREHOUSE_RESEARCH_KEY"

curl --fail-with-body \
  "$WAREHOUSE_BASE_URL/api/research/projects/PROJECT_ID/files/FILE_ID/preview" \
  -H "Authorization: Bearer $WAREHOUSE_RESEARCH_KEY"

curl --fail-with-body \
  "$WAREHOUSE_BASE_URL/api/research/projects/PROJECT_ID/files/FILE_ID/diff?from_version=1&to_version=2" \
  -H "Authorization: Bearer $WAREHOUSE_RESEARCH_KEY"

curl --fail-with-body \
  "$WAREHOUSE_BASE_URL/api/research/projects/PROJECT_ID/commits?limit=80" \
  -H "Authorization: Bearer $WAREHOUSE_RESEARCH_KEY"
```

The API also accepts a project's slug. File IDs are the unambiguous reference
for terminal calls; a single-segment logical path is accepted as a convenience.

## 7. Research operating model

The workflow endpoint joins the project's living DMP, protocols, execution
runs, claims, immutable evidence links, peer reviews, reproducibility checks,
and releases:

```sh
curl --fail-with-body \
  "$WAREHOUSE_BASE_URL/api/research/projects/PROJECT_ID/workflow" \
  -H "Authorization: Bearer $WAREHOUSE_RESEARCH_KEY"
```

The same operations are discoverable in Super Terminal and Runtime Skills:

```text
research workflow show --project PROJECT_ID
research dmp show --project PROJECT_ID
research dmp update --project PROJECT_ID --question "..." --storage "..."
research protocol list --project PROJECT_ID
research protocol create --project PROJECT_ID --title "Protocol v1"
research run list --project PROJECT_ID
research run start --project PROJECT_ID --title "Run 01" --protocol PROTOCOL_ID
research run complete --project PROJECT_ID --run RUN_ID
research claim list --project PROJECT_ID
research claim create --project PROJECT_ID --statement "..."
research evidence link --project PROJECT_ID --claim CLAIM_ID --run RUN_ID
research review list --project PROJECT_ID
research review submit --project PROJECT_ID --target-type claim \
  --target CLAIM_ID --decision approve
research reproduce check --project PROJECT_ID
research release list --project PROJECT_ID
research release create --project PROJECT_ID --access restricted
research release show --project PROJECT_ID --release RELEASE_ID
```

The headless equivalents use the same nouns:

```sh
bonfire-research workflow show --project PROJECT_ID
bonfire-research dmp update --project PROJECT_ID --content @dmp.json
bonfire-research protocol create \
  --project PROJECT_ID --title "Protocol v1" --specification @protocol.json
bonfire-research run start \
  --project PROJECT_ID --title "Run 01" --environment @environment.json
bonfire-research run update \
  --project PROJECT_ID --run RUN_ID --status completed --observations @results.json
bonfire-research claim create \
  --project PROJECT_ID --statement "The intervention changes outcome Y"
bonfire-research evidence link \
  --project PROJECT_ID --claim CLAIM_ID --file-version FILE_VERSION_ID
bonfire-research review submit \
  --project PROJECT_ID --target-type claim --target CLAIM_ID --decision approve
bonfire-research reproduce check --project PROJECT_ID
bonfire-research release create --project PROJECT_ID --access restricted
```

An evidence link accepts exactly one immutable `file_version_id` or one
`run_id`. Reviews require `research.review`; approving a DMP marks the current
revision approved, approving a protocol locks its baseline, and approving a
claim makes it eligible for release.

`research reproduce check` freezes a SHA-256 manifest and validates that the
project has an approved, sufficiently complete DMP, a locked protocol, a
completed run with execution context, and claims backed by exact evidence.
A published release additionally requires at least one accepted claim and a
fully passed check.

## Isolated reproducible computation

The manifest check is complemented by a durable execution queue. Every job
pins exact research file-version IDs and SHA-256 values before it can run.
The executor has no internet route, no shell adapter or Docker socket, uses a
read-only container filesystem, and runs each program under a distinct numeric
UID with CPU, memory, process, file-size and wall-clock limits.

```text
research execution runtimes
research execution list --project PROJECT_ID
research execution submit --project PROJECT_ID --entrypoint analysis/main.py --arguments '["--seed","42"]'
research execution show --project PROJECT_ID --execution EXECUTION_ID
research execution cancel --project PROJECT_ID --execution EXECUTION_ID
research execution retry --project PROJECT_ID --execution EXECUTION_ID
research artifact promote --project PROJECT_ID --execution EXECUTION_ID --artifact ARTIFACT_ID --path results/summary.csv
```

The CLI can submit and wait without polling code in the calling script:

```sh
bonfire-research execution submit \
  --project PROJECT_ID \
  --entrypoint analysis/main.py \
  --arguments '["--seed","42"]' \
  --limits '{"timeout_seconds":300,"memory_mb":1024}'

bonfire-research execution watch \
  --project PROJECT_ID --execution EXECUTION_ID --wait-timeout 900

bonfire-research artifact download \
  --project PROJECT_ID --execution EXECUTION_ID --artifact ARTIFACT_ID \
  --output ./summary.csv

bonfire-research artifact promote \
  --project PROJECT_ID --execution EXECUTION_ID --artifact ARTIFACT_ID \
  --path results/summary.csv --message "Promote verified simulation output"
```

The first runtime is `python-3.13` with NumPy, Pandas and SciPy. Programs read
the immutable package from `RESEARCH_INPUT_DIR` and write outputs only beneath
`RESEARCH_OUTPUT_DIR`. On completion the worker records bounded stdout/stderr,
hashes every regular output file, and registers it as an execution artifact.
Researchers can inspect an artifact inline and explicitly promote it into the
research vault; promotion creates a normal immutable file version and Git
commit, so later revisions retain the existing preview and diff behavior.

Every release contains:

- an immutable Warehouse research manifest and SHA-256;
- file version hashes and Git commit references;
- protocol, Run, claim, and evidence identifiers;
- an RO-Crate JSON-LD graph;
- explicit `open`, `embargoed`, or `restricted` access policy.
