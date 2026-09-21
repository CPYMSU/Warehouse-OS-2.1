# DB Studio: view-designer preview and production integration plan

## Status

This is a standalone, read-only interaction prototype, not a completed native module or production release. Entry: `frontend/v2/db-studio.html`. No existing application files, navigation, bundles, migrations, database records or deployment configuration are changed. AG Grid, Tabulator and React Flow are recommendations below; none is a runtime dependency of this preview.

The local JSON mode works without a backend. Account-backed reads require this page to be served by the authenticated Warehouse 2.1 origin, not a plain static development server. This branch has not been deployed or validated against production sessions.

## Implemented

- Table, cards, expandable JSON and sample-field structure views.
- Independent spacing density (0-100; does not shrink fonts) and detail level (first 3, first 8 or all selected fields).
- Column visibility, display aliases, up/down ordering, width and typed display format.
- Record inspector, search over loaded records and client pagination (25/50/100). Counts explicitly describe loaded records, not the full database.
- Local JSON import/paste, plus read-only adapters for `/api/auth/me`, `/api/account/profile` and `/api/tasks?scope=mine` using the existing account/tenant headers. These are API projections, not physical database tables.
- Named designs in page memory; style JSON import/export. Refresh clears records and named presets. Export contains only version, view, density, detail and whitelisted column configuration, not record values or credentials.
- Bounded input: 2 MiB, 5000 rows, 200 top-level fields, depth 32. JSON tree expands child entries in batches of 100.
- Text-only rendering, explicit 401/403/non-JSON/unavailable states, abort/stale-response checks, and clearing loaded remote records and the inspector after an account/tenant change. This is client hygiene, not a replacement for server authorization.

Field hiding is presentation, not access control: the inspector can show all fields already returned by the authorized source. Field types are inferred from the sample; they are not database DDL. Numeric identifiers beyond JavaScript safe-integer precision must be supplied as JSON strings.

## Tests

Run `node --test scripts/test_db_studio.cjs` (7 tests).
Run `python scripts/test_db_studio_browser.py` with Python Playwright and Chromium installed; set `CHROMIUM_PATH` when needed (21 checks).
The browser test injects local HTML/CSS/JS and mocks storage/fetch. It uses only synthetic records and makes no production API requests. It verifies four views, density, field visibility/reordering, pagination, style export, text-only rendering, identity clearing and error handling. It is not a full backend, native-shell, CI or production integration test.

## Recommended mature components

Prefer AG Grid Community for the production table renderer: column state, filtering, sorting, paging and virtualization. Use documented compactness parameters rather than arbitrary CSS row heights. Enterprise features, including its server-side row model, pivoting and master/detail, require the appropriate license; do not accidentally bundle them into a Community-only implementation.

Tabulator is a viable alternative for a lightweight vanilla-JavaScript integration. NocoDB supplies a useful product pattern: separate configurations for multiple views over the same data. It is not proposed as a parallel backend. React Flow is an optional future relationship/schema renderer, with contextual zoom changing node detail rather than merely enlarging text.

Primary documentation checked for this design:
- https://www.ag-grid.com/javascript-data-grid/theming-compactness/
- https://www.ag-grid.com/javascript-data-grid/community-vs-enterprise/
- https://www.tabulator.info/docs/6.x/layout/
- https://nocodb.com/docs/product/tables/views
- https://reactflow.dev/examples/interaction/contextual-zoom

## Required before native production release

1. Add the `db` page to `W2.PAGES`, navigation, route ACL and the existing deterministic bundle build. Validate entry/return paths and tenant switching in the actual shell.
2. Add a source adapter over the existing company-authorized workspace schema/table endpoints documented in `digital-asset-hosting.md`. Preserve backend ACL/RLS and define paging, sorting and filtering contracts. Never accept arbitrary SQL, DSNs or client-selected tenant IDs. MySQL/MongoDB/SQLite are not implemented by this prototype.
3. Persist only validated view definitions, scoped to tenant + user + source. Add optimistic version checks and explicit sharing permissions; changing a layout must not mutate business data.
4. Install and pin the selected mature renderer through the repository's governed build, then test large-result paging, keyboard/touch accessibility, permissions, schema changes, and stale-source races.
5. Add relationship views only when backend relation metadata exists. Do not infer foreign keys merely from similar field names. A future semantic-zoom rule could progress from database summary to table fields to record details, all within the same authorization boundary.

Proposed architecture: authorized source adapter -> normalized records + schema -> validated ViewSpec -> selected renderer. Spacing density, content detail and data permissions are three separate concepts.
