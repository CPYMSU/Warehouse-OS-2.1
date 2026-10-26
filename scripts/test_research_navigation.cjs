"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../frontend/v2/app.jsx"), "utf8");
const start = source.indexOf("const NAV2 =");
const end = source.indexOf("/* ── 語言切換");
assert.ok(start > 0 && end > start, "The navigation model boundary must be present");
const context = vm.createContext({ W2: { WarehouseTabs: true }, window: {}, location: { hash: "" } });
vm.runInContext(source.slice(start, end) + "\nglobalThis.model = navModelOf;globalThis.defaults = routeNow;globalThis.ids = NAV2.map(n => n.id);", context);
const ids = values => Array.from(values, value => value.id);
const account = allowed => ({ allowed_nav: allowed, roles: [{ level: 10 }], permissions: [] });
const all = Array.from(context.ids);
const complete = context.model(account(all), false, {}, "research_lab");
const grouped = ["warehouse", "alerts", "stocktake", "erp", "finance", "assets", "procurement", "legal", "gis", "reports"];

assert.deepEqual(ids(complete.main).slice(0, 3), ["research", "tasks", "administration"]);
assert.equal(context.defaults(), "research");
for (const id of ["dashboard", ...grouped, "inventory", "inbound", "outbound", "shipments"]) {
  assert.equal(ids(complete.main).includes(id), false, id + " must not remain in the primary navigation");
}
for (const id of grouped) assert.ok(ids(complete.administrative).includes(id), id + " must remain available inside administration");
const parent = complete.main.find(item => item.id === "administration");
for (const id of ["administration", ...grouped, "inventory", "inbound", "outbound", "shipments"]) {
  assert.ok(parent.activeRoutes.includes(id), id + " must highlight the administrative parent");
}
assert.ok(ids(complete.routeItems).includes("finance"), "Canonical authorized links remain routable");
assert.ok(ids(complete.routeItems).includes("administration"));
assert.deepEqual(ids(complete.warehouseTabs), ["inventory", "inbound", "outbound", "shipments"]);
assert.ok(ids(complete.moduleItems).includes("perms"), "The existing dashboard keeps its full authorized module view");

const limited = context.model(account(["research", "inventory"]), false, {}, "research_lab");
assert.deepEqual(ids(limited.administrative), ["warehouse"]);
assert.deepEqual(ids(limited.warehouseTabs), ["inventory"]);
assert.equal(ids(limited.routeItems).includes("finance"), false);
assert.equal(limited.main.find(item => item.id === "administration").activeRoutes.includes("outbound"), false);

const scienceOnly = context.model(account(["research"]), false, {}, "research_lab");
assert.deepEqual(ids(scienceOnly.main), ["research"]);
assert.equal(ids(scienceOnly.routeItems).includes("administration"), false);
const noScience = context.model(account(["tasks", "finance"]), false, {}, "research_lab");
assert.deepEqual(ids(noScience.main), ["tasks", "administration"]);
assert.equal(ids(noScience.routeItems).includes("research"), false);

const hidden = context.model(account(all), false, { items: { finance: { hidden: true } } }, "research_lab");
assert.equal(ids(hidden.administrative).includes("finance"), false);
assert.equal(ids(hidden.routeItems).includes("finance"), false);
const explicitEmpty = context.model(account([]), true, {}, "research_lab");
assert.equal(explicitEmpty.administrative.length, 0, "A platform title must not bypass an explicit empty business grant");

const biu = context.model(account(all), false, {}, "biu_legal_ethics_case_lab");
assert.equal(biu.main[0].id, "dashboard");
assert.equal(biu.administrative.length, 0);
assert.equal(biu.main[0].label, "案件總覽");
const civilization = context.model(account(all), false, {}, "civilization");
assert.equal(civilization.main[0].id, "civilization");
assert.equal(civilization.administrative.length, 0);
console.log("PASS: research priority, ten grouped workspaces, canonical deep links, warehouse tabs, permission and template boundaries");
