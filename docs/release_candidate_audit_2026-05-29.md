# v0.1.0 Release Candidate Audit

Date: 2026-05-29
Last refreshed: 2026-05-29 after launch status automation and CI verification

## Summary

The v0.1.0 release candidate is publicly reachable and technically ready for the
first feedback-oriented launch. The demo, tests, CI, fixture policy, release
notes, and community launch materials are in place. The remaining launch gate is
manual/community-facing: upload the GitHub social preview image and then post
the prepared LangChain Forum thread.

## Current Evidence

- Repository: `https://github.com/fengjikui/langgraph-memory-inspector`
- Default branch: `main`
- Current visibility: public (`gh repo view` reports `PUBLIC`)
- Latest audited commit: `9c6572a`
- Latest green CI:
  `https://github.com/fengjikui/langgraph-memory-inspector/actions/runs/26645996221`
- Launch status command:
  `uv run python scripts/launch_status.py`
- Public fresh-clone audit:
  `docs/quickstart_audit_2026-05-29.md`
- Fixture policy: `docs/fixture_policy.md`
- Diagnostic matrix: `docs/diagnostic_matrix.md`
- Launch playbook: `docs/community_launch_playbook.md`
- Forum launch draft: `docs/langchain_forum_launch_post.md`
- Draft release notes: `docs/release_notes_v0.1.0.md`

## Gate Review

| Gate | Status | Evidence |
| --- | --- | --- |
| Repository visibility intentionally set | Pass | `gh repo view fengjikui/langgraph-memory-inspector --json visibility` reports `PUBLIC`. |
| License and contribution docs | Pass | `LICENSE`, `CONTRIBUTING.md`, and README links exist. |
| Known limitations | Pass | README documents namespace, pagination, diagnostic, Postgres, and privacy boundaries. |
| Issue templates | Pass | Bug, checkpoint bug pattern, and feature/diagnostic request forms exist. |
| Fixture privacy policy | Pass | README, CONTRIBUTING, issue template, and launch playbook link to `docs/fixture_policy.md`. |
| Generated artifacts ignored | Pass | `.gitignore` covers demo SQLite files, exports, package builds, web build output, and test artifacts. |
| Open feedback loop | Pass | #20 is open for real checkpoint bug patterns; #23 tracks the remaining social preview upload. |
| CI green on main | Pass | Latest checked main CI is green at run `26645996221`. |
| Public fresh-clone quickstart | Pass | HTTPS clone, `uv sync`, `lgmi doctor --skip-web`, and `lgmi prove-demo --reset-demo --json` pass from `/tmp/lgmi-public-quickstart-audit-20260529`. |
| Demo GIF | Pass | `docs/assets/stale-memory-debugging-demo.gif` exists. |
| Product proof CLI | Pass | `uv run lgmi prove-demo --reset-demo --json` proves the stale-memory path and excludes raw evidence payloads. |
| Diagnostic click e2e | Pass | `npm run test:e2e` covers diagnostic click, Writes highlight, causal chain, and redacted export. |
| Redacted debug bundle | Pass | Tests cover redaction and non-mutating export behavior. |
| Namespace selector | Pass | README, API tests, reader tests, and UI/e2e code cover namespace switching. |
| Timeline pagination | Pass | API and UI tests cover the paginated timeline contract. |
| Safe fixture regression | Pass | `tests/test_fixtures.py` validates fixture metadata and matrix alignment. |
| Diagnostic matrix coverage | Pass | Every current diagnostic is protected by the deterministic demo or a committed safe fixture; no row is unit-only. |
| Postgres confidence | Pass | CI includes a real PostgresSaver integration job, and README documents `scripts/postgres_confidence.py`. |
| Launch assets | Pass | Community launch playbook, public launch packet, and Forum draft are present. |
| Launch status automation | Pass | `scripts/launch_status.py` checks local git status, repository visibility, latest main CI, v0.1.0 release, #20, #23, and the repository OpenGraph image. |

## Current Launch Gates

- [x] Repository is public.
- [x] Main CI is green.
- [x] Public fresh-clone proof path passes.
- [x] GitHub feedback issue #20 is open.
- [x] LangChain Forum launch draft is ready.
- [x] `uv run python scripts/launch_status.py` reports PASS for local git
  status, repository visibility, latest main CI, v0.1.0 release, and #20.
- [ ] GitHub social preview asset still needs manual upload in repository
  Settings; tracked in #23. The verified upload guide is
  `docs/social_preview_upload_guide.md`.
- [ ] LangChain Forum post has not been posted yet.

## CI Annotation Decision

Previous CI runs emitted GitHub Actions Node 20 deprecation annotations even
though the workflow forced JavaScript actions onto Node 24. The workflow now
uses actions whose metadata targets Node 24:

- `actions/checkout@v6.0.2`
- `actions/setup-node@v6.4.0`
- `astral-sh/setup-uv@v8.1.0`

The current main CI run is green with Python tests, the `lgmi prove-demo` proof
CLI, Web build/e2e, and real PostgresSaver integration.

## Recommendation

Proceed with the first feedback-oriented launch after uploading the GitHub
social preview image. The first external post should be the prepared LangChain
Forum / LangGraph category draft, with #20 as the feedback home base.
