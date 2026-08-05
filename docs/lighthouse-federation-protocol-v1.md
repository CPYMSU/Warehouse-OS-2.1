# Warehouse × Lighthouse Federation v1

Status: implementation contract for the first read-only vertical slice.

The federation connects a user's Lighthouse desktop runtime to Warehouse without
opening an inbound port on the device. Lighthouse establishes an outbound WSS
connection over port 443. Warehouse sends a natural-language goal and a bounded
policy; it never sends shell text, mouse instructions, or a serialized local
capability invocation.

## Namespace and envelope

Every WebSocket message uses the namespace
`warehouse-lighthouse-federation/v1` and this envelope:

```json
{
  "protocol": "warehouse-lighthouse-federation/v1",
  "message_id": "UUID",
  "type": "run.offer",
  "sent_at": "RFC3339 timestamp",
  "payload": {}
}
```

`message_id` is an idempotency key. Receivers must accept duplicate delivery and
must not repeat the represented state transition.

## Warehouse to Lighthouse

- `run.offer`: contains `run_id`, `goal`, optional `conversation_ref` and
  `workspace_ref`, and `policy`. In v1 the policy is always
  `{ "mode": "read_only", "allow_local_write": false }`.
- `run.input`: adds user text to an accepted local Run.
- `run.cancel`: requests cooperative cancellation.
- `message.ack`: confirms that Lighthouse-to-Warehouse outbox data was durably
  accepted by Warehouse.
- `operation.approval_granted` and `operation.approval_denied` are reserved by
  the wire contract. Warehouse does not issue a grant in the read-only MVP.

## Lighthouse to Warehouse

- `instance.hello`: safe instance metadata, protocol version, local workspace
  references, and capability descriptors. It never contains local secrets.
- `instance.heartbeat`: liveness and current load.
- `run.accepted` / `run.rejected`: disposition of one offer.
- `run.event`: an append-only local Run event with a stable `event_id`.
- `operation.approval_required`: immutable Operation digest and a redacted
  human-readable projection. The local Operation remains authoritative.
- `receipt.committed`: a redacted Receipt projection and its digest.
- `run.completed`: terminal result or error.
- `message.ack`: confirms that a Warehouse outbox command was handled locally.

Both peers answer durable messages with `message.ack` carrying the received
`message_id`. Merely writing bytes to a socket does not mark an outbox row as
delivered; only the peer acknowledgement does. Duplicate delivery after a
network interruption is therefore expected and idempotent.

## Pairing and connection

1. An authenticated Warehouse user creates a ten-minute pairing challenge.
2. The user enters the one-time code in Lighthouse.
3. Lighthouse exchanges it for a device ID and a device bearer token. Warehouse
   stores only a peppered digest of both pairing codes and device tokens.
4. Lighthouse stores the token in the operating-system credential store and
   opens `/api/lighthouse/device/v1/connect` using `Authorization: Bearer ...`.
5. On reconnect, Warehouse replays undelivered outbox messages. Device events are
   de-duplicated by `(run_id, event_id)`.

## Authority boundary

Lighthouse remains the device authority: its local Main AI plans, selects local
capabilities, creates immutable Operations, owns confirmation state, commits the
full Receipt, and decides whether a task can run. Warehouse is the remote console,
identity/pairing service, durable relay, audit projection, and optional cloud model
gateway.

The server may display and relay a local approval request, but a future write-capable
version must bind a passkey proof to the exact Operation digest and expiry. A grant
must never authorize a changed Operation. Until that proof path ships, remote Runs
are read-only and no remote approval grant is accepted.
