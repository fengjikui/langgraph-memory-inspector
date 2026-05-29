# User Value And Real Use Cases

LangGraph Memory Inspector is useful only if it shortens a real debugging loop.
The target user is not looking for another graph picture; they need to answer
why a stateful agent behaved incorrectly.

## Primary User

The primary user is an LLM application engineer building a LangGraph workflow
with memory, retrieval, tools, or human-in-the-loop resume points.

They usually have three assets:

- the source code for the graph
- a local checkpoint database
- a failing conversation or thread id

They usually lack one thing: a fast way to connect the final bad answer to the
earlier state transition that caused it.

## Job To Be Done

When my LangGraph agent gives a wrong answer, I want to inspect the checkpoint
timeline and compare state snapshots, so that I can identify which node wrote
the bad state and fix the graph without guessing.

## Concrete Value Points

1. **Find the first bad checkpoint**

   Instead of reading the whole database or stepping through code blindly, the
   developer can scan a timeline and jump to the checkpoint where a diagnostic
   first appears.

2. **Turn raw state into causal evidence**

   The tool surfaces state fields such as `memory_events`, `selected_city`,
   `retrieved_docs`, and `diagnostics`, then shows how they changed between
   checkpoints.

3. **Debug memory bugs without an LLM call**

   Rule-based diagnostics can detect stale or conflicting memory from the saved
   checkpoint state. This keeps the debugging path deterministic.

4. **Reduce privacy and setup friction**

   The tool reads a local SQLite checkpoint database. A developer can inspect
   private or early-stage traces without uploading them to a hosted platform.

5. **Give teams a shareable debug artifact**

   A future debug bundle can package the timeline, state diff, diagnostics, and
   reproduction notes for code review or incident analysis.

## Realistic Use Cases

### Use Case 1: Stale User Profile Memory

A user first says they live in Shanghai and later says they moved to Hangzhou.
The agent appends both memories but retrieval still uses the first one. The
tool should show:

- latest residence memory is Hangzhou
- `selected_city` is Shanghai
- retrieved docs are from Shanghai
- first conflict checkpoint
- first stale selected-city checkpoint
- write evidence showing Hangzhou was appended to `memory_events`

### Use Case 2: Retrieval Context Repetition

A graph retrieves the same source repeatedly, causing context waste and hiding
better evidence. The tool should show duplicate `retrieved_docs` content/source
pairs and the node that wrote them.

### Use Case 3: Checkpoint Growth

A long-running thread keeps appending messages or intermediate data. The tool
should show checkpoint size growth, identify the channel causing it, and tell
the developer whether cleanup, summarization, or retention rules are needed.

### Use Case 4: Resume Or Namespace Confusion

A developer resumes a thread and gets unexpected state. The tool should show
the active `thread_id`, `checkpoint_ns`, parent checkpoint, and the snapshot
that was actually used.

## What A Strong Demo Must Prove

The demo must prove that the tool is not just a JSON viewer. It should answer:

- What did the user expect?
- What did the agent actually use?
- Where did the state diverge?
- Which checkpoint first shows the issue?
- Which state channel gives the strongest evidence?
- What code should the developer inspect next?
