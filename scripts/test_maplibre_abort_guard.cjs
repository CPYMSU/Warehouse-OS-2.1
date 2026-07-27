#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(
  path.join(root, "frontend", "v2", "maplibre-abort-guard.js"),
  "utf8",
);

const listeners = new Map();
const consoleCalls = [];
const fakeConsole = {
  error(...args) {
    consoleCalls.push(args);
  },
};
const fakeWindow = {
  console: fakeConsole,
  addEventListener(type, listener) {
    listeners.set(type, listener);
  },
};

vm.runInNewContext(source, {
  window: fakeWindow,
  globalThis: fakeWindow,
  console: fakeConsole,
  Array,
  String,
  RegExp,
});

const benign = {
  name: "AbortError",
  message: "signal is aborted without reason",
  stack: "AbortError: signal is aborted without reason\n at de._remove (style.ts:1557)\n at Map.remove (map.ts:3248)",
};
const unrelatedAbort = {
  name: "AbortError",
  message: "The operation was aborted",
  stack: "AbortError: The operation was aborted\n at uploadFile (uploader.js:20)",
};
const realMapError = {
  name: "Error",
  message: "Map style JSON is invalid",
  stack: "Error: Map style JSON is invalid\n at setStyle (style.ts:100)",
};

assert.equal(fakeWindow.__W2_IS_BENIGN_MAPLIBRE_ABORT(benign), true);
assert.equal(fakeWindow.__W2_IS_BENIGN_MAPLIBRE_ABORT(unrelatedAbort), false);
assert.equal(fakeWindow.__W2_IS_BENIGN_MAPLIBRE_ABORT(realMapError), false);

const rejectionHandler = listeners.get("unhandledrejection");
assert.equal(typeof rejectionHandler, "function");

const benignEvent = {
  reason: benign,
  prevented: false,
  stopped: false,
  preventDefault() {
    this.prevented = true;
  },
  stopImmediatePropagation() {
    this.stopped = true;
  },
};
rejectionHandler(benignEvent);
assert.equal(benignEvent.prevented, true);
assert.equal(benignEvent.stopped, true);

const realEvent = {
  reason: realMapError,
  prevented: false,
  stopped: false,
  preventDefault() {
    this.prevented = true;
  },
  stopImmediatePropagation() {
    this.stopped = true;
  },
};
rejectionHandler(realEvent);
assert.equal(realEvent.prevented, false);
assert.equal(realEvent.stopped, false);

fakeConsole.error(benign);
assert.equal(consoleCalls.length, 0);

fakeConsole.error(realMapError);
assert.equal(consoleCalls.length, 1);
assert.equal(consoleCalls[0][0], realMapError);

process.stdout.write("MapLibre teardown guard tests passed.\n");
