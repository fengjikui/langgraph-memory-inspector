# Postgres Adapter Research And Thin Implementation Plan

## User Value

SQLite support proves the debugging workflow locally. Postgres support makes
LangGraph Memory Inspector relevant to production teams, because many deployed
LangGraph apps persist checkpoints in Postgres through `PostgresSaver` or
`AsyncPostgresSaver`.

The adapter must stay read-only. A developer should be able to point LGMI at a
production-like checkpoint store, inspect evidence, and trust that the tool will
not call LangGraph migrations, mutate rows, delete threads, or run graph code.

## Evidence Checked

Research date: 2026-05-29.

- LangChain persistence docs explain that checkpoints are snapshots saved at
  super-step boundaries, while node/task writes are stored separately in
  `checkpoint_writes` and linked to the in-progress checkpoint.
- The same docs list `langgraph-checkpoint-postgres` as the production-oriented
  Postgres checkpointer.
- Current `langgraph.checkpoint.postgres.base.MIGRATIONS` defines four
  Postgres tables for the full saver: `checkpoint_migrations`, `checkpoints`,
  `checkpoint_blobs`, and `checkpoint_writes`.
- Current `PostgresSaver.put()` stores primitive channel values inline in the
  `checkpoints.checkpoint` JSONB payload and stores non-primitive channel values
  in `checkpoint_blobs`.
- Current `PostgresSaver.put_writes()` writes intermediate node outputs to
  `checkpoint_writes`, including `task_path`.

Primary references:

- [LangGraph persistence docs](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Postgres checkpointer reference](https://reference.langchain.com/python/langgraph.checkpoint.postgres)
- [Postgres migrations reference](https://reference.langchain.com/python/langgraph.checkpoint.postgres/base/MIGRATIONS)
- [PostgresSaver source](https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint-postgres/langgraph/checkpoint/postgres/__init__.py)

## Current Schema Target

Full `PostgresSaver` currently uses:

```text
checkpoints(
  thread_id,
  checkpoint_ns,
  checkpoint_id,
  parent_checkpoint_id,
  type,
  checkpoint jsonb,
  metadata jsonb
)

checkpoint_blobs(
  thread_id,
  checkpoint_ns,
  channel,
  version,
  type,
  blob bytea
)

checkpoint_writes(
  thread_id,
  checkpoint_ns,
  checkpoint_id,
  task_id,
  task_path,
  idx,
  channel,
  type,
  blob bytea
)

checkpoint_migrations(v)
```

There is also a shallow saver with a different `checkpoints` primary key and no
historical checkpoint rows. The first LGMI Postgres adapter should explicitly
target the full saver and detect shallow stores as unsupported or limited mode.

## Adapter Boundary

The repository now has a `CheckpointReader` protocol in `src/lgmi/adapters.py`.
Every backend should implement:

- `summary()`
- `list_threads()`
- `list_checkpoints(thread_id)`
- `get_checkpoint(thread_id, checkpoint_id)`
- `list_writes(thread_id, checkpoint_id)`

This keeps FastAPI routes and frontend normalization independent from the
database implementation.

## Thin Implementation Plan

1. Add optional dependencies only for Postgres inspection:

   ```text
   psycopg[binary]>=3
   ```

   Do not make Postgres dependencies mandatory for SQLite users.

2. Add a read-only `PostgresCheckpointReader`.

   Constructor:

   ```python
   PostgresCheckpointReader(conninfo: str, schema: str = "public")
   ```

   It should connect with a dict row factory, never call `.setup()`, and set a
   read-only transaction mode where supported.

3. Validate schema before reading.

   Required full-saver tables:

   - `checkpoints`
   - `checkpoint_blobs`
   - `checkpoint_writes`

   Required columns should be checked through `information_schema.columns`.
   If `checkpoint_writes.task_path` is missing, treat it as an older/partial
   schema and return `task_path=""` rather than failing.

4. Hydrate checkpoints safely.

   The adapter cannot simply return `checkpoints.checkpoint` because Postgres
   stores many channel values in `checkpoint_blobs`. For each checkpoint:

   - read JSONB checkpoint metadata
   - inspect `checkpoint.channel_versions`
   - join matching blob rows by `(thread_id, checkpoint_ns, channel, version)`
   - decode each blob through `JsonPlusSerializer`
   - merge hydrated values back into `checkpoint.channel_values`

   Primitive inline values can remain as-is.

5. Decode writes.

   Map `checkpoint_writes.blob` through `JsonPlusSerializer` and expose rows in
   the same shape the UI already expects:

   ```text
   rowid-like id, thread_id, checkpoint_ns, checkpoint_id, task_id,
   task_path, idx, channel, type, byte_size, value
   ```

6. Preserve incoming-writes semantics.

   SQLite recording showed that users expect the Writes tab to explain how the
   selected checkpoint snapshot was created. The Postgres adapter should follow
   the same behavior: `list_writes(thread_id, checkpoint_id)` returns the writes
   for the parent checkpoint id when those are the writes that produced the
   selected snapshot, with a fallback to the selected checkpoint id.

7. Add a fixture-level integration test.

   Preferred path:

   - use Docker or local Postgres only in an optional test group
   - create a tiny graph with `PostgresSaver`
   - call `.setup()` in the fixture only, never in the reader
   - assert the reader hydrates a non-primitive `memory_events` channel from
     `checkpoint_blobs`
   - assert `list_writes()` returns decoded `checkpoint_writes`

8. Add CLI support after the reader is proven.

   Keep the current SQLite command stable, then add:

   ```bash
   lgmi inspect-postgres "$DATABASE_URL" --schema public --no-browser --port 8765
   ```

   Do not overload `lgmi inspect <path>` with connection-string guessing until
   there is a clear UX reason.

## Risks And Guardrails

- **Schema drift:** Pin tests to the current migration shape and document the
  detected saver schema version.
- **Large production tables:** Always page and limit thread/checkpoint queries.
  Do not hydrate every checkpoint eagerly.
- **Sensitive data:** Keep local-first behavior; do not send checkpoint contents
  to external services.
- **Write safety:** The reader must not call `.setup()`, `.put()`,
  `.put_writes()`, or `.delete_thread()`.
- **Shallow saver:** Detect and report limited support instead of silently
  presenting a fake timeline.

## Open Follow-Up Issue

After this research issue closes, implementation should happen in a separate
issue titled:

```text
Read-only Postgres checkpoint adapter implementation
```

Acceptance criteria for that issue should require a real Postgres-backed
fixture or an explicitly documented local Docker command, not only mocked SQL.
