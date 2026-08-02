# AI Secretary Conversation History

The AI secretary uses PostgreSQL as the transcript source of truth. Browser
storage contains presentation preferences only; it is not used to preserve
messages.

## Continuity model

- Every account owns its conversations inside one tenant.
- Every user and assistant message is append-only and ordered by a database
  sequence.
- Opening the application preloads the most recently active conversation.
- Opening a specific UUID conversation restores that exact conversation.
- The UI restores the latest 80 messages. Older messages remain in PostgreSQL
  and can be requested with the `before_sequence` cursor.
- Each browser turn carries a unique `turn_id`. Replaying the same completed
  turn returns the stored assistant message without running the AI or tools
  again.

## Runtime context

The full transcript is retained, but only a bounded recent window enters the
active AI context. The window is labelled as transcript data, never as
authority. Company permissions and current database facts continue to come
from the authenticated L0-L6 runtime layers.

Completed turns are also queued for incremental background distillation. Auto
Runtime begins with a small `index` capsule and may request `focused` or `deep`
evidence when its own judgment says the current capsule is insufficient. See
[Layered Memory Fabric](layered-memory-fabric.md) for the source-cursor,
provenance, conflict, privacy, and forgetting contract.

## Isolation

`secretariat.messages` has forced tenant RLS. Application queries additionally
require the authenticated account to own the conversation, so a platform role
does not implicitly expose another employee's private secretary transcript.

## APIs

- `GET /api/assistant/bootstrap`
- `GET /api/ai/conversations`
- `POST /api/ai/conversations`
- `GET /api/ai/conversations/{conversation_id}`
- `POST /api/agent/run/stream`
