# Contributing

Thanks for helping make LangGraph Memory Inspector more useful for real agent
debugging. The project is still early, so the best contributions are small,
evidence-backed improvements that make one developer workflow clearer.

## Good First Contributions

- Add a small reproducible checkpoint bug pattern.
- Improve a diagnostic so it points to a clearer state path or write channel.
- Add tests for a real LangGraph checkpoint shape.
- Improve docs where a first-time user might get stuck.
- Validate the Postgres reader against another `PostgresSaver` fixture.

Please avoid broad rewrites unless an issue already describes the migration.

## Local Setup

Install Python and Node dependencies:

```bash
uv sync --extra postgres
cd web
npm install
```

Generate the deterministic demo checkpoint database:

```bash
uv run python examples/relocation_policy_agent/run_demo.py
```

Start the local API:

```bash
uv run lgmi inspect examples/relocation_policy_agent/data/checkpoints.sqlite --no-browser --port 8765
```

Start the web UI in another terminal:

```bash
cd web
npm run dev
```

Open `http://127.0.0.1:5173/`.

## Verification Before A PR

Run the product smoke test:

```bash
uv run python scripts/use_case_smoke.py --reset-demo
```

Run backend tests:

```bash
uv run pytest -q
```

Run frontend build and e2e:

```bash
cd web
npm run build
npm run test:e2e
```

Optional Postgres integration test:

```bash
LGMI_POSTGRES_TEST_DSN="$DATABASE_URL" uv run --extra postgres pytest tests/test_postgres_reader.py -m integration
```

## Issue Workflow

Before implementing a larger change, open or comment on an issue with:

- the developer workflow or bug pattern being improved
- the checkpoint store involved, such as SQLite or Postgres
- the evidence you will use to prove the change works
- any generated files the change may create

For bug reports, include:

- LangGraph version and checkpointer type
- whether the store is SQLite, Postgres, or another backend
- a minimal checkpoint database or redacted debug bundle when possible
- expected state path and actual state path if known

For checkpoint pattern reports or fixture contributions, follow
`docs/fixture_policy.md`. Public fixtures must be synthetic, redacted, or
schema-only, and should include metadata for backend, LangGraph version,
namespace shape, state channels, and expected diagnostics.

## Storage Hygiene

Do not commit generated artifacts unless they are intentionally tiny fixtures.
These are disposable and should stay out of commits:

- `examples/relocation_policy_agent/data/*.sqlite`
- `examples/relocation_policy_agent/data/*.sqlite-shm`
- `examples/relocation_policy_agent/data/*.sqlite-wal`
- `exports/`
- `dist/`
- `web/dist/`
- `web/test-results/`
- caches such as `.pytest_cache/` and `__pycache__/`

Debug bundles are useful for review, but they may contain private state. Share
only redacted bundles in public issues. Do not commit raw production checkpoint
stores, raw debug bundles, user chats, customer data, secrets, or proprietary
retrieval content.

## Pull Request Shape

Keep PRs focused. A good PR usually includes:

- one user-facing improvement or one adapter/diagnostic fix
- tests or a smoke command proving the behavior
- a short note about storage or privacy impact
- screenshots only when the UI changed

The maintainer may ask for a smaller slice when a PR combines product, adapter,
and visual changes at once.
