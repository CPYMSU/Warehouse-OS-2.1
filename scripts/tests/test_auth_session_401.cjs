const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const core = fs.readFileSync(path.resolve(__dirname, '../../frontend/v2/core.jsx'), 'utf8');
const end = core.indexOf('/* ── 預警提示音');
assert.ok(end > 0, 'API block boundary is present');

function harness(fetch, token = 'old-token') {
  const values = new Map([['warehouse_auth_token', token], ['warehouse_current_tenant', 'bonfire']]);
  const events = [];
  const localStorage = {
    getItem: key => values.get(key) || null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: key => values.delete(key),
  };
  const window = { location: { href: 'https://bonfirework.org/#/research', origin: 'https://bonfirework.org' },
    atob: value => Buffer.from(value, 'base64').toString('binary'),
    setTimeout: (fn, ms) => { const timer = setTimeout(fn, ms); if (ms > 10000) timer.unref(); return timer; },
    clearTimeout, dispatchEvent: event => events.push(event.type) };
  const context = {window, localStorage, Headers, URL, Event, AbortController, DOMException, fetch};
  vm.runInNewContext(core.slice(0, end) + '\n})();', context, {filename: 'core.jsx'});
  return {W2: window.W2, events};
}

const status = value => ({status: value, ok: value >= 200 && value < 300});
const jwt = (seconds, sub = 'user-1', tenantId = 'tenant-1') =>
  'header.' + Buffer.from(JSON.stringify({sub, tenant_id: tenantId, exp: Math.floor(Date.now() / 1000) + seconds})).toString('base64url') + '.signature';
const refreshed = token => ({...status(200), json: async () => ({token, tenant: 'bonfire'})});
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return {promise, resolve}; };

test('business 401 preserves a valid session and returns the original response', async () => {
  const calls = [];
  const h = harness(async path => { calls.push(path); return status(path === '/api/auth/me' ? 200 : 401); });
  const result = await h.W2.fetch('/api/research/example', {method: 'POST'});
  assert.equal(result.status, 401);
  assert.equal(h.W2.token(), 'old-token');
  assert.deepEqual(h.events, []);
  assert.deepEqual(calls, ['/api/research/example', '/api/auth/me']);
});

test('verified expiry clears only the matching session once', async () => {
  let checks = 0;
  const h = harness(async path => { if (path === '/api/auth/me') checks++; return status(401); });
  await h.W2.fetch('/api/research/example', {method: 'POST'});
  assert.equal(checks, 1);
  assert.equal(h.W2.token(), '');
  assert.deepEqual(h.events, ['w2-auth-expired']);
});

test('both expired bearer and unavailable refresh are required to sign out', async () => {
  let authChecks = 0, refreshes = 0;
  const oldToken = jwt(3600);
  const h = harness(async path => {
    if (path === '/api/auth/me') authChecks++;
    if (path === '/api/auth/refresh') refreshes++;
    return status(401);
  }, oldToken);
  await h.W2.fetch('/api/research/example', {method: 'POST'});
  assert.equal(authChecks, 1); assert.equal(refreshes, 1);
  assert.equal(h.W2.token(), ''); assert.deepEqual(h.events, ['w2-auth-expired']);
});

test('auth/me is itself authoritative and does not recursively probe', async () => {
  let checks = 0;
  const h = harness(async () => { checks++; return status(401); });
  await h.W2.fetch('/api/auth/me');
  assert.equal(checks, 1);
  assert.equal(h.W2.token(), '');
  assert.deepEqual(h.events, ['w2-auth-expired']);
});

test('network or server failure when checking identity does not sign out', async () => {
  for (const probe of [() => status(503), () => { throw new Error('offline'); }]) {
    const h = harness(async path => path === '/api/auth/me' ? probe() : status(401));
    assert.equal((await h.W2.fetch('/api/research/example', {method: 'POST'})).status, 401);
    assert.equal(h.W2.token(), 'old-token');
    assert.deepEqual(h.events, []);
  }
});

test('a late 401 from an old request cannot clear a newer token or tenant', async () => {
  const pending = deferred(); let checks = 0;
  const h = harness(async path => { if (path === '/api/auth/me') checks++; return pending.promise; });
  const request = h.W2.fetch('/api/research/example', {method: 'POST'});
  h.W2.setToken('new-token'); h.W2.setTenant('new-tenant');
  pending.resolve(status(401));
  assert.equal((await request).status, 401);
  assert.equal(h.W2.token(), 'new-token');
  assert.equal(checks, 0);
  assert.deepEqual(h.events, []);
});

