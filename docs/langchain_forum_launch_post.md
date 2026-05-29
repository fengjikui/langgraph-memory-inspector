# LangChain Forum Launch Post

This is the first external launch post. Use it in the LangChain Forum under the
LangGraph category. The goal is feedback and real checkpoint bug patterns, not
stars.

## Pre-Post Checklist

- [ ] GitHub social preview image uploaded in repository Settings.
      Use `docs/social_preview_upload_guide.md`; the asset has been verified as
      PNG, 1280 x 640, and under 1 MB.
- [ ] CI is green on `main`.
- [ ] `uv run lgmi doctor` works from a fresh clone.
- [ ] `uv run lgmi prove-demo --reset-demo` proves the stale-memory path.
- [ ] `uv run lgmi demo --build-ui` opens the demo.
- [ ] `uv run --extra postgres python scripts/postgres_confidence.py --help` works.
- [ ] Issue #20 is open and ready as the feedback home base.
- [ ] Do not include raw production data, private checkpoint rows, prompts, or
  user messages in the post.
- [ ] Do not ask for stars as the primary call to action.

## Category

Post in the LangGraph category on the LangChain Forum:

```text
https://forum.langchain.com/
```

The official LangChain community page points builders to the Forum and
Community Slack. Slack is better for a later short showcase; the Forum is the
right first post because this is help/product-feedback shaped and asks for
implementation feedback.

Reference links checked on 2026-05-29:

- LangChain community page: https://www.langchain.com/community
- LangGraph Forum category: https://forum.langchain.com/t/about-the-langgraph-category/37
- LangChain Community Slack guidelines: https://www.langchain.com/join-community

## Title

```text
Local-first checkpoint inspector for debugging LangGraph stale-memory bugs
```

## Body

````markdown
I am building **LangGraph Memory Inspector**, a local-first checkpoint forensics
workflow for debugging stateful LangGraph apps.

The current demo is intentionally concrete:

- the user first says they live in Shanghai
- later they say they moved to Hangzhou
- the agent still answers with Shanghai policy context
- the inspector surfaces stale retrieved context, not only conflicting profile
  memory
- the checkpoint store contains the evidence, but the root cause is several
  checkpoints before the final answer

The Inspector reads the checkpoint store locally and shows:

- checkpoint timeline
- state snapshots and diffs
- node/channel writes
- deterministic diagnostics such as `conflicting_residence_memory` and
  `stale_selected_city`, plus `stale_retrieved_context`
- additional diagnostics for repeated retrieved context, reducer append
  duplicates, message/history bloat, namespace confusion, checkpoint size
  spikes, and wrong-resume lineage jumps
- a node-level causal path such as
  `extract_profile -> retrieve_policy -> answer`
- checkpoint id prefix filtering for jumping from logs to the suspicious
  timeline range
- redacted debug bundle export for issues, teammates, or PRs

Quickstart:

```bash
uv sync
uv run lgmi doctor
uv run lgmi prove-demo --reset-demo
uv run lgmi demo --build-ui
```

Try it on your own local SQLite checkpoint copy:

```bash
uv run lgmi doctor --sqlite-db ./checkpoints.sqlite
uv run lgmi inspect ./checkpoints.sqlite --build-ui
```

For a PostgresSaver store:

```bash
uv sync --extra postgres
uv run --extra postgres lgmi doctor --postgres-conninfo "$DATABASE_URL" --postgres-schema public
uv run --extra postgres lgmi inspect-postgres "$DATABASE_URL" --schema public --build-ui
```

`ShallowPostgresSaver` latest-only schemas are detected and reported as
unsupported because they cannot provide checkpoint timelines. Doctor reports
redact connection credentials and do not include checkpoint state.

If you want to test the Postgres path before connecting a private store, the repo
also includes a confidence script that writes a tiny LangGraph PostgresSaver demo
schema, validates it with the read-only reader and doctor check, and optionally
keeps the schema for UI inspection:

```bash
uv run --extra postgres python scripts/postgres_confidence.py --dsn "$DATABASE_URL" --keep-schema
```

Repo/demo:
https://github.com/fengjikui/langgraph-memory-inspector

Feedback home base:
https://github.com/fengjikui/langgraph-memory-inspector/issues/20

I am looking for real LangGraph checkpoint bug patterns to turn into
deterministic diagnostics. The most useful feedback:

- Which checkpoint backend do you use: SQLite, PostgresSaver, Redis, custom?
- Do you use multiple `checkpoint_ns` values under one `thread_id`?
- Which state channel is hardest to debug?
- Have you seen stale memory, stale retrieved context, repeated retrieval,
  reducer append bugs, wrong resume points, namespace confusion, or
  message/history bloat?
- Have you had only a checkpoint id/prefix from logs and needed to jump to that
  part of the timeline?
- What would you need to safely inspect a production copy locally?

Every current diagnostic is backed by the deterministic demo or a committed
safe fixture in the diagnostic matrix, so the next useful input is a real
production-shaped pattern rather than another synthetic-only example.

This is not intended to replace LangSmith or LangGraph Studio. The scope is
narrower: local checkpoint forensics when persisted state is wrong and you need
to find which checkpoint/write made it visible.

If you can share evidence, please use a redacted bundle, synthetic fixture, or
schema-only snapshot. For SQLite checkpoint copies, `export-debug-bundle --issue`
creates a redacted bundle and `audit-debug-bundle` runs a local safety check
before you attach it. Please do not share raw production checkpoint stores:
https://github.com/fengjikui/langgraph-memory-inspector/blob/main/docs/fixture_policy.md
````

## First Reply If Someone Asks How It Differs From LangSmith / Studio

```text
I see LangSmith / Studio as broader observability and graph development tools.
This project is intentionally narrower: local checkpoint forensics.

The question it tries to answer is: when a persisted state value is wrong, which
checkpoint/write/node made that bad value visible, and can I inspect that
without uploading private state?
```

## First Reply If Someone Has A Real Bug But Cannot Share Data

```text
That is exactly the kind of pattern I am trying to collect, and raw data is not
needed. The safest options are:

- describe the state channels and checkpoint backend in prose
- share a redacted debug bundle after running `audit-debug-bundle`
- create a small synthetic fixture that reproduces the shape
- share a schema-only backend snapshot

The fixture policy is here:
https://github.com/fengjikui/langgraph-memory-inspector/blob/main/docs/fixture_policy.md
```
