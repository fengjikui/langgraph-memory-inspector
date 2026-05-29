# MVP Definition Of Done

This checklist defines the smallest interview-ready LangGraph Memory Inspector
MVP. The goal is one excellent local debugging path, not a broad observability
platform.

Status: achieved for v0.1.0. Items below reflect the implemented scope as of
2026-05-29. Broader production-hardening work is tracked in
`docs/release_checklist.md`, `docs/diagnostic_matrix.md`, and open GitHub
issues.

## Backend

- [x] `lgmi inspect <checkpoint.sqlite>` starts a local backend and serves the
  selected database in read-only mode.
- [x] Backend validates that the SQLite file exists and contains LangGraph
  checkpoint tables.
- [x] Backend exposes `GET /api/summary` with path, file size, row counts, and
  detected checkpoint namespaces.
- [x] Backend exposes `GET /api/threads` with thread id, namespace, checkpoint
  count, first checkpoint id, and last checkpoint id.
- [x] Backend exposes `GET /api/threads/{thread_id}/checkpoints`.
- [x] Backend exposes `GET /api/threads/{thread_id}/checkpoints/{checkpoint_id}`
  with decoded checkpoint state and metadata.
- [x] Backend exposes `GET /api/threads/{thread_id}/diff?from=...&to=...`.
- [x] Backend exposes diagnostics for a thread or checkpoint range.
- [x] Checkpoint access is isolated behind an adapter interface.
- [x] SQLite adapter has tests for the relocation demo database or a small
  deterministic fixture.
- [x] Backend handles unreadable blobs, missing parents, and malformed paths
  with clear error responses.

## Frontend

- [x] UI can open the backend-served database summary.
- [x] UI lists threads and selects `relocation-demo-user-001`.
- [x] UI renders an ordered checkpoint timeline with parent-child continuity.
- [x] UI shows checkpoint details, including metadata, state channels, and
  serialized size.
- [x] UI includes a JSON state inspector for `messages`, `memory_events`,
  `retrieved_docs`, `diagnostics`, and `selected_city`.
- [x] UI shows a previous-to-selected checkpoint diff for the active checkpoint.
- [x] UI shows diagnostics with severity, checkpoint id, evidence path, and a
  short explanation.
- [x] UI has loading, empty, and error states for missing databases and empty
  threads.
- [x] UI works on a typical laptop viewport without horizontal layout breakage.

## Analysis

- [x] Diff service reports added, removed, and changed state paths.
- [x] Diff service highlights list changes in `memory_events`.
- [x] Diagnostics detects `conflicting_residence_memory`.
- [x] Diagnostics detects `stale_selected_city` when `selected_city` does not
  match the newest residence memory.
- [x] Diagnostics detects `checkpoint_size_spike` with a configurable threshold.
- [x] Diagnostics detects `oversized_message_history`.
- [x] Diagnostics detects `reducer_append_duplicate_state`.
- [x] Diagnostics detects `unexpected_parent_checkpoint`.
- [x] Diagnostics can identify the first checkpoint where each issue appears.
- [x] Findings include enough evidence to reproduce the reasoning without an
  LLM call.

## Demo

- [x] `uv sync` installs the project successfully.
- [x] `uv run python examples/relocation_policy_agent/run_demo.py --reset`
  creates a fresh demo checkpoint database.
- [x] Demo runs without an API key using deterministic local answers.
- [x] Demo optionally runs with `--use-llm` when `OPENAI_API_KEY` is set.
- [x] Demo final output shows memory events, selected city, diagnostics,
  checkpoint DB path, checkpoint row count, and writes row count.
- [x] Demo creates the stale-memory scenario: newest residence is Hangzhou, but
  retrieval selects Shanghai.
- [x] Interview script can be completed in 5-8 minutes.
- [x] Fallback terminal-only demo exists for cases where the UI is not ready.

## Docs

- [x] README explains the current milestone and demo command.
- [x] Product spec states the one-line pitch, target user, MVP scope, non-goals,
  and demo story.
- [x] Architecture doc explains the demo agent, checkpoint DB, inspector
  backend/frontend, diff service, diagnostics, and data flow.
- [x] Demo script explains the 5-8 minute interview path and clearly labels UI
  portions that are MVP target screens.
- [x] Resume project doc includes compact bullets, a longer project summary, and
  a STAR story.
- [x] Generated artifact policy is documented in README and docs.

## Storage Hygiene

- [x] Demo checkpoint files are documented as safe to delete:
  `examples/relocation_policy_agent/data/checkpoints.sqlite`,
  `examples/relocation_policy_agent/data/checkpoints.sqlite-shm`, and
  `examples/relocation_policy_agent/data/checkpoints.sqlite-wal`.
- [x] Generated debug bundles, timeline exports, diff exports, and diagnostic
  exports are documented as safe to delete.
- [x] SQLite checkpoint databases, WAL/SHM sidecars, and generated exports are
  excluded from commits unless intentionally added as tiny test fixtures.
- [x] Export actions are explicit user actions, not automatic side effects of
  opening the inspector.
- [x] Export result shows output path and file size.
- [x] Any recurring generated output has a retention rule, size cap, or cleanup
  command before it is considered MVP complete.
- [x] Demo handoff tells the audience which artifacts are generated and what can
  be deleted after the session.
