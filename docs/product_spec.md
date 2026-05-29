# LangGraph Memory Inspector Product Spec

## One-line Pitch

LangGraph Memory Inspector is a local-first DevTools app for inspecting,
diffing, replaying, and diagnosing LangGraph checkpoints and memory stores.

## Problem

LangGraph applications are stateful. A real agent is not just a single model
call; it is a graph of nodes, reducers, tool calls, memory updates, checkpoint
snapshots, and resume points.

When an agent gives a wrong answer, the developer often sees only the final
failure. The hidden question is harder:

- Which node first wrote the wrong value?
- Which checkpoint introduced the bad state?
- Did a memory update append stale information instead of replacing it?
- Did a thread resume from a surprising checkpoint namespace?
- Why did the checkpoint database grow so quickly?

Official tooling such as LangSmith Studio is powerful, but there is room for a
small local tool that works directly on a developer's checkpoint database and
turns the state history into a debugging story.

## Target User

- Developers building LangGraph agents locally.
- LLM application engineers debugging memory, tool use, and multi-step agent
  behavior.
- Teams that need to inspect checkpoint data before sending traces to a hosted
  observability platform.

## MVP Scope

The two-week MVP should focus on a single strong demo path:

1. Start a local web UI with `lgmi inspect ./checkpoints.sqlite`.
2. Read LangGraph SQLite checkpoint data.
3. Show thread IDs and checkpoint timelines.
4. Show checkpoint state snapshots.
5. Diff any two checkpoints.
6. Highlight node writes when the checkpoint contains write metadata.
7. Run memory diagnostics:
   - conflicting memory
   - stale memory
   - checkpoint size spike
   - oversized message history
   - missing parent checkpoint
8. Export a debug bundle with timeline, state diff, and reproduction notes.

## Non-goals For MVP

- Full replacement for LangSmith.
- Multi-user hosted SaaS.
- Editing checkpoints and resuming execution from arbitrary modified state.
- Full support for every saver backend.
- Perfect semantic diff for arbitrary custom reducers.

## Demo Story

The repository includes a small LangGraph application:

**Relocation Policy Agent**

The user tells the agent:

1. "I live in Shanghai."
2. "I moved to Hangzhou."
3. "Which local benefits should I check first?"

The intentionally flawed profile node appends the new residence memory but does
not invalidate the old residence memory. A later retrieval node reads the first
residence value instead of the newest one, so the final answer can be grounded
in stale Shanghai context even after the user moved to Hangzhou.

The inspector should make this failure obvious:

- Timeline shows the checkpoint where the second residence was appended.
- State diff shows two conflicting residence memories.
- Node write attribution points to `extract_profile`.
- Diagnostics marks `conflicting_residence_memory`.
- The final answer checkpoint shows retrieval using the stale city.

## Candidate Interview Framing

### Situation

LangGraph checkpointing is central to production agent behavior: persistence,
memory, human-in-the-loop, time travel, and failure recovery all depend on
state snapshots. However, checkpoint data is hard to inspect directly and the
causal chain from node write to wrong answer is not obvious.

### Task

Build a local-first tool that turns raw checkpoint data into a developer-facing
debugging workflow.

### Action

- Designed a checkpoint adapter abstraction.
- Built a SQLite reader for LangGraph checkpoint data.
- Implemented state timeline and JSON diff APIs.
- Built a React-based timeline, state inspector, and diff viewer.
- Added memory diagnostics for conflict, staleness, and growth.
- Created a reproducible LangGraph demo with a real memory-conflict bug.

### Result

Developers can open a checkpoint database, choose a thread, compare two
checkpoints, and locate the exact node that introduced stale or conflicting
memory. The project demonstrates practical understanding of agent state
machines, checkpoint persistence, memory architecture, and LLM developer
tooling.

## Data Retention

This project creates durable debug artifacts by design, so storage behavior must
be explicit from the beginning.

The sample app writes only local demo checkpoints under
`examples/relocation_policy_agent/data/`. These files are safe to delete and can
be regenerated. The inspector MVP should avoid writing unbounded exports by
default; debug bundles should be explicit user actions and should include file
sizes in the export result.
