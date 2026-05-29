# v0.1.0 Release Notes Draft

Status: draft release candidate notes. Do not publish until the repository is
public and the release checklist has no blocking unchecked items.

## Headline

LangGraph Memory Inspector v0.1.0 is a local-first checkpoint forensics tool for
debugging stateful LangGraph agents.

The first release focuses on one concrete failure mode: an agent gives a wrong
answer because a stale memory or state write several checkpoints earlier still
affects retrieval or final response behavior.

## Why It Exists

When a LangGraph app fails, the final LLM response is often only the symptom.
The cause may be hidden in an earlier checkpoint: a reducer appended duplicate
state, a namespace was inspected by accident, a selected retrieval key stayed
stale, or a resume path jumped to a surprising parent checkpoint.

This release turns checkpoint state into a navigable debugging trail:

1. Open a local SQLite checkpoint database or read-only PostgresSaver store.
2. Pick the relevant thread and checkpoint namespace.
3. Walk the checkpoint timeline, diffs, writes, and diagnostics.
4. Click a diagnostic to highlight the related state/write evidence.
5. Export a redacted debug bundle for a teammate, issue, or PR.

## Included Demo

The deterministic demo reproduces a stale-memory bug:

- the user first says they live in Shanghai
- the user later says they moved to Hangzhou
- the agent still retrieves Shanghai policy context
- the inspector surfaces conflicting residence memories and stale selected city
  evidence from the checkpoint trail

Run it locally:

```bash
uv sync
uv run python examples/relocation_policy_agent/run_demo.py
uv run lgmi inspect examples/relocation_policy_agent/data/checkpoints.sqlite --no-browser --port 8765
```

Then start the UI:

```bash
cd web
npm install
npm run dev
```

## Highlights

- Local SQLite checkpoint inspection.
- Read-only PostgresSaver inspection against full historical checkpoint tables.
- Thread and checkpoint namespace selection.
- Paginated checkpoint timeline with diagnostic and state-path filters.
- State snapshots, checkpoint diffs, writes, and deterministic diagnostics.
- Diagnostics for stale/conflicting memory, stale selected city, oversized
  messages, repeated retrieval context, reducer append duplicates, checkpoint
  size spikes, and unexpected parent checkpoint jumps.
- Explicit debug bundle export from CLI, API, and UI.
- Redacted export mode for private fields, message content, evidence, prompts,
  secrets, tokens, emails, and phone-like strings.
- Fixture intake policy and diagnostic matrix for turning user feedback into
  regression tests.

## Verification

Release-candidate verification commands:

```bash
uv run pytest -q
uv run python scripts/use_case_smoke.py --reset-demo
cd web
npm run build
npm run test:e2e
```

The current release-candidate CI run should include Python tests, the
stale-memory smoke test, web build/e2e, and real PostgresSaver integration.

## Known Limitations

- The repository is still private until the maintainer intentionally switches
  visibility for launch.
- Cross-namespace diffing is not supported.
- Very large production stores still need richer indexing, virtualized
  rendering, and server-side search.
- Diagnostics are deterministic rules for known patterns, not a general proof
  of agent correctness.
- Postgres support targets full historical `PostgresSaver` tables, not
  `ShallowPostgresSaver`.
- Raw debug bundles may contain private state. Use redacted exports before
  sharing publicly.

## Feedback Ask

The most useful feedback is not "does this look cool?" It is a concrete
checkpoint debugging pattern:

- Which backend do you use: SQLite, PostgresSaver, Redis, or custom?
- Do checkpoint namespaces matter in your app?
- Which state channels are hardest to debug?
- Have you seen stale memory, reducer append bugs, wrong resume points, or
  oversized message histories?
- Can the pattern be reduced to a redacted, synthetic, or schema-only fixture?