test('identity changed during the verification is never cleared', async () => {
  const probe = deferred(), started = deferred();
  const h = harness(async path => { if (path === '/api/auth/me') { started.resolve(); return probe.promise; } return status(401); });
  const request = h.W2.fetch('/api/research/example', {method: 'POST'});
  await started.promise;
  h.W2.setToken('new-token');
  probe.resolve(status(401));
  await request;
  assert.equal(h.W2.token(), 'new-token');
  assert.deepEqual(h.events, []);
});

test('parallel 401 responses share one verification and never replay writes', async () => {
  const probe = deferred(), started = deferred(); let checks = 0, writes = 0;
  const h = harness(async path => {
    if (path === '/api/auth/me') { checks++; started.resolve(); return probe.promise; }
    writes++; return status(401);
  });
  const requests = [h.W2.fetch('/api/research/a', {method: 'POST'}), h.W2.fetch('/api/research/b', {method: 'POST'})];
  await started.promise; await Promise.resolve();
  probe.resolve(status(401));
  await Promise.all(requests);
  assert.equal(checks, 1); assert.equal(writes, 2);
  assert.equal(h.W2.token(), ''); assert.deepEqual(h.events, ['w2-auth-expired']);
});

test('failed login and external 401 do not clear an existing session', async () => {
  let checks = 0;
  const h = harness(async path => { if (path === '/api/auth/me') checks++; return status(401); });
  await h.W2.fetch('/api/auth/login', {method: 'POST'});
  await h.W2.fetch('https://other.example/image', {method: 'POST'});
  assert.equal(checks, 0); assert.equal(h.W2.token(), 'old-token'); assert.deepEqual(h.events, []);
});

test('near-expiry token refreshes before a write, without replaying it', async () => {
  const oldToken = jwt(60), newToken = jwt(3600); let writes = 0, refreshes = 0;
  const h = harness(async (path, options) => {
    if (path === '/api/auth/refresh') {
      refreshes++;
      assert.equal(options.credentials, 'same-origin');
      assert.deepEqual(JSON.parse(options.body), {tenant: 'bonfire'});
      return refreshed(newToken);
    }
    writes++; assert.equal(options.headers.get('Authorization'), 'Bearer ' + newToken);
    return status(200);
  }, oldToken);
  assert.equal((await h.W2.fetch('/api/research/example', {method: 'PUT', body: '{}'})).status, 200);
  assert.equal(writes, 1); assert.equal(refreshes, 1); assert.equal(h.W2.token(), newToken);
});

test('expired token is restored from the cookie before an ordinary request', async () => {
  const oldToken = jwt(-1), newToken = jwt(3600);
  const h = harness(async (path, options) => path === '/api/auth/refresh' ? refreshed(newToken) :
    (assert.equal(options.headers.get('Authorization'), 'Bearer ' + newToken), status(200)), oldToken);
  assert.equal((await h.W2.fetch('/api/research/example')).status, 200);
  assert.equal(h.W2.token(), newToken); assert.deepEqual(h.events, []);
});

test('GET that expires in flight refreshes and retries only once', async () => {
  const oldToken = jwt(3600), newToken = jwt(3601); let calls = 0, refreshes = 0;
  const h = harness(async path => {
    if (path === '/api/auth/me') return status(401);
    if (path === '/api/auth/refresh') { refreshes++; return refreshed(newToken); }
    calls++; return status(calls === 1 ? 401 : 200);
  }, oldToken);
  assert.equal((await h.W2.fetch('/api/research/example')).status, 200);
  assert.equal(calls, 2); assert.equal(refreshes, 1); assert.equal(h.W2.token(), newToken);
  assert.deepEqual(h.events, []);
});

test('write that expires in flight is never replayed after successful refresh', async () => {
  const oldToken = jwt(3600), newToken = jwt(3601); let writes = 0;
  const h = harness(async path => {
    if (path === '/api/auth/me') return status(401);
    if (path === '/api/auth/refresh') return refreshed(newToken);
    writes++; return status(401);
  }, oldToken);
  assert.equal((await h.W2.fetch('/api/research/example', {method: 'POST'})).status, 401);
  assert.equal(writes, 1); assert.equal(h.W2.token(), newToken); assert.deepEqual(h.events, []);
});

