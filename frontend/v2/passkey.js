/* ============================================================
   WAREHOUSE 2.0 · Passkey / WebAuthn browser adapter

   The server remains authoritative for challenges, RP binding, user
   verification and replay prevention.  This module only converts the JSON
   WebAuthn wire format and exposes a small, fail-closed browser API.
   ============================================================ */
(function () {
  "use strict";

  var W2 = window.W2 = window.W2 || {};
  var API = "/api/auth/passkeys";
  var CAPABILITY_PROBE_TIMEOUT_MS = 1800;
  var LOCAL_EN = {
    "伺服器返回了無效的 Passkey 資料。": "The server returned invalid passkey data.",
    "瀏覽器返回了無效的 Passkey 憑證。": "The browser returned an invalid passkey credential.",
    "瀏覽器沒有返回 Passkey 憑證。": "The browser did not return a passkey credential.",
    "伺服器沒有返回 Passkey 挑戰。": "The server did not return a passkey challenge.",
    "驗證已取消、逾時，或此裝置沒有可用的 Passkey。": "Verification was cancelled, timed out, or no passkey is available on this device.",
    "Passkey 驗證已取消。": "Passkey verification was cancelled.",
    "這個 Passkey 已在帳號中登記。": "This passkey is already registered to the account.",
    "此瀏覽器或裝置不支援目前的 Passkey 設定。": "This browser or device does not support the current passkey options.",
    "Passkey 嘗試次數過多，請稍候再試。": "Too many passkey attempts. Wait a moment and try again.",
    "Passkey 只能在安全的 HTTPS 網站及正確網域使用。": "Passkeys require the approved secure HTTPS site.",
    "裝置無法完成必要的本人驗證。": "The device could not complete the required user verification.",
    "裝置未能完成 Passkey 操作，請重試或改用密碼。": "The device could not complete the passkey operation. Retry or use your password.",
    "Passkey 操作失敗，請重試或改用密碼。": "The passkey operation failed. Retry or use your password.",
    "此瀏覽器或目前連線不支援 Passkey，請使用密碼登入。": "Passkeys are unavailable in this browser or connection. Use your password to sign in.",
    "登入挑戰缺少 request_id。": "The sign-in challenge is missing request_id.",
    "註冊挑戰缺少 request_id。": "The registration challenge is missing request_id.",
    "缺少要移除的 Passkey 編號。": "The passkey ID to remove is missing.",
    "高風險操作必須綁定具體資源。": "A high-risk action must be bound to a specific resource.",
    "操作資源無法安全序列化。": "The action resource could not be serialized safely.",
    "高風險操作缺少用途。": "The high-risk action is missing its purpose.",
    "二次驗證挑戰缺少 request_id。": "The step-up challenge is missing request_id.",
    "二次驗證沒有返回一次性授權憑證。": "Step-up verification did not return a one-time authorization token.",
  };
  var translationsInstalled = false;
  function installTranslations() {
    if (!translationsInstalled && window.W2_LANG && typeof window.W2_LANG.addEN === "function") {
      window.W2_LANG.addEN(LOCAL_EN);
      translationsInstalled = true;
    }
  }
  installTranslations();

  function tr(message) {
    installTranslations();
    return window.W2_LANG && typeof window.W2_LANG.t === "function" ? window.W2_LANG.t(message) : message;
  }

  function bytesFromBase64url(value) {
    if (value instanceof ArrayBuffer) return value;
    if (ArrayBuffer.isView(value)) {
      return value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength);
    }
    if (typeof value !== "string" || !value) throw passkeyError("invalid_options", "伺服器返回了無效的 Passkey 資料。");
    var normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    while (normalized.length % 4) normalized += "=";
    var binary;
    try { binary = window.atob(normalized); }
    catch (error) { throw passkeyError("invalid_options", "伺服器返回了無效的 Passkey 資料。", error); }
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
  }

  function base64urlFromBytes(value) {
    if (value == null) return null;
    var bytes;
    if (value instanceof ArrayBuffer) bytes = new Uint8Array(value);
    else if (ArrayBuffer.isView(value)) bytes = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
    else throw passkeyError("invalid_credential", "瀏覽器返回了無效的 Passkey 憑證。");
    var binary = "";
    /* Small chunks avoid a call-stack overflow for large attestation blobs. */
    for (var offset = 0; offset < bytes.length; offset += 0x8000) {
      binary += String.fromCharCode.apply(null, bytes.subarray(offset, Math.min(offset + 0x8000, bytes.length)));
    }
    return window.btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  }

  function passkeyError(code, message, cause) {
    var error = new Error(tr(message));
    error.code = code;
    if (cause) error.cause = cause;
    return error;
  }

  function supported() {
    var local = location.hostname === "localhost" || location.hostname === "127.0.0.1";
    return !!(window.PublicKeyCredential && navigator.credentials && navigator.credentials.get && navigator.credentials.create && (window.isSecureContext || local));
  }

  function probeCapability(methodName, timeoutMs) {
    var method = window.PublicKeyCredential && window.PublicKeyCredential[methodName];
    if (typeof method !== "function") {
      return Promise.resolve({ available: false, known: false, timedOut: false });
    }
    return new Promise(function (resolve) {
      var settled = false;
      var timer = window.setTimeout(function () {
        finish({ available: false, known: false, timedOut: true });
      }, timeoutMs);
      function finish(value) {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        resolve(value);
      }
      try {
        Promise.resolve(method.call(window.PublicKeyCredential)).then(
          function (available) { finish({ available: !!available, known: true, timedOut: false }); },
          function () { finish({ available: false, known: false, timedOut: false }); }
        );
      } catch (error) {
        finish({ available: false, known: false, timedOut: false });
      }
    });
  }

  async function capabilities(probeTimeoutMs) {
    var timeoutMs = typeof probeTimeoutMs === "number" && probeTimeoutMs >= 0
      ? probeTimeoutMs : CAPABILITY_PROBE_TIMEOUT_MS;
    var result = {
      supported: supported(), secure: !!window.isSecureContext,
      platform: false, platformKnown: false, platformTimedOut: false,
      conditional: false, conditionalKnown: false, conditionalTimedOut: false,
      /* Aggregate retained for older callers; UI decisions should use the
         capability-specific timeout fields below. */
      probeTimedOut: false,
    };
    if (!result.supported) return result;
    /* Chromium delegates platform discovery to optional browser/OS capability
       providers, whose promise may be slow or never settle.  Probe in parallel
       and never let it gate the standards-based credentials.create/get paths. */
    var probes = await Promise.all([
      probeCapability("isUserVerifyingPlatformAuthenticatorAvailable", timeoutMs),
      probeCapability("isConditionalMediationAvailable", timeoutMs),
    ]);
    result.platform = probes[0].available;
    result.platformKnown = probes[0].known;
    result.platformTimedOut = probes[0].timedOut;
    result.conditional = probes[1].available;
    result.conditionalKnown = probes[1].known;
    result.conditionalTimedOut = probes[1].timedOut;
    result.probeTimedOut = result.platformTimedOut || result.conditionalTimedOut;
    return result;
  }

  function unwrapOptions(payload) {
    if (!payload || typeof payload !== "object") throw passkeyError("invalid_options", "伺服器沒有返回 Passkey 挑戰。");
    var wrapped = payload.options || payload.public_key || payload.publicKey || payload;
    return wrapped && wrapped.publicKey ? wrapped.publicKey : wrapped;
  }

  function requestIdOf(payload) {
    return payload && (payload.request_id || payload.challenge_id || payload.requestId) || "";
  }

  function credentialDescriptors(rows) {
    return Array.isArray(rows) ? rows.map(function (row) {
      return Object.assign({}, row, { id: bytesFromBase64url(row.id) });
    }) : rows;
  }

  function credentialMode(options) {
    var mode = options && options.mode ? String(options.mode) : "auto";
    if (["auto", "platform", "hybrid"].indexOf(mode) < 0) {
      throw passkeyError("invalid_mode", "此瀏覽器或裝置不支援目前的 Passkey 設定。");
    }
    return mode;
  }

  function reportStatus(options, stage) {
    if (!options || typeof options.onStatus !== "function") return;
    try { options.onStatus(stage); } catch (error) { /* UI status cannot break WebAuthn. */ }
  }

  function stagedError(error, stage) {
    var mapped = friendlyError(error);
    try { if (mapped && !mapped.passkeyStage) mapped.passkeyStage = stage; } catch (ignored) {}
    return mapped;
  }

  function fallbackTimeout(options) {
    var configured = Number(options && options.platformTimeoutMs);
    if (!Number.isFinite(configured) || configured <= 0) return 30000;
    return Math.min(configured, 120000);
  }

  function cancellationError(signal) {
    var reason = signal && signal.reason;
    if (reason && reason.name === "AbortError") return reason;
    if (typeof window.DOMException === "function") return new window.DOMException(tr("Passkey 驗證已取消。"), "AbortError");
    var error = new Error(tr("Passkey 驗證已取消。"));
    error.name = "AbortError";
    return error;
  }

  /* Run the local authenticator first, then switch to the browser's native
     nearby-phone flow only after that ceremony has fully aborted.  A user
     cancellation is deliberately not a fallback signal: NotAllowedError can
     mean that the user declined the ceremony and must remain fail-closed. */
  async function authenticatorCredential(kind, payload, requireVerification, mode, options, setStage) {
    var buildOptions = kind === "create"
      ? function (nextMode) { return creationOptions(payload, nextMode); }
      : function (nextMode) { return requestOptions(payload, requireVerification, nextMode); };
    var operationSignal = options && options.signal;
    if (operationSignal && operationSignal.aborted) throw cancellationError(operationSignal);
    var fallbackEnabled = mode === "platform" && !!(options && options.fallbackToHybrid);
    if (!fallbackEnabled || typeof window.AbortController !== "function") {
      setStage("authenticator");
      if (!operationSignal || typeof window.AbortController !== "function") {
        var uncancellableCredential = await navigator.credentials[kind]({ publicKey: buildOptions(mode) });
        if (operationSignal && operationSignal.aborted) throw cancellationError(operationSignal);
        return uncancellableCredential;
      }
      var directController = new window.AbortController();
      var cancelDirect = function () { try { directController.abort(); } catch (ignored) {} };
      operationSignal.addEventListener("abort", cancelDirect, { once: true });
      try {
        var directCredential = await navigator.credentials[kind]({ publicKey: buildOptions(mode), signal: directController.signal });
        if (operationSignal.aborted) throw cancellationError(operationSignal);
        return directCredential;
      } finally {
        operationSignal.removeEventListener("abort", cancelDirect);
      }
    }

    var controller = new window.AbortController();
    var fallbackReason = "";
    var settled = false;
    var operationCancelled = false;
    var switchSignal = options && options.fallbackSignal;
    var cancelOperation = function () {
      if (settled || operationCancelled) return;
      operationCancelled = true;
      try { controller.abort(); } catch (ignored) {}
    };
    var requestFallback = function (reason) {
      if (settled || operationCancelled || fallbackReason) return;
      fallbackReason = reason;
      try { controller.abort(); } catch (ignored) {}
    };
    var switchListener = function () { requestFallback("switch"); };
    var timer = window.setTimeout(function () { requestFallback("timeout"); }, fallbackTimeout(options));
    if (switchSignal && typeof switchSignal.addEventListener === "function") {
      if (switchSignal.aborted) switchListener();
      else switchSignal.addEventListener("abort", switchListener, { once: true });
    }
    if (operationSignal && typeof operationSignal.addEventListener === "function") {
      if (operationSignal.aborted) cancelOperation();
      else operationSignal.addEventListener("abort", cancelOperation, { once: true });
    }

    setStage("authenticator-platform");
    try {
      try {
        var credential = await navigator.credentials[kind]({
          publicKey: buildOptions("platform"),
          signal: controller.signal,
        });
        if (operationCancelled) throw cancellationError(operationSignal);
        settled = true;
        return credential;
      } catch (error) {
        /* Only our watchdog/manual switch owns this fallback.  Waiting for
           the first promise to reject prevents overlapping WebAuthn calls. */
        if (operationCancelled) throw cancellationError(operationSignal);
        if (!fallbackReason) throw error;
      }
      setStage(fallbackReason === "timeout" ? "authenticator-hybrid-timeout" : "authenticator-hybrid-switch");
      controller = new window.AbortController();
      if (operationCancelled) controller.abort();
      var hybridCredential = await navigator.credentials[kind]({ publicKey: buildOptions("hybrid"), signal: controller.signal });
      if (operationCancelled) throw cancellationError(operationSignal);
      return hybridCredential;
    } finally {
      settled = true;
      window.clearTimeout(timer);
      if (switchSignal && typeof switchSignal.removeEventListener === "function") {
        switchSignal.removeEventListener("abort", switchListener);
      }
      if (operationSignal && typeof operationSignal.removeEventListener === "function") {
        operationSignal.removeEventListener("abort", cancelOperation);
      }
    }
  }

  function creationOptions(payload, mode) {
    var source = unwrapOptions(payload);
    var publicKey = Object.assign({}, source, {
      challenge: bytesFromBase64url(source.challenge),
      user: Object.assign({}, source.user, { id: bytesFromBase64url(source.user && source.user.id) }),
      excludeCredentials: credentialDescriptors(source.excludeCredentials),
    });
    publicKey.authenticatorSelection = Object.assign({}, source.authenticatorSelection || {}, {
      residentKey: (source.authenticatorSelection && source.authenticatorSelection.residentKey) || "preferred",
      userVerification: "required",
    });
    /* Explicit user choice, rather than a best-effort capability probe, owns
       authenticator routing. Platform covers OS authenticators such as
       Windows Hello and Touch ID; hybrid requests the native nearby-phone UI. */
    if (mode === "platform") {
      publicKey.authenticatorSelection.authenticatorAttachment = "platform";
      publicKey.hints = ["client-device"];
    } else if (mode === "hybrid") {
      publicKey.authenticatorSelection.authenticatorAttachment = "cross-platform";
      publicKey.hints = ["hybrid"];
    }
    return publicKey;
  }

  function requestOptions(payload, requireVerification, mode) {
    var source = unwrapOptions(payload);
    var publicKey = Object.assign({}, source, {
      challenge: bytesFromBase64url(source.challenge),
      allowCredentials: credentialDescriptors(source.allowCredentials),
      userVerification: requireVerification ? "required" : (source.userVerification || "preferred"),
    });
    /* Assertion options have no authenticatorAttachment.  Level 3 hints are
       progressive enhancement and are ignored safely by older browsers. */
    if (mode === "platform") publicKey.hints = ["client-device"];
    else if (mode === "hybrid") publicKey.hints = ["hybrid"];
    return publicKey;
  }

  function serializeCredential(credential) {
    if (!credential || !credential.response) throw passkeyError("invalid_credential", "瀏覽器沒有返回 Passkey 憑證。");
    var response = credential.response;
    var serializedResponse = { clientDataJSON: base64urlFromBytes(response.clientDataJSON) };
    if (response.attestationObject != null) serializedResponse.attestationObject = base64urlFromBytes(response.attestationObject);
    if (response.authenticatorData != null) serializedResponse.authenticatorData = base64urlFromBytes(response.authenticatorData);
    if (response.signature != null) serializedResponse.signature = base64urlFromBytes(response.signature);
    if (response.userHandle != null) serializedResponse.userHandle = base64urlFromBytes(response.userHandle);
    if (typeof response.getTransports === "function") serializedResponse.transports = response.getTransports();
    if (typeof response.getPublicKeyAlgorithm === "function") serializedResponse.publicKeyAlgorithm = response.getPublicKeyAlgorithm();
    return {
      id: credential.id,
      rawId: base64urlFromBytes(credential.rawId),
      type: credential.type,
      authenticatorAttachment: credential.authenticatorAttachment || null,
      response: serializedResponse,
      clientExtensionResults: typeof credential.getClientExtensionResults === "function" ? credential.getClientExtensionResults() : {},
    };
  }

  function friendlyError(error) {
    /* DOMException.code is a legacy numeric value (AbortError is commonly
       20), not one of our stable application error codes. */
    if (error && typeof error.code === "string" && error.code) return error;
    var name = error && error.name || "";
    var messages = {
      NotAllowedError: "驗證已取消、逾時，或此裝置沒有可用的 Passkey。",
      AbortError: "Passkey 驗證已取消。",
      InvalidStateError: "這個 Passkey 已在帳號中登記。",
      NotSupportedError: "此瀏覽器或裝置不支援目前的 Passkey 設定。",
      SecurityError: "Passkey 只能在安全的 HTTPS 網站及正確網域使用。",
      ConstraintError: "裝置無法完成必要的本人驗證。",
      UnknownError: "裝置未能完成 Passkey 操作，請重試或改用密碼。",
    };
    var mapped = error && error.status === 429
      ? "Passkey 嘗試次數過多，請稍候再試。"
      : messages[name] || (error && error.message) || "Passkey 操作失敗，請重試或改用密碼。";
    var result = passkeyError(name || "passkey_failed", mapped, error);
    if (error && error.status != null) result.status = error.status;
    if (error && error.data != null) result.data = error.data;
    return result;
  }

  async function publicPost(path, body) {
    var response = await fetch(W2.API_BASE + path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) {
      var error = new Error(data.error || data.message || response.statusText || "Passkey request failed");
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  function verificationPost(path, body, options) {
    return W2.json(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
      signal: options && options.signal,
      /* Invalid WebAuthn proof is not evidence that the bearer expired. */
      suppressAuthExpired: true,
    });
  }

  function requireSupport() {
    if (!supported()) throw passkeyError("unsupported", "此瀏覽器或目前連線不支援 Passkey，請使用密碼登入。");
  }

  async function login(username, options) {
    var stage = "support";
    var setStage = function (nextStage) {
      stage = nextStage;
      reportStatus(options, stage);
    };
    try {
      requireSupport();
      var mode = credentialMode(options);
      setStage("options");
      var optionsPayload = await publicPost(API + "/login/options", username ? { username: String(username).trim() } : {});
      var requestId = requestIdOf(optionsPayload);
      if (!requestId) throw passkeyError("invalid_options", "登入挑戰缺少 request_id。");
      var credential = await authenticatorCredential("get", optionsPayload, true, mode, options, setStage);
      setStage("verify");
      return await publicPost(API + "/login/verify", { request_id: requestId, credential: serializeCredential(credential) });
    } catch (error) { throw stagedError(error, stage); }
  }

  async function register(name, password, options) {
    var stage = "support";
    var setStage = function (nextStage) {
      stage = nextStage;
      reportStatus(options, stage);
    };
    try {
      requireSupport();
      var mode = credentialMode(options);
      setStage("options");
      var optionsPayload = await W2.post(API + "/register/options", { password: String(password || "") });
      var requestId = requestIdOf(optionsPayload);
      if (!requestId) throw passkeyError("invalid_options", "註冊挑戰缺少 request_id。");
      var credential = await authenticatorCredential("create", optionsPayload, true, mode, options, setStage);
      setStage("verify");
      return await verificationPost(API + "/register/verify", {
        request_id: requestId,
        credential: serializeCredential(credential),
        name: String(name || "").trim() || null,
      });
    } catch (error) { throw stagedError(error, stage); }
  }

  async function list() {
    var data = await W2.json(API);
    return Array.isArray(data) ? data : (data.passkeys || data.credentials || []);
  }

  async function remove(id, password) {
    if (id == null || id === "") throw passkeyError("invalid_credential", "缺少要移除的 Passkey 編號。");
    return await W2.json(API + "/" + encodeURIComponent(String(id)), {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: String(password || "") }),
      suppressAuthExpired: true,
    });
  }

  function cloneResource(resource) {
    if (!resource || typeof resource !== "object" || Array.isArray(resource)) {
      throw passkeyError("invalid_intent", "高風險操作必須綁定具體資源。");
    }
    try { return JSON.parse(JSON.stringify(resource)); }
    catch (error) { throw passkeyError("invalid_intent", "操作資源無法安全序列化。", error); }
  }

  async function requestStepUp(purpose, resource, options) {
    var stage = "support";
    var setStage = function (nextStage) {
      stage = nextStage;
      reportStatus(options, stage);
    };
    try {
      requireSupport();
      var mode = credentialMode(options);
      var normalizedPurpose = String(purpose || "").trim();
      if (!normalizedPurpose) throw passkeyError("invalid_intent", "高風險操作缺少用途。");
      var boundResource = cloneResource(resource);
      var operationSignal = options && options.signal;
      if (operationSignal && operationSignal.aborted) throw cancellationError(operationSignal);
      setStage("options");
      var optionsPayload = await W2.post(
        API + "/step-up/options",
        { purpose: normalizedPurpose, resource: boundResource },
        { signal: operationSignal }
      );
      var requestId = requestIdOf(optionsPayload);
      if (!requestId) throw passkeyError("invalid_options", "二次驗證挑戰缺少 request_id。");
      var credential = await authenticatorCredential("get", optionsPayload, true, mode, options, setStage);
      setStage("verify");
      var result = await verificationPost(API + "/step-up/verify", {
        request_id: requestId,
        credential: serializeCredential(credential),
        purpose: normalizedPurpose,
        resource: boundResource,
      }, { signal: operationSignal });
      if (!result || !result.step_up_token) throw passkeyError("invalid_receipt", "二次驗證沒有返回一次性授權憑證。");
      return result.step_up_token;
    } catch (error) { throw stagedError(error, stage); }
  }

  W2.Passkeys = Object.freeze({
    supported: supported,
    capabilities: capabilities,
    login: login,
    register: register,
    list: list,
    remove: remove,
    requestStepUp: requestStepUp,
    serializeCredential: serializeCredential,
    bytesFromBase64url: bytesFromBase64url,
    base64urlFromBytes: base64urlFromBytes,
    friendlyError: friendlyError,
  });
}());
