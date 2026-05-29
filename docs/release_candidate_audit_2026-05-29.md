# v0.1.0 Release Candidate Audit

Date: 2026-05-29

## Summary

The v0.1.0 release candidate is technically close to public launch: the demo,
tests, CI, docs, fixture policy, and launch materials are in place. The main
remaining launch blocker is repository visibility: the GitHub repository is
currently private, so public launch posts and unauthenticated clone instructions
are not valid yet.

## Current Evidence

- Repository: `https://github.com/fengjikui/langgraph-memory-inspector`
- Default branch: `main`
- Visibility at audit time: private
- Latest audited commit before this RC pass: `bd4946e`
- Latest green CI before this RC pass:
  `https://github.com/fengjikui/langgraph-memory-inspector/actions/runs/26634357989`
- Fresh-clone audit:
  `docs/quickstart_audit_2026-05-29.md`
- Fixture policy: `docs/fixture_policy.md`
- Diagnostic matrix: `docs/diagnostic_matrix.md`
- Launch playbook: `docs/community_launch_playbook.md`
- Draft release notes: `docs/release_notes_v0.1.0.md`

## Gate Review

| Gate | Status | Evidence |
| --- | --- | --- |
| Repository visibility intentionally set | Blocked | `gh repo view` reports `PRIVATE`; public launch requires maintainer approval and is tracked in #19. |
| License and contribution docs | Pass | `LICENSE`, `CONTRIBUTING.md`, and README links exist. |
| Known limitations | Pass | README documents namespace, pagination, diagnostic, Postgres, and privacy boundaries. |
| Issue templates | Pass | Bug, checkpoint bug pattern, and feature/diagnostic request forms exist. |
| Fixture privacy policy | Pass | README, CONTRIBUTING, issue template, and launch playbook link to `docs/fixture_policy.md`. |
| Generated artifacts ignored | Pass | `.gitignore` covers demo SQLite files, exports, package builds, web build output, and test artifacts. |
| Open roadmap issues | Pass | #16 tracks node-level causal chain; #18 tracks release-candidate readiness during this pass. |
| CI green on main | Pass | Latest checked main CI before this pass was green. |
| Fresh-clone quickstart | Pass with condition | Private repo required authenticated clone; otherwise README quickstart passed in the audit. |
| Demo GIF | Pass | `docs/assets/stale-memory-debugging-demo.gif` exists. |
| Product smoke test | Pass | `uv run python scripts/use_case_smoke.py --reset-demo` passes locally. |
| Diagnostic click e2e | Pass | `npm run test:e2e` covers diagnostic click and writes highlight. |
| Redacted debug bundle | Pass | Tests cover redaction and non-mutating export behavior. |
| Namespace selector | Pass | README, API tests, reader tests, and UI code cover namespace switching. |
| Timeline pagination | Pass | API and UI tests cover the paginated timeline contract. |
| Safe fixture regression | Pass | `tests/test_fixtures.py` validates fixture metadata and matrix alignment. |
| Postgres confidence | Pass | CI includes a real PostgresSaver integration job. |
| Launch assets | Pass | Community launch playbook includes English, Chinese, HN, Reddit, LangChain, X, and OpenClaw drafts. |

## CI Annotation Decision

Previous CI runs emitted GitHub Actions Node 20 deprecation annotations even
though the workflow forced JavaScript actions onto Node 24. The RC pass upgrades
the workflow to actions whose metadata uses `node24`:

- `actions/checkout@v6.0.2`
- `actions/setup-node@v6.4.0`
- `astral-sh/setup-uv@v8.1.0`

The release-candidate commit must pass CI after this upgrade. If annotations
remain, they should be tracked as a non-blocking GitHub Actions ecosystem issue
only if the jobs are green.

## Remaining Launch Blockers

- Public repository visibility still needs explicit maintainer approval and is
  tracked in #19.
- #16 remains the next meaningful product improvement, but it is not required
  for the first v0.1.0 release candidate because the current demo flow is
  already runnable, tested, and documented.

## Recommendation

After the RC commit passes CI, the project can be treated as a private release
candidate. Public launch should wait until the maintainer intentionally switches
the repository to public and confirms the launch post timing.
