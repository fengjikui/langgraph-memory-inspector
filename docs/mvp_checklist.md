# MVP Definition Of Done

This checklist defines the smallest interview-ready LangGraph Memory Inspector
MVP. The goal is one excellent local debugging path, not a broad observability
platform.

## Backend

- [ ] `lgmi inspect <checkpoint.sqlite>` starts a local backend and serves the
  selected database in read-only mode.
- [ ] Backend validates that the SQLite file exists and contains LangGraph
  checkpoint tables.
- [ ] Backend exposes `GET /api/databases/current/summary` with path, file size,
  table names, row counts, and detected checkpoint namespaces.
- [ ] Backend exposes `GET /api/threads` with thread id, namespace, checkpoint
  count, first checkpoint id, and last checkpoint id.
- [ ] Backend exposes `GET /api/threads/{thread_id}/checkpoints`.
- [ ] Backend exposes `GET /api/threads/{thread_id}/checkpoints/{checkpoint_id}`
  with decoded checkpoint state and metadata.
- [ ] Backend exposes `GET /api/threads/{thread_id}/diff?from=...&to=...`.
- [ ] Backend exposes diagnostics for a thread or checkpoint range.
- [ ] Checkpoint access is isolated behind an adapter interface.
- [ ] SQLite adapter has tests for the relocation demo database or a small
  deterministic fixture.
- [ ] Backend handles unreadable blobs, missing parents, and malformed paths
  with clear error responses.

## Frontend

- [ ] UI can open the backend-served database summary.
- [ ] UI lists threads and selects `relocation-demo-user-001`.
- [ ] UI renders an ordered checkpoint timeline with parent-child continuity.
- [ ] UI shows checkpoint details, including metadata, state channels, and
  serialized size.
- [ ] UI includes a JSON state inspector for `messages`, `memory_events`,
  `retrieved_docs`, `diagnostics`, and `selected_city`.
- [ ] UI allows selecting two checkpoints and viewing their diff.
- [ ] UI shows diagnostics with severity, checkpoint id, evidence path, and a
  short explanation.
- [ ] UI has loading, empty, and error states for missing databases and empty
  threads.
- [ ] UI works on a typical laptop viewport without horizontal layout breakage.

## Analysis

- [ ] Diff service reports added, removed, and changed state paths.
- [ ] Diff service highlights list changes in `memory_events`.
- [ ] Diagnostics detects `conflicting_residence_memory`.
- [ ] Diagnostics detects `stale_retrieval_context` when `selected_city` does
  not match the newest residence memory.
- [ ] Diagnostics detects `checkpoint_size_spike` with a configurable threshold.
- [ ] Diagnostics detects `oversized_message_history`.
- [ ] Diagnostics detects `missing_parent_checkpoint`.
- [ ] Diagnostics can identify the first checkpoint where each issue appears.
- [ ] Findings include enough evidence to reproduce the reasoning without an
  LLM call.

## Demo

- [ ] `uv sync` installs the project successfully.
- [ ] `uv run python examples/relocation_policy_agent/run_demo.py --reset`
  creates a fresh demo checkpoint database.
- [ ] Demo runs without an API key using deterministic local answers.
- [ ] Demo optionally runs with `--use-llm` when `OPENAI_API_KEY` is set.
- [ ] Demo final output shows memory events, selected city, diagnostics,
  checkpoint DB path, checkpoint row count, and writes row count.
- [ ] Demo creates the stale-memory scenario: newest residence is Hangzhou, but
  retrieval selects Shanghai.
- [ ] Interview script can be completed in 5-8 minutes.
- [ ] Fallback terminal-only demo exists for cases where the UI is not ready.

## Docs

- [ ] README explains the current milestone and demo command.
- [ ] Product spec states the one-line pitch, target user, MVP scope, non-goals,
  and demo story.
- [ ] Architecture doc explains the demo agent, checkpoint DB, inspector
  backend/frontend, diff service, diagnostics, and data flow.
- [ ] Demo script explains the 5-8 minute interview path and clearly labels UI
  portions that are MVP target screens.
- [ ] Resume project doc includes compact bullets, a longer project summary, and
  a STAR story.
- [ ] Generated artifact policy is documented in README and docs.

## Storage Hygiene

- [ ] Demo checkpoint files are documented as safe to delete:
  `examples/relocation_policy_agent/data/checkpoints.sqlite`,
  `examples/relocation_policy_agent/data/checkpoints.sqlite-shm`, and
  `examples/relocation_policy_agent/data/checkpoints.sqlite-wal`.
- [ ] Generated debug bundles, timeline exports, diff exports, and diagnostic
  exports are documented as safe to delete.
- [ ] SQLite checkpoint databases, WAL/SHM sidecars, and generated exports are
  excluded from commits unless intentionally added as tiny test fixtures.
- [ ] Export actions are explicit user actions, not automatic side effects of
  opening the inspector.
- [ ] Export result shows output path and file size.
- [ ] Any recurring generated output has a retention rule, size cap, or cleanup
  command before it is considered MVP complete.
- [ ] Demo handoff tells the audience which artifacts are generated and what can
  be deleted after the session.
