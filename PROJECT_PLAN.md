# LangGraph Memory Inspector Project Plan

## Objective

Build a local-first LangGraph checkpoint and memory inspector that can explain
the Relocation Policy Agent demo failure:

- the user moved from Shanghai to Hangzhou
- memory contains both residence values
- retrieval still selects Shanghai
- diagnostics marks `conflicting_residence_memory`

The MVP should be strong enough for an interview demo before it attempts to be
a general production tool.

## Parallel Workstreams

### Backend

Owner scope:

- `src/lgmi/checkpoint_reader.py`
- `src/lgmi/api.py`
- `src/lgmi/cli.py`
- `tests/test_checkpoint_reader.py`

Deliverable:

- Read LangGraph SQLite checkpoint databases.
- Expose thread, checkpoint, checkpoint detail, and writes APIs.
- Provide a simple local server command.

### Analysis

Owner scope:

- `src/lgmi/analysis.py`
- `tests/test_analysis.py`

Deliverable:

- Diff two state snapshots.
- Detect conflicting memory, stale selected city, repeated retrieval context,
  oversized message history, and checkpoint size spikes.
- Summarize node writes for the UI.

### Frontend

Owner scope:

- `web/**`

Deliverable:

- React developer-tool UI scaffold.
- Thread selector, checkpoint timeline, state viewer, writes viewer, diff viewer,
  and diagnostics panel.
- Mock data path that mirrors the relocation demo before backend integration.

### Docs And Packaging

Owner scope:

- `docs/architecture.md`
- `docs/demo_script.md`
- `docs/resume_project.md`
- `docs/mvp_checklist.md`

Deliverable:

- Interview-ready narrative and demo script.
- Architecture and data-flow explanation.
- MVP Definition of Done.

## Integration Order

1. Keep the demo agent stable. It is the fixture for every other layer.
2. Land analysis functions because backend and frontend can both consume their
   output shape.
3. Land backend reader and API.
4. Wire backend API to the frontend.
5. Update README with final run commands.
6. Run the complete demo from a clean checkout:
   - `uv sync`
   - `uv run python examples/relocation_policy_agent/run_demo.py --reset`
   - start inspector
   - open UI
   - identify the stale Shanghai retrieval from checkpoint history

## Storage Hygiene

Checkpoint databases and export bundles are generated artifacts. They must not
be committed by default.

Safe-to-delete artifacts:

- `examples/relocation_policy_agent/data/*.sqlite`
- `examples/relocation_policy_agent/data/*.sqlite-shm`
- `examples/relocation_policy_agent/data/*.sqlite-wal`
- `exports/`

Any future automatic export, cache, trace, or report generation must include an
explicit size or retention policy before it is considered complete.
