# Resume Project Wording

Use this document as interview and resume copy for LangGraph Memory Inspector.
The wording is intentionally written from the candidate perspective and frames
the project as a completed MVP.

## Compact Resume Bullets

- Built a local-first LangGraph checkpoint inspector that reads SQLite
  checkpoint databases, reconstructs thread timelines, and compares state
  snapshots to debug memory-related agent failures.
- Implemented a reproducible LangGraph demo agent with an intentional stale
  memory bug, then surfaced the root cause through checkpoint diffs,
  write-level attribution, and deterministic diagnostics.
- Designed an adapter-based architecture for checkpoint backends, with SQLite
  support first and clear extension points for additional LangGraph saver
  backends.
- Created an interview-ready debugging workflow covering timeline inspection,
  state diffing, memory conflict detection, stale retrieval diagnosis, and
  explicit storage hygiene for generated artifacts.

## Slightly Longer Resume Version

LangGraph Memory Inspector - local-first DevTools for agent memory debugging.
Built a LangGraph checkpoint inspection workflow that reads SQLite checkpoint
databases, reconstructs thread timelines, diffs state snapshots, and flags
memory failures such as conflicting profile updates and stale retrieval context.
Created a reproducible relocation policy agent demo where a user moves from
Shanghai to Hangzhou but retrieval still uses stale Shanghai memory, then used
the inspector workflow to identify the checkpoint and graph node responsible
for the bad state.

Tech: Python, LangGraph, LangGraph SQLite checkpointing, SQLite, FastAPI-style
API design, React-style DevTools UX design, deterministic diagnostics.

## STAR Interview Story

Situation:

LangGraph agents are not single prompt calls. They are stateful graphs with
reducers, node writes, checkpoint snapshots, memory updates, and resume points.
When an agent gives a wrong answer, the final output rarely explains which node
first introduced the bad state.

Task:

I wanted to build a practical developer tool that could inspect checkpoint data
locally and turn raw state history into a debugging workflow. The goal was not
to replace hosted observability tools, but to make one common failure mode very
easy to diagnose: stale or conflicting memory.

Action:

I built a small LangGraph relocation policy agent that writes real SQLite
checkpoints through `SqliteSaver`. The demo intentionally appends residence
memories instead of invalidating older values, so after the user moves from
Shanghai to Hangzhou the graph still retrieves Shanghai policy context. Around
that fixture, I designed the inspector architecture: a checkpoint adapter, a
timeline service, a state snapshot API, a JSON diff service, and a diagnostics
layer that detects conflicting residence memory, stale retrieval context,
checkpoint size spikes, oversized message history, and missing parent
checkpoints. I also designed the frontend workflow around a thread timeline,
state inspector, diff viewer, and diagnostics panel.

Result:

The project demonstrates a full debugging story: run the agent, open the local
checkpoint database, select the demo thread, compare checkpoints around the
second user turn, see that Hangzhou was appended without invalidating Shanghai,
and trace the final stale answer back to the retrieval node using the oldest
memory. It shows practical understanding of agent state machines, checkpoint
persistence, memory architecture, and developer tooling UX.

## 60-Second Spoken Version

"I built LangGraph Memory Inspector, a local-first DevTools project for
debugging agent state. The core idea is that LangGraph failures often happen
inside checkpoint history: a node writes stale memory, a reducer appends a bad
value, or retrieval uses the wrong snapshot. I created a relocation policy demo
agent that writes real SQLite checkpoints and intentionally contains a memory
bug: the user moves from Shanghai to Hangzhou, but retrieval still uses the
first Shanghai memory. The inspector workflow reads that checkpoint database,
shows the thread timeline, diffs state snapshots, and flags diagnostics like
conflicting residence memory and stale retrieval context. The project is narrow
by design, but it demonstrates the full loop from reproducible agent bug to
checkpoint-level root cause."

## What To Emphasize In Interviews

- This is an agent infrastructure project, not just a UI wrapper.
- The demo uses real LangGraph checkpoint persistence.
- The bug is intentionally reproducible without network access or an LLM key.
- Diagnostics are deterministic first; LLM summaries can be added later.
- The architecture separates checkpoint adapters from analysis and UI.
- Storage behavior is explicit: demo SQLite files and debug exports are
  generated artifacts and should not be committed.

## Generated Artifact Policy

Safe to delete:

- `examples/relocation_policy_agent/data/checkpoints.sqlite`
- `examples/relocation_policy_agent/data/checkpoints.sqlite-shm`
- `examples/relocation_policy_agent/data/checkpoints.sqlite-wal`
- generated debug bundles
- exported timeline, diff, or diagnostic files

Do not commit generated SQLite checkpoint databases, WAL/SHM sidecars, or
inspector export bundles. Keep committed fixtures deliberately small and
separate from live demo output.
