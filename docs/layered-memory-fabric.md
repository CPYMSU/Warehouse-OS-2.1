# Layered Memory Fabric

Warehouse OS retains complete conversations in PostgreSQL and derives small,
evidence-bearing memory capsules for Auto Runtime. The prompt is never the
memory database, and a derived memory is never a permission grant or a
replacement for live business data.

## Flow

```text
append-only messages
  → coalesced memory job
  → hidden Memory Steward
  → conversation distillation + private memory units + relations
  → cached index / focused / deep capsule
  → Auto Runtime judgment
  → live tools and PostgreSQL verification
```

The steward processes only new messages after the latest distillation cursor.
A batch must end with an assistant message, so an incomplete user turn is not
summarized prematurely. Jobs use durable states and leases; model or network
failure requeues the work without affecting transcript persistence.

The steward is a post-response server task. It uses `deepseek-v4-flash` with
thinking disabled and drains up to four coalesced jobs per completed turn.
Foreground chat never waits for this work: later turns read the already
distilled index or capsule, and fall back to the append-only transcript when a
background job has not completed yet.

## Durable layers

- L0: immutable `secretariat.messages` and operational evidence.
- L1: deterministic complete turns, run state, tool results, and source cursors.
- L2: `secretariat.conversation_distillations` with summaries, facts,
  entities, relations, inferences, uncertainties, and open questions.
- L3-L5: `secretariat.memory_units` for semantic, episodic, procedural,
  preference, entity, inference, and uncertainty memory.
- L6: `secretariat.context_snapshots`, compiled for the current goal and
  selected resolution depth.

`secretariat.memory_relations` records support, contradiction, supersession,
derivation, and related-memory edges. Every automatically created memory unit
contains validated source-message evidence. Raw messages are not changed when
a derived memory is forgotten.

## Resolution depths

- `index`: four recent messages, one latest distillation, and eight memory
  units. This is the default for every turn.
- `focused`: sixteen messages, three distillations, and twenty memory units.
- `deep`: sixty-four primary messages, eight distillations, and forty-eight
  memory units.

The values are prompt-budget ceilings, not semantic routing rules. Auto Runtime
first sees `index` and may subjectively request `focused` or `deep`; it is then
run once more with that evidence. Query, memory depth, and source cursors are
part of the snapshot cache key, preventing a shallow capsule from being reused
as a deep one.

## Isolation and authority

- Every memory table has forced tenant RLS.
- Private memory resolution also requires conversation ownership.
- Automatic conversation distillation always creates private memory.
- Company-shared memory is a separate scope and is never inferred merely from
  an employee's private transcript.
- Authentication secrets must not be emitted into derived memory.
- Any operational claim must be checked against current PostgreSQL state or a
  live tool before execution.

## APIs

- `GET /api/ai/memory/capsule?conversation_id=...&depth=index`
- `GET /api/ai/memory?conversation_id=...`
- `DELETE /api/ai/memory/{memory_id}`

The delete operation tombstones a private derived memory. It intentionally
does not remove the append-only source transcript.
