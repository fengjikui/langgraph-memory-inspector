# Interview Demo Script

This script is designed for a 5-8 minute interview demo. The current MVP has a
real LangGraph demo, a local FastAPI checkpoint reader, a React inspector UI,
and a use-case smoke test that verifies the stale-memory debugging path.

## Setup Before The Call

From the repository root:

```bash
uv sync
uv run lgmi demo --prepare-only
uv run python scripts/use_case_smoke.py
```

Optional LLM mode:

```bash
export OPENAI_API_KEY=...
uv run python examples/relocation_policy_agent/run_demo.py --reset --use-llm
```

For a deterministic interview demo, use the default local mode. It does not
depend on network access or an API key.

Generated checkpoint files are safe to delete:

- `examples/relocation_policy_agent/data/checkpoints.sqlite`
- `examples/relocation_policy_agent/data/checkpoints.sqlite-shm`
- `examples/relocation_policy_agent/data/checkpoints.sqlite-wal`

Do not commit these generated SQLite files or any exported debug bundles.

## 0:00-0:45 - Project Framing

Say:

"LangGraph agents are stateful systems. When an answer is wrong, the failure
usually happened earlier: a node wrote stale memory, a reducer appended instead
of replacing, or a thread resumed from an unexpected checkpoint. I built
LangGraph Memory Inspector as a local-first DevTools workflow for reading
checkpoint databases and turning state history into a debugging story."

Show:

- `README.md`
- `docs/product_spec.md`
- The one-line pitch: local-first inspection, diffing, replay context, and
  diagnostics for LangGraph checkpoints.

## 0:45-2:00 - Run The Demo Agent

Run:

```bash
uv run lgmi demo --prepare-only
```

Narrate the three turns:

1. The user says they live in Shanghai.
2. The user says they moved to Hangzhou.
3. The user asks which local benefits to check first.

Point out the final summary:

- `memory_events` contains both Shanghai and Hangzhou residence memories.
- `selected_city` is Shanghai.
- `diagnostics` includes `conflicting_residence_memory`.
- The checkpoint DB path is
  `examples/relocation_policy_agent/data/checkpoints.sqlite`.

Say:

"This is the intentional bug. The profile extractor remembered Hangzhou, but
retrieval used the first residence memory. The answer is therefore grounded in
stale Shanghai context."

## 2:00-3:00 - Explain The Checkpoint Data

Show the demo code in `examples/relocation_policy_agent/run_demo.py`.

Call out the graph:

```text
extract_profile -> audit_memory -> retrieve_policy -> answer
```

Explain:

- `extract_profile` appends residence memories.
- `audit_memory` detects conflicting cities.
- `retrieve_policy` contains the bug: it uses `residence_events[0]` instead of
  the newest residence event.
- `SqliteSaver` persists every step into the checkpoint database.

If you want a quick terminal proof without modifying the database:

```bash
sqlite3 examples/relocation_policy_agent/data/checkpoints.sqlite \
  "select 'checkpoints', count(*) from checkpoints union all select 'writes', count(*) from writes;"
```

## 3:00-5:30 - Open Inspector

Start the API:

```bash
uv run lgmi demo
```

Start the UI in another terminal:

```bash
cd web
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`.

Show:

- Left sidebar: database summary and thread list.
- Namespace selector: active checkpoint namespace for the selected thread.
- Main timeline: ordered checkpoints for `relocation-demo-user-001`.
- Right panel: selected checkpoint state.
- State, diff, writes, and diagnostics tabs/panels.

Narrate the debugging path:

1. Select thread `relocation-demo-user-001`.
2. Open the timeline and find the turn where Hangzhou was appended.
3. Compare the checkpoint before and after the second turn.
4. In the diff, show `memory_events` changing from one residence to two.
5. Open diagnostics and highlight `conflicting_residence_memory`.
6. Click `conflicting_residence_memory`.
7. Confirm the UI jumps to the related checkpoint, opens Writes, and highlights
   `state.memory_events`.
8. Point to the Causal chain panel: it should show the earlier Shanghai memory
   write, the Hangzhou append, and where `conflicting_residence_memory` first
   appears.
9. Move to the final answer checkpoint and show `selected_city=Shanghai`.
10. Explain the root cause: the newest memory is Hangzhou, but retrieval used the
   oldest memory.
11. Keep `Redact private fields` enabled and click `Export redacted`.
12. Show that the UI reports the exported bundle path, file size, and diagnostic
    ids.
13. Point out the redaction status so the interviewer sees that shareable
    evidence does not require exposing raw checkpoint state.

Say:

"The value of the tool is not just showing JSON. It connects the final bad
answer to the checkpoint where the bad state became visible, then turns the
diagnostic into a compact causal chain of state paths, checkpoint writes, and
node/task evidence. Export turns that local diagnosis into a shareable,
redacted artifact for a teammate, issue, or PR."

### GIF Capture Checklist

Use this flow when refreshing `docs/assets/stale-memory-debugging-demo.gif`:

1. Start from the final wrong answer.
2. Click `conflicting_residence_memory`.
3. Show the selected checkpoint in the timeline.
4. Open Writes and show `state.memory_events` highlighted.
5. Show the Causal chain panel with the earlier Shanghai memory and later
   Hangzhou append.
6. Close by showing `selected_city=Shanghai` while the latest residence memory
   is Hangzhou.

## 5:30-6:45 - Show The Fix Direction

Open the retrieval function and explain the expected fix:

```text
selected_city = residence_events[-1]["value"]
```

Do not change code during the interview unless asked. The demo is stronger when
the bug remains reproducible.

Say:

"A production inspector should make this diagnosis before I read the code. The
causal chain tells me which checkpoint and write to inspect first; the code
confirms the diagnosis after the checkpoint timeline tells me where to look."

## 6:45-8:00 - Close With Engineering Depth

Highlight the engineering choices:

- Local-first: reads a developer's checkpoint database directly.
- Adapter boundary: SQLite first, Postgres later.
- Deterministic diagnostics: no model call required to find the bug.
- Diff-first UX: compare snapshots instead of scanning raw blobs.
- Storage hygiene: generated SQLite files and exports are disposable and should
  not be committed.
- Use-case smoke testing: `scripts/use_case_smoke.py` proves the value path from
  checkpoint evidence, not from hand-waved UI claims.

Close:

"The MVP is intentionally narrow: one database, one excellent debugging path,
and a real checkpoint-backed memory bug. That makes it interviewable as both an
agent systems project and a developer tooling project."

## Current Fallback Without UI

If the inspector UI is not ready during a demo, use this fallback:

1. Run the demo agent.
2. Show the final printed summary.
3. Show the SQLite schema and row counts.
4. Run `uv run python scripts/use_case_smoke.py`.
5. Open `run_demo.py` and confirm the root cause in `retrieve_policy`.

The fallback still demonstrates the project thesis: LangGraph checkpoint state
contains the evidence needed to debug memory failures.
