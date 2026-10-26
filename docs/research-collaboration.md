# Researcher and Codex collaboration

Each discipline step shares its project context, plan, findings, blockers,
next action, assignee, progress and immutable research artifacts with Codex.
The website reads these same records. An external Codex session can continue
the project through the scoped Research CLI; the web panel supplies a current
task prompt and machine-readable contract. It does not pretend to start a Codex
session by itself.

## One-time connection

Use the existing Research API Key credential flow and install the current
`bonfire-research` CLI as described in [Research API](research-api.md). Supply
`WAREHOUSE_BASE_URL` and `WAREHOUSE_RESEARCH_KEY` in the Codex execution
environment. The key stays outside prompts, project files and process arguments.

## Work on a step

```sh
bonfire-research collaboration context --project PROJECT_ID --stage STAGE_KEY
bonfire-research collaboration context --project PROJECT_ID --stage STAGE_KEY --format prompt --output AGENTS.md
bonfire-research file download --project PROJECT_ID --file FILE_ID --version VERSION --output ./input.csv
bonfire-research stage save --project PROJECT_ID --stage STAGE_KEY --payload @stage.json
bonfire-research collaboration publish --project PROJECT_ID --stage STAGE_KEY --file ./chart.html --role visualization --path figures/chart.html
```

The generated task contains the actual project and discipline, required
research output, previous progress, pinned input versions, supported tool paths,
authorization and relevant testing instructions. Discover the fresh revision
before saving. `stage.json` includes `discipline` and `expected_revision`, plus
the fields being updated: `notes`, `plan`, `findings`, `blockers`, `next_action`,
`assignee`, `status` or `artifacts`.

Stage states are `planned`, `in_progress`, `blocked`, and `completed`. A completed
step needs recorded outcome notes. Assignee is `user`, `codex`, or `shared`;
this is an assignment, not proof that an agent is currently running. Artifacts
use immutable `file_version_id`, a role (`design`, `dataset`, `code`,
`visualization`, `report`, `other`), and an optional title. References must belong
to the same tenant and project.

`collaboration publish` streams a SHA-verified file into the existing project
vault, then links that version to the step. It preserves unrelated research
notes and artifacts. If a concurrent edit prevents linking, the CLI returns
the retained upload's version ID and stops; it never overwrites the other edit
or silently repeats the upload.

## Display and publication

The Swiss workspace shows actual stage states, artifacts, plans and next
actions. Visible discipline pages refresh their workflow in the background and
on return to the browser, preserving local drafts. The artifact panel fetches
authenticated content and displays supported documents, datasets and figures.
Interactive HTML remains in an isolated preview.

Uploading research artifacts and updating progress do not redeploy the website.
Research releases continue through the existing review/reproduction contract.
Applications requiring a server Runtime need separately authorized workspace
deployment; a research-scoped key does not grant platform deployment access.

## Interfaces

- `GET /api/research/projects/{project}/collaboration?stage={step}`
- `PUT /api/research/projects/{project}/discipline-workflow/stages/{step}`
- Existing file upload/download, execution and research-release APIs.
- Internal capabilities `research_collaboration_context` and
  `research_stage_save` use the same endpoints and permissions.

Verification is limited to the changed collaboration contract, CLI publication
path, one browser collaboration scenario and necessary live read/write checks.
