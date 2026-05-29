# Release Checklist

Use this before making the repository public or announcing a release candidate.

Current audit: `docs/release_candidate_audit_2026-05-29.md`.
Draft release notes: `docs/release_notes_v0.1.0.md`.

## Repository Readiness

- [x] Repository visibility is intentionally set for public launch.
- [x] `LICENSE` is present and linked from `README.md`.
- [x] `CONTRIBUTING.md` is present and linked from `README.md`.
- [x] README includes clear known limitations.
- [x] GitHub issue templates exist for bugs, checkpoint bug patterns, and
  feature/diagnostic requests.
- [x] Fixture policy explains acceptable public inputs and is linked from
  checkpoint feedback entry points.
- [x] Generated demo databases, exports, package builds, web build output, and
  test artifacts are ignored by git.
- [x] Open issues describe the next product gaps instead of hiding them.

## Product Proof

- [x] CI is green on `main`.
- [x] README quickstart works from a fresh clone.
- [x] The stale-memory demo GIF is present at
  `docs/assets/stale-memory-debugging-demo.gif`.
- [x] SQLite quickstart starts the API and UI against the demo checkpoint DB.
- [x] `uv run python scripts/use_case_smoke.py --reset-demo` passes.
- [x] Diagnostic click opens Writes and highlights `state.memory_events`.
- [x] Diagnostics include reducer append duplicate and unexpected parent
  checkpoint warning rules with documented false-positive boundaries.
- [x] Debug bundle export shows path, file size, and diagnostic ids.
- [x] Redacted debug bundle export records redaction mode and masks private
  message/evidence fields without modifying the checkpoint store.
- [x] Namespace selector is visible for multi-namespace threads and switching
  namespaces changes the timeline without changing thread context.
- [x] Timeline API returns a paginated contract and the UI can load earlier
  checkpoints without losing the selected thread or namespace.
- [x] At least one safe fixture proves a real reported bug pattern through a
  regression test.

## Adapter Confidence

- [x] SQLite reader tests pass.
- [x] Postgres integration test passes in CI against a real `postgres` service.
- [x] README explains that Postgres inspection is read-only.
- [x] Known limitations mention large production stores and cross-namespace
  boundaries.

## Launch Assets

- [x] README explains the problem in the first viewport.
- [x] Demo story uses the Shanghai -> Hangzhou stale-memory bug.
- [x] `docs/community_launch_playbook.md` exists and links every channel to a
  user-problem framing.
- [x] English launch post draft exists.
- [x] Chinese launch post draft exists.
- [x] Pinned GitHub feedback issue draft exists.
- [x] Feedback drafts point users to the fixture policy before asking for
  checkpoint data.
- [x] OpenClaw consultation prompt exists for distribution critique.
- [x] Community feedback asks for checkpoint bug patterns, not only stars.
- [x] GitHub social preview asset exists at
  `docs/assets/github-social-preview.png`.
- [ ] GitHub social preview asset has been uploaded in repository Settings.

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
uv run --extra postgres python scripts/postgres_confidence.py --dsn "$DATABASE_URL"
```
