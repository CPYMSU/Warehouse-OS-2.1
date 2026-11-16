// Run npm install in scripts/tests, then npm run test:credential-delivery.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const React = require('react');
const Test = require('react-test-renderer');
const Babel = require('../../frontend/v2/vendor/babel.min.js');
const src = fs.readFileSync(path.join(__dirname, '../../frontend/v2/core.jsx'), 'utf8');
const bubble = src.slice(src.indexOf('const CredentialBubble ='), src.indexOf('const RECORD_ACTION_TERMINAL_STATUSES'));
const card = src.slice(src.indexOf('const OperationConfirmation ='), src.indexOf('/* ── Workflow Repair Plan'));
const deliveryId = 'acd_' + 'x'.repeat(25);
const delivery = {action_id: 60, delivery_id: deliveryId, fetch_path: '/fetch', ack_path: '/ack'};
const action = {id: 60, action_key: 'command:60', status: 'completed', revision: 4, credential_deliveries: [delivery]};
let releaseFetch;
const fetchResult = new Promise(resolve => { releaseFetch = resolve; });
let acked = 0, ackFails = true, emitted = [], lock = [];
const sandbox = {
  React, window: {W2_LANG: {t: s => s}, addEventListener() {}, removeEventListener() {}, dispatchEvent() {}},
  document: {visibilityState: 'visible', addEventListener() {}, removeEventListener() {}},
  navigator: {clipboard: {writeText: async () => {}}},
  setTimeout: () => 1, clearTimeout() {}, CustomEvent: function () {},
  W2: {json: async () => ({action}), post: async url => {
    if (url === '/fetch') return fetchResult;
    if (url === '/ack') { acked++; if (ackFails) throw Error('synthetic failure'); return {ok: true, status: 'acked', plaintext_destroyed: true, delivery_id: deliveryId}; }
    throw Error('unexpected endpoint');
  }},
  secretaryCredentialClientId: () => 'test-client',
  secretaryCredentialDeliveryEnvelope: d => d,
  operationCredentialDeliveries: (source, next) => next.credential_deliveries || [],
  operationConfirmationAction: source => source && (source.action || source),
  operationConfirmationId: a => a.id,
  operationProjectedStatus: a => a.status,
  operationCompletionReceipt: () => null,
  operationEditDraft: () => ({}), operationEditableFields: () => [],
  operationCredentialReceipt: () => null, shouldApplyOperationAction: () => true,
  operationText: x => String(x ?? ''), operationStatusLabel: s => s,
  OPERATION_TERMINAL_STATUSES: new Set(['completed']),
  OPERATION_KNOWN_STATUSES: new Set(['completed']),
  Icon: () => null, Icon2: () => null,
};
const code = Babel.transform(`${bubble}\n${card}\nthis.TestCard = OperationConfirmation;`, {presets: ['react']}).code;
vm.runInNewContext(code, sandbox);

(async () => {
  let root;
  await Test.act(async () => {
    root = Test.create(React.createElement(sandbox.TestCard, {
      confirmation: {action}, inlineCredentials: true,
      onCredentialStateChange: value => lock.push(value),
      onTerminal: value => emitted.push(value),
    }));
    await Promise.resolve();
  });
  assert(lock.includes(true), 'pending credential prevents closing before fetch');
  assert.equal(root.root.findAllByProps({'data-credential-delivery': `${deliveryId}:0`}).length, 0);
  await Test.act(async () => {
    releaseFetch({ok: true, action_key: action.action_key, credential_delivery: delivery,
      requires_ack: true, credentials: [{value: 'synthetic-test-secret', action_key: action.action_key}]});
    await fetchResult;
    await Promise.resolve();
  });
  assert.equal(root.root.findAllByProps({'data-credential-delivery': `${deliveryId}:0`}).length, 1, 'credential card survives prior completion event');
  assert(!JSON.stringify(emitted).includes('synthetic-test-secret'), 'secret never enters terminal callbacks');
  const show = root.root.findAllByType('button').find(b => b.children.includes('揭示'));
  await Test.act(async () => show.props.onClick());
  assert(JSON.stringify(root.toJSON()).includes('synthetic-test-secret'), 'reveal displays delivered credential');
  const clear = root.root.findAllByType('button').find(b => b.children.includes('已安全保存，清除'));
  await Test.act(async () => { await clear.props.onClick(); });
  assert.equal(root.root.findAllByProps({'data-credential-delivery': `${deliveryId}:0`}).length, 1, 'failed acknowledgement retains card');
  assert.equal(lock.at(-1), true);
  ackFails = false;
  await Test.act(async () => { await clear.props.onClick(); });
  assert.equal(acked, 2);
  assert.equal(root.root.findAllByProps({'data-credential-delivery': `${deliveryId}:0`}).length, 0);
  assert.equal(lock.at(-1), false, 'successful acknowledgement unlocks closing');
  root.unmount();
  process.stdout.write('business credential delivery passed\n');
})().catch(error => { console.error(error); process.exitCode = 1; });