test('refresh network failure keeps an expired token and does not submit a write', async () => {
  let writes = 0;
  const oldToken = jwt(-1);
  const h = harness(async path => { if (path === '/api/auth/refresh') throw new Error('offline'); writes++; return status(200); }, oldToken);
  await assert.rejects(h.W2.fetch('/api/research/example', {method: 'POST'}), error => error.status === 503 && error.code === 'AUTH_REFRESH_UNAVAILABLE');
  assert.equal(writes, 0); assert.equal(h.W2.token(), oldToken); assert.deepEqual(h.events, []);
});

test('a 401 followed by transient refresh failure preserves the login', async () => {
  const oldToken = jwt(3600);
  const h = harness(async path => {
    if (path === '/api/auth/refresh') return status(503);
    return status(401);
  }, oldToken);
  await assert.rejects(h.W2.fetch('/api/auth/me'), error => error.status === 503 && error.code === 'AUTH_REFRESH_UNAVAILABLE');
  assert.equal(h.W2.token(), oldToken); assert.equal(h.W2.tenant(), 'bonfire'); assert.deepEqual(h.events, []);
});

test('concurrent near-expiry requests share one cookie refresh', async () => {
  const oldToken = jwt(60), newToken = jwt(3600), pending = deferred(), started = deferred(); let refreshes = 0;
  const h = harness(async path => { if (path === '/api/auth/refresh') { refreshes++; started.resolve(); return pending.promise; } return status(200); }, oldToken);
  const a = h.W2.fetch('/api/research/a'), b = h.W2.fetch('/api/research/b');
  await started.promise; pending.resolve(refreshed(newToken));
  assert.equal((await a).status, 200); assert.equal((await b).status, 200);
  assert.equal(refreshes, 1); assert.equal(h.W2.token(), newToken);
});

test('late refresh cannot resurrect a session after logout or overwrite another account', async () => {
  for (const mutation of ['logout', 'account', 'tenant']) {
    const oldToken = jwt(60), next = jwt(3600), pending = deferred(), started = deferred();
    const h = harness(async path => { assert.equal(path, '/api/auth/refresh'); started.resolve(); return pending.promise; }, oldToken);
    const refresh = h.W2.refreshSession(); await started.promise;
    if (mutation === 'logout') { h.W2.setToken(''); h.W2.setTenant(''); }
    else if (mutation === 'account') h.W2.setToken(jwt(3600, 'different-user'));
    else h.W2.setTenant('another-tenant');
    const expectedToken = h.W2.token(), expectedTenant = h.W2.tenant();
    pending.resolve(refreshed(next));
    assert.equal(await refresh, 'superseded');
    assert.equal(h.W2.token(), expectedToken); assert.equal(h.W2.tenant(), expectedTenant);
  }
});

test('refresh response for a different identity is rejected', async () => {
  const oldToken = jwt(60);
  const h = harness(async () => refreshed(jwt(3600, 'different-user')), oldToken);
  assert.equal(await h.W2.refreshSession(), 'transient');
  assert.equal(h.W2.token(), oldToken);
});

test('missing legacy cookie does not repeatedly attempt refresh before expiration', async () => {
  const oldToken = jwt(60); let refreshes = 0;
  const h = harness(async path => { if (path === '/api/auth/refresh') { refreshes++; return status(401); } return status(200); }, oldToken);
  await h.W2.fetch('/api/research/a'); await h.W2.fetch('/api/research/b');
  assert.equal(refreshes, 1); assert.equal(h.W2.token(), oldToken); assert.deepEqual(h.events, []);
});

test('cross-origin requests do not receive the account bearer or tenant', async () => {
  const h = harness(async (_path, options) => {
    assert.equal(options.headers.has('Authorization'), false);
    assert.equal(options.headers.has('X-Tenant-Slug'), false);
    assert.equal(options.headers.get('X-Explicit'), 'permitted');
    return status(200);
  }, jwt(3600));
  await h.W2.fetch('https://other.example/image', {headers: {'X-Explicit': 'permitted'}});
});
