# Shared Runtime API

Warehouse OS exposes the same tenant-isolated execution core used by the
Company Secretary and Super Terminal. An external client does not receive a
second planner, command catalogue, permission snapshot, database connection,
or provider key.

```text
external client / Company Secretary / Super Terminal
        -> shared Runtime ingress
        -> Auto Runtime
        -> the same capability executor and PostgreSQL RLS
        -> the same conversation, command, operation, and audit stores
```

## Issue a credential

An interactively authenticated user may issue a tenant-bound key only for
audiences backed by their current live permissions:

```http
POST /api/assistant/cli-keys
Authorization: Bearer <interactive-session-token>
Content-Type: application/json

{
  "label": "Codex integration test",
  "scopes": ["assistant", "terminal"],
  "expires_in_days": 30
}
```

The response includes a `wsk_...` plaintext key exactly once. PostgreSQL stores
only a domain-separated, server-peppered digest and a non-secret hint.

Keys can be listed without plaintext through `GET /api/assistant/cli-keys` and
revoked through `POST /api/assistant/cli-keys/{id}/revoke`. The aliases
`/api/runtime/keys` and `/api/runtime/keys/{id}` are provided for API clients.
A Runtime key cannot issue, list, or revoke another Runtime key.

Research integrations should use the narrower
`POST /api/research/api-keys` endpoint or `research key issue`. It always
issues for the current user and company with only the `research` audience.
`research cli show` returns the authenticated download contract for the
dependency-free `bonfire-research` client. The client talks directly to the
research routes; granting generic `terminal` scope is neither required nor
recommended for research automation.

## AI Secretary

The exact endpoint used by the web secretary accepts the Runtime key:

```http
POST /api/agent/run/stream
Authorization: Bearer <wsk-key>
Content-Type: application/json

{
  "text": "分析今天的採購待辦並給出下一步",
  "surface": "secretary",
  "context_mode": "balanced",
  "locale": "zh-Hant",
  "language_mode": "auto",
  "conversation_id": null,
  "turn_id": "client-generated-idempotency-key"
}
```

The response is `application/x-ndjson`. It emits `run_start`, live
`runtime_activity` updates, the observable Runtime phases, and `final`.
Activities have stable `activity_id` values, so a client can update one row as
it moves from `running` to `succeeded`, `failed`, `waiting_confirmation`,
`requires_user_input`, `skipped`, or `stopped`. Model-routing activities expose
their phase and model; command activities expose only the command/tool name,
description, round, status, and elapsed time. Arguments, result data, and
secrets are deliberately excluded from this progress channel.

The final activity projection is stored with the assistant message and restored
with conversation history. Reusing the same `turn_id` with the same conversation
replays the durable assistant result rather than executing twice.

### Public-output contract

Every AI surface passes through one server-side public-output boundary. The
model's routing, tool selection, planning, reflection, continuation and language
repair responses are control-plane data, not chat messages.

- Structured control output is parsed first. One bounded format-repair attempt
  is allowed when a provider returns malformed JSON.
- If repair also fails, Runtime stops safely and returns a localized retry
  message. It never substitutes the raw provider response as the answer.
- Progress events expose only allowlisted model/tool names, statuses and timing.
  Prompts, reasoning, arguments and raw tool results remain server-side.
- Confirmation cards retain business results but remove credentials, connection
  strings, prompts, reasoning and raw failure diagnostics. Detailed failures
  remain available to protected audit and Shield workflows.
- New assistant messages are filtered before persistence. Legacy assistant
  messages are filtered again when read, so an older malformed transcript cannot
  reappear after reload or enter a later memory/context capsule.
- Plaintext credentials are the sole exception: they are returned only through
  the existing one-time, browser-bound secure credential card and are never put
  in chat prose, progress events, run snapshots or replayable history.

Protected run snapshots may retain the full control envelope for diagnosis and
audit. That protected representation is deliberately distinct from the public
stream representation.

`context_mode` accepts `balanced` or `thinking`. Balanced requests use
`deepseek-v4-flash` with provider thinking disabled. Thinking requests use
`deepseek-v4-pro` with provider thinking enabled. This changes inference depth,
not the Runtime, command catalogue, authority checks, tenant boundary, or
execution gateway.

`locale` uses one of `zh-Hant`, `zh-Hans`, or `en`. With the default
`language_mode: "auto"`, an explicit language request or a strong language
signal in the current turn wins; an ambiguous turn falls back to the supplied
interface/account locale. `language_mode: "fixed"` always uses the supplied
locale. The resolved locale is returned on `run_start` and `final`, persisted
in message metadata, injected into every user-facing Runtime phase, and checked
before the final answer is emitted. Commands, API fields, identifiers, code,
paths, URLs, citations, numbers, and quoted source text are never translated.

## Super Terminal

The exact endpoint used by the human terminal accepts the same credential when
the key has `terminal` scope and the owner still has `terminal.use`:

```http
POST /api/cli/exec
Authorization: Bearer <wsk-key>
Content-Type: application/json

{"line": "warehouse list"}
```

`GET /api/cli/commands` returns the live catalogue projection. Command
execution still passes argument validation, current-account authorization,
confirmation policy, native API or PostgreSQL adapter dispatch, RLS, and
durable audit.

## Live authority and isolation

- A key is an audience credential, not an authorization snapshot.
- Every request reloads the active tenant, membership, all active appointments,
  role grants, department ceilings, direct grants, and direct denials.
- Removing `ai.use` or `terminal.use`, disabling the member/company, expiry, or
  revocation takes effect on the next request.
- Key-derived requests are accepted only by identity and the exact audience
  ingress routes in their scopes: AI, tenant terminal, or research. They cannot
  call arbitrary business or platform REST routes.
- The key embeds and verifies one tenant slug. It cannot switch companies or
  select a database.
