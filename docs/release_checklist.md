# Release Checklist

Use this before making the repository public or announcing a release candidate.

## Repository Readiness

- [ ] Repository visibility is intentionally set.
- [ ] `LICENSE` is present and linked from `README.md`.
- [ ] `CONTRIBUTING.md` is present and linked from `README.md`.
- [ ] README includes clear known limitations.
- [ ] Generated demo databases, exports, package builds, web build output, and
  test artifacts are ignored by git.
- [ ] Open issues describe the next product gaps instead of hiding them.

## Product Proof

- [ ] CI is green on `main`.
- [ ] README quickstart works from a fresh clone.
- [ ] The stale-memory demo GIF is present at
  `docs/assets/stale-memory-debugging-demo.gif`.
- [ ] SQLite quickstart starts the API and UI against the demo checkpoint DB.
- [ ] `uv run python scripts/use_case_smoke.py --reset-demo` passes.
- [ ] Diagnostic click opens Writes and highlights `state.memory_events`.
- [ ] Debug bundle export shows path, file size, and diagnostic ids.

## Adapter Confidence

- [ ] SQLite reader tests pass.
- [ ] Postgres integration test passes in CI against a real `postgres` service.
- [ ] README explains that Postgres inspection is read-only.
- [ ] Known limitations mention large production stores and namespace handling.

## Launch Assets

- [ ] README explains the problem in the first viewport.
- [ ] Demo story uses the Shanghai -> Hangzhou stale-memory bug.
- [ ] English launch post draft exists.
- [ ] Chinese launch post draft exists.
- [ ] Community feedback asks for checkpoint bug patterns, not only stars.

## Commands

```bash
uv run pytest -q
uv run python scripts/use_case_smoke.py --reset-demo
cd web
npm run build
npm run test:e2e
```

Optional local Postgres gate:

```bash
LGMI_POSTGRES_TEST_DSN="$DATABASE_URL" uv run --extra postgres pytest tests/test_postgres_reader.py -m integration
```
