# Relocation Policy Agent

This is a deliberately small LangGraph application for generating useful
checkpoint history.

The scenario:

1. The user says they live in Shanghai.
2. The user says they moved to Hangzhou.
3. The user asks which local benefits to check first.

The app intentionally contains a memory bug: it appends residence memories
without invalidating older ones, then retrieves policy context from the first
residence instead of the newest residence.

That makes it a good fixture for LangGraph Memory Inspector because a developer
should be able to inspect the checkpoint timeline and discover:

- conflicting residence memory
- stale retrieval context
- the node that wrote the conflicting state
- checkpoint growth across turns

## Run

From the repository root, prepare this fixture and start the Inspector API:

```bash
uv run lgmi demo
```

Only generate or refresh the checkpoint database:

```bash
uv run lgmi demo --prepare-only
```

Run the demo script directly:

```bash
uv run python examples/relocation_policy_agent/run_demo.py
```

Use a real model for the final response:

```bash
export OPENAI_API_KEY=...
uv run python examples/relocation_policy_agent/run_demo.py --use-llm
```

Reset the generated checkpoint database:

```bash
uv run python examples/relocation_policy_agent/run_demo.py --reset
```
