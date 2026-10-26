# Research-first navigation

The standard Bonfire shell starts with Research, Tasks and Administration.
Research is the default route and the masthead identifies the site as
Bonfire Research. The administration hub uses the research workspace's Swiss
typography with a racing circuit, checkered markers and red/yellow/blue lanes.

Administration groups Warehouse, Alerts, Stocktake, ERP, Finance, Assets,
Procurement, Legal, Map and Reports. The existing business dashboard is an
additional overview inside that workspace. Category filters and search operate
on the actual visible entries. Counts describe available workspaces and groups.

## Routing and authority

The administrative parent is derived after `allowed_nav`, effective permissions,
template selection and navigation visibility settings have been applied.
It exists only when at least one administrative child is available. Its cards
and subnavigation receive that same authorized set.

Canonical hashes such as `#/finance` and `#/reports` retain their existing pages,
API calls and business-action context. The shell places them inside the
administrative frame and highlights the administrative parent. The Warehouse
page retains its own inventory, inbound, outbound and shipment tabs.
The original module index remains available to the business dashboard.

An actor who lacks Research receives the first available authorized entry.
Actors with no administrative children have no administrative entry. Existing
BIU legal-ethics and Civilization navigation profiles retain their own routes
and ordering. This presentation change introduces no permission, database or
data-migration contract.

## Verification

```sh
node scripts/test_research_navigation.cjs
node scripts/build_v2_frontend.cjs --check
```

The navigation regression test executes the actual navigation model and checks
research priority, the ten grouped workspaces, old deep links, warehouse tabs,
explicit grants, hidden modules, restricted users and specialized profiles.
Browser verification uses the compiled application with isolated API fixtures
to exercise the hub, search, child navigation, a restricted-account redirect,
mobile layout and the research reader's immediate loading feedback.
