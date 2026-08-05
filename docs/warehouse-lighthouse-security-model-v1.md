# Warehouse × Lighthouse security model v1

## Trust boundaries

- The browser trusts Warehouse for account identity and the user's selected
  device, but it is not a device credential holder.
- Warehouse can offer goals and retain redacted projections. It cannot bypass
  Lighthouse's local policy, Operation, confirmation, or Receipt machinery.
- Lighthouse trusts a Warehouse offer only after authenticating its outbound WSS
  session. It treats all goal text as untrusted input.
- Enterprise Warehouse capabilities and local desktop capabilities are distinct
  authorities. No credential is copied from one side to the other.

## MVP invariants

1. A device is private to the Warehouse user that paired it.
2. Pairing codes expire after ten minutes, are consumed once, and are stored only
   as peppered SHA-256 HMAC digests.
3. Device tokens are shown once, stored only as peppered digests on Warehouse,
   and can be revoked independently.
4. The device makes the network connection; Warehouse requires no inbound device
   address, SSH key, Tailscale membership, or port forwarding.
5. Warehouse sends a natural-language goal plus `read_only` policy. It does not
   send shell commands or local capability arguments.
6. Device events and Receipt projections are append-only and idempotent.
7. Local secret values, screenshots, file contents, model context, and full
   Receipts are excluded from telemetry unless a later, explicit sharing policy
   permits a specifically redacted field.
8. Disconnect does not weaken policy. An unacknowledged outbox message can be
   replayed; an already-recorded event cannot be applied twice.

## Later write-capable phase

Write support requires all of the following before it can be enabled:

- an immutable, canonical Operation representation and SHA-256 digest generated
  by Lighthouse;
- a Warehouse WebAuthn/passkey assertion bound to device ID, Run ID, Operation
  digest, user, tenant, expiry, and a single-use challenge;
- Lighthouse-side verification of the signed approval claim before execution;
- a Receipt linking the Operation digest, approval proof digest, outcome, and
  local audit chain;
- revocation, expiry, replay, edited-operation, wrong-device, and offline tests.

The browser confirmation card is only a projection. Editing parameters creates a
new Operation and invalidates any approval for the previous digest.
