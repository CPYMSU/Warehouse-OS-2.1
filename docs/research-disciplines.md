# Research disciplines and workflows

The Research workspace groups projects into Data Science, Engineering Science,
Theoretical Science and Econometrics. Each has its own ordered research prompts,
expected outputs and links to the existing data, execution and evidence workspaces.
The four cards filter project selection and the library. A project can be
classified on creation or from **專業與流程**. Existing subject-area text remains
available; only exact recognized discipline names are automatically recognized.
Other existing projects remain visibly unclassified until a researcher chooses.

The Econometrics template follows the requested question → database → econometric
model → regularities → economic phenomenon → hypothesis model → substitution and
channels → dynamic equilibrium → influence logic and boundaries → real case path,
followed by review and reproduction. Data discovery, causal identification and
model-based implications are recorded separately. It is an editable research
route, not a claim that every study must follow a single universal sequence.
Methods guidance was checked against the [MIT Econometrics syllabus](https://ocw.mit.edu/courses/14-382-econometrics-spring-2017/pages/syllabus/)
and the [NIST process-modeling handbook](https://itl.nist.gov/div898/handbook/pmd/pmd.htm).

## Persistence and authorization

- `GET /api/research/projects` includes the shared discipline catalogue and each
  project's resolved `discipline`.
- `POST /api/research/projects` accepts optional `discipline`. The CLI's existing
  metadata argument also accepts `research_discipline`.
- `PUT /api/research/projects/{project}/discipline` accepts `discipline` and optional
  `expected_discipline`; null explicitly leaves a project unclassified.
- `PUT /api/research/projects/{project}/discipline-workflow/stages/{stage}` accepts
  `discipline`, `notes`, `status` and required `expected_revision`.
- `GET /api/research/projects/{project}/workflow` includes `discipline_workflow`.

Classification uses existing project metadata. Stage notes are stored under
`discipline_workflows` in immutable DMP revisions. Generic DMP updates preserve
these notes; switching disciplines retains each discipline's prior notes. The
project lock serializes writes, and per-stage revisions reject stale updates
with 409. Both mutations require `research.write` and use existing tenant RLS.
No schema or permission changes are required.

Stage completion is a researcher's explicit declaration with nonempty outcome
notes; it is separate from peer review and publication gates. Drafts are retained
locally per tenant, actor, project, discipline and stage. After a conflict, the
researcher can compare the server version before continuing with their draft.

## Verification

```sh
python -m pytest backend/tests/test_research_disciplines.py
node scripts/build_v2_frontend.cjs --check
```

Browser verification exercises all four workflows, the 11 Econometrics stages,
category filtering, reload persistence, local drafts, concurrent edits, legacy
classification, rapid project switching, empty categories, project creation,
390px layout and read-only accounts using the actual compiled application.
