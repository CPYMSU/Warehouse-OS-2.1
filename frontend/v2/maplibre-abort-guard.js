/* Warehouse OS 2.1 · MapLibre teardown guard
 *
 * MapLibre may reject an in-flight style/sprite fetch with AbortError when a
 * React view unmounts and map.remove() deliberately cancels the request. That
 * cancellation is expected lifecycle control, not a user-visible map failure.
 *
 * This guard suppresses only that exact teardown signature. Network failures,
 * style parse errors, WebGL errors and unrelated AbortErrors remain visible.
 */
(function installMapLibreTeardownGuard(global) {
  "use strict";

  function isBenignMapLibreAbort(value) {
    if (!value) return false;

    var name = String(value.name || "");
    var message = String(value.message || value || "");
    var stack = String(value.stack || "");

    return name === "AbortError"
      && /signal\s+is\s+aborted|aborted\s+without\s+reason|operation\s+was\s+aborted/i.test(message)
      && /maplibre|evented\.ts|style\.ts|map\.ts|_loadSprite|_updateStyle|setStyle/i.test(stack);
  }

  global.__W2_IS_BENIGN_MAPLIBRE_ABORT = isBenignMapLibreAbort;

  if (typeof global.addEventListener === "function") {
    global.addEventListener("unhandledrejection", function onUnhandledRejection(event) {
      if (!event || !isBenignMapLibreAbort(event.reason)) return;
      if (typeof event.preventDefault === "function") event.preventDefault();
      if (typeof event.stopImmediatePropagation === "function") event.stopImmediatePropagation();
    });
  }

  var consoleObject = global.console;
  if (!consoleObject || typeof consoleObject.error !== "function") return;

  var originalError = consoleObject.error;
  consoleObject.error = function guardedConsoleError() {
    var args = Array.prototype.slice.call(arguments);
    if (args.some(isBenignMapLibreAbort)) return;
    return originalError.apply(consoleObject, args);
  };
})(typeof window !== "undefined" ? window : globalThis);
