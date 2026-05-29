# Diagnostic Matrix

This matrix shows which LangGraph debugging patterns are protected by a demo,
fixture, or test. Its job is to keep product learning visible: every real bug
pattern should eventually become a diagnostic row with safe evidence and a
repeatable validation command.

## How To Read This

- `Fixture ID` names the safest evidence source currently attached to a
  diagnostic.
- `Source Safety` follows `docs/fixture_policy.md`: synthetic, redacted, or
  schema-only evidence is acceptable for public work.
- `Status` calls out whether the row is protected by a committed fixture, the
  deterministic relocation demo, or only a unit-level example.
- Unit-only rows are useful, but they are product gaps: they still need a
  fixture, redacted bundle, or schema-only backend snapshot from a real reported
  pattern.

## Matrix

| Diagnostic ID | Fixture ID | Backend Shape | Source Safety | State Channels | Validation Command | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `conflicting_residence_memory` | `relocation_demo_checkpoint_db` | `sqlite` | `synthetic` | `memory_events`, `retrieved_docs` | `uv run lgmi prove-demo --reset-demo` | Protected by the deterministic Shanghai-to-Hangzhou demo. |
| `stale_selected_city` | `relocation_demo_checkpoint_db` | `sqlite` | `synthetic` | `memory_events`, `selected_city` | `uv run lgmi prove-demo --reset-demo` | Protected by the deterministic Shanghai-to-Hangzhou demo. |
| `oversized_message_history` | `relocation_demo_checkpoint_db` | `sqlite` | `synthetic` | `messages` | `uv run lgmi prove-demo --reset-demo` | Protected by the deterministic demo smoke path. |
| `checkpoint_size_spike` | `relocation_demo_checkpoint_db` | `sqlite` | `synthetic` | `checkpoints` | `uv run lgmi prove-demo --reset-demo` | Protected by the deterministic demo smoke path. |
| `reducer_append_duplicate_state` | `synthetic_reducer_append_duplicate_memory_v1` | `synthetic_json` | `synthetic` | `memory_events` | `uv run pytest tests/test_fixtures.py -q` | Protected by a committed safe fixture. |
| `checkpoint_namespace_confusion` | `synthetic_namespace_confusion_multi_ns_v1` | `synthetic_json` | `synthetic` | `checkpoint_ns`, `memory_events`, `messages`, `selected_city` | `uv run pytest tests/test_fixtures.py -q` | Protected by a committed safe fixture with two namespaces under one thread. |
| `stale_retrieved_context` | `synthetic_rag_stale_retrieved_context_v1` | `synthetic_json` | `synthetic` | `memory_events`, `query_context`, `retrieved_docs` | `uv run pytest tests/test_fixtures.py -q` | Protected by a committed safe RAG stale-context fixture. |
| `repeated_retrieved_context` | `unit_state_repeated_docs` | `in_memory` | `synthetic` | `retrieved_docs` | `uv run pytest tests/test_analysis.py -q` | Unit-only coverage; needs a safe fixture from a real retrieval-repeat pattern. |
| `unexpected_parent_checkpoint` | `unit_checkpoint_lineage_jump` | `in_memory` | `synthetic` | `checkpoints` | `uv run pytest tests/test_analysis.py -q` | Unit-only coverage; needs a safe fixture from a real resume or branching pattern. |

## Next Evidence To Collect

The highest-value next fixture candidates are:

- A redacted bundle from a real stale RAG/context reuse report, so
  `stale_retrieved_context` can be tuned against more than city-scoped
  synthetic metadata.
- A schema-only PostgresSaver snapshot that proves the matrix against a
  production-like backend shape.
- A redacted debug bundle where a user resumed from an unexpected parent
  checkpoint and needed lineage evidence.

## Maintainer Rule

When adding a committed JSON fixture, update this matrix in the same pull
request. The fixture tests verify that every fixture `expected_diagnostics`
entry appears here with matching backend, source safety, state channels, and a
validation command.
