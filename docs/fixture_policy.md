# Fixture Intake Policy

LangGraph Memory Inspector should learn from real checkpoint bugs without
turning private agent state into public repository data. This policy defines
what users can share, what maintainers can commit, and how a report becomes a
regression test.

## Goals

- Turn real LangGraph debugging stories into deterministic diagnostics.
- Keep raw user messages, customer data, secrets, prompts, and proprietary
  tool output out of the repository.
- Prefer small, reviewable fixtures that prove one bug pattern at a time.
- Record enough metadata that future contributors can understand why a fixture
  exists and what product decision it changed.

## Acceptable Inputs

These inputs can be discussed in public issues after review:

- A redacted debug bundle generated with `--redact`.
- A synthetic JSON fixture derived from a real debugging pattern.
- A minimal SQLite checkpoint database created specifically to reproduce one
  issue.
- A schema-only PostgresSaver snapshot, such as table names, column names, row
  counts, anonymized namespace shapes, and version metadata.
- A written debugging story when no file can be shared.

Keep files small. Public fixtures should normally stay under 2 MB unless an
issue explains why a larger artifact is necessary.

## Inputs We Do Not Accept Publicly

Do not attach or commit:

- Raw production checkpoint databases.
- Raw debug bundles.
- API keys, access tokens, passwords, cookies, or connection strings.
- Private user chats, emails, phone numbers, addresses, customer identifiers,
  or other personal data.
- Proprietary documents, tool outputs, prompts, retrieval content, or business
  records.
- Large checkpoint stores that are not reduced to a minimal reproduction.

If a report depends on sensitive data, share the shape of the state, the state
paths, and the failing transition instead of the values.

## Recommended User Workflow

When possible, generate a redacted bundle:

```bash
uv run lgmi export-debug-bundle path/to/checkpoints.sqlite \
  --thread-id <thread-id> \
  --checkpoint-id <checkpoint-id> \
  --redact \
  --output-dir exports
```

Before posting, open the JSON and confirm it contains no private values. If the
default redaction misses a project-specific field, rerun the export with
`--redact-path`:

```bash
uv run lgmi export-debug-bundle path/to/checkpoints.sqlite \
  --thread-id <thread-id> \
  --checkpoint-id <checkpoint-id> \
  --redact \
  --redact-path selected_checkpoint.checkpoint.value.channel_values.customer_notes
```

If a file still cannot be shared, describe:

- the checkpoint backend and package versions
- the `thread_id` / `checkpoint_ns` shape, with anonymized values
- the state channel and state path that changed
- the node, task, or write channel that likely caused the issue
- the visible failure users saw
- the diagnostic you expected the inspector to surface

## Required Fixture Metadata

Every committed fixture should include this metadata, either in the fixture file
or next to it:

```json
{
  "fixture_id": "synthetic_reducer_append_duplicate_memory_v1",
  "source_safety": "synthetic",
  "backend": "synthetic_json",
  "langgraph_version": "synthetic",
  "checkpointer": "synthetic",
  "checkpoint_ns_shape": "single default namespace",
  "state_channels": ["memory_events"],
  "bug_pattern_tags": ["reducer_append_duplicate_state"],
  "expected_diagnostics": ["reducer_append_duplicate_state"]
}
```

Allowed `source_safety` values:

- `synthetic`
- `redacted`
- `schema_only`

Allowed `backend` values:

- `sqlite`
- `postgres`
- `debug_bundle`
- `synthetic_json`

## Maintainer Review Checklist

Before accepting a fixture:

- Confirm the source is synthetic, redacted, or schema-only.
- Search for obvious secrets, emails, phone-like strings, private chats, and
  proprietary content.
- Confirm the file is small enough to review in a pull request.
- Add or update a test that loads the fixture and asserts the expected
  diagnostic.
- Add the fixture and diagnostic to `docs/diagnostic_matrix.md`.
- Update `docs/maintainer_notes.md` with the product decision that changed
  because of the fixture.

## Repository Layout

Use predictable paths:

- `tests/fixtures/synthetic/<fixture_id>.json`
- `tests/fixtures/redacted/<fixture_id>.json`
- `tests/fixtures/schema_only/<fixture_id>.json`

Raw databases, generated debug bundles, and local exports should stay outside
git unless a maintainer explicitly reduces them into a tiny fixture.

## Product Rule

A fixture is not just sample data. It should either:

- protect a diagnostic from regression,
- document a checkpoint shape the reader must support, or
- teach the product a real debugging workflow.

If it does none of those, keep it out of the repository.
