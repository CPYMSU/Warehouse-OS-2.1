/* ============================================================
   Empty bootstrap fallback

   Real application data comes from GET /api/bootstrap after login.
   Keep this file free of believable demo rows so failed bootstrap or
   stale auth cannot leak fake grid/material records into tenant pages.
   ============================================================ */

const NAV_CONFIG = { items: {} };
const CUSTOM_MODULES = [];
const WAREHOUSES = ["—"];
const CATEGORIES = [];
const LEDGER_CATEGORIES = [];
const INVENTORY = [];
const ALERTS = [];
const INBOUND = [];
const OUTBOUND = [];
const FAULT_TYPES = [];
const STOCKTAKE = [];
const STOCKTAKE_DIFF = [];
const ZONES = [];
const AI_TASKS = [];
const AI_LOG = [];
const PEOPLE = [];
const ROLES = [];
const FLOW = { title: "—", steps: [] };

Object.assign(window, {
  NAV_CONFIG, CUSTOM_MODULES,
  WAREHOUSES, CATEGORIES, LEDGER_CATEGORIES, INVENTORY, ALERTS, INBOUND, OUTBOUND, FAULT_TYPES,
  STOCKTAKE, STOCKTAKE_DIFF, ZONES, AI_TASKS, AI_LOG, PEOPLE, ROLES, FLOW,
});
