# Research showcase

The Research page has a **研究展示** tab and an overview entry. Its reading
edition contains PDF manuscripts, interactive HTML explanations and a methods
comparison. `/#/research?section=showcase` opens the tab directly after login.

The owner requested this website edition on 2026-10-26, explicitly selecting
the contents served at `http://127.0.0.1:8000/`. That request authorizes these
website copies of pages previously labelled local-only; original project
instructions, manuscripts, source files and research claims are unchanged.

## Content and access

Actual papers and page contents are **runtime data**, never public GitHub
assets or frontend build inputs. Both catalogue and content endpoints require
the ordinary live `current_actor` authentication and `research.read` permission.
An edition is scoped to exactly one tenant UUID. Other tenants receive an
explicit empty state. Both endpoints use private, uncached responses.

The importer follows only the selected site's `mk73`, `mk77`, `learn` and
`papers` routes. It embeds local image, stylesheet and script dependencies,
records original and exported SHA-256 hashes, and keeps linked historical
HTML editions. It does not import project directories, raw data, credentials
or unrelated local services.

HTML is rendered in an opaque iframe sandbox with scripts enabled for models.
It cannot read the application token or local storage. Internal navigation
uses a parent message checked against the current iframe and the tenant's
exact file manifest; the authenticated parent fetches the next page. PDFs
use authenticated fetches and revocable blob URLs. Selecting another tenant
clears the prior edition and pending responses.

Opening a document immediately reveals and focuses the reader. A Swiss grid
animation identifies connection, byte transfer and page composition separately;
the byte count and percentage use the actual response stream and edition file
size. The indicator remains until the HTML/PDF frame has loaded. Slow requests
retain visible feedback, and failures offer retry inside the reading panel.
Closing or switching documents aborts the prior transfer. Reduced-motion
preferences retain the progress information without animation.

## Update an edition

With the selected reading server running on the author's computer:

```sh
python scripts/import_research_showcase.py --source http://127.0.0.1:8000/
```

The default output, `backend/var/research-showcase-export`, is ignored by Git
and release packaging. Transfer this directory privately to the production
host, copy it into the API container, then run the installer **inside that API
image**, where ordinary application settings identify durable research storage:

```sh
python scripts/install_research_showcase.py --bundle /tmp/research-edition --tenant bonfire
```

The installer checks every content size and SHA-256 before writing, resolves
the active tenant through the existing database, and atomically replaces a
relative `_showcase` symlink. Editions live under
`WAREHOUSE_RESEARCH_REPOSITORY_ROOT/<tenant-uuid>/_showcase-editions/` and survive
API replacement. Older editions remain available for rollback. Data must be
transferred to each serving node; database replication does not copy files.

Frontend/API code follows the ordinary coordinated production release channel.
No schema migration, new account or permission expansion is required.
