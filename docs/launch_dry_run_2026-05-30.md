# First External User Launch Dry Run

Date: 2026-05-30
Repository: `https://github.com/fengjikui/langgraph-memory-inspector`
Audited commit: `2cd6407`

## Goal

Walk the project as a first external developer would: discover the repository,
install it, prove the stale-memory failure, and decide whether it is safe enough
to share checkpoint evidence with the maintainer.

## User Scenario

A LangGraph developer has an agent that should update the user's residence from
Shanghai to Hangzhou. The final answer still uses Shanghai context. The
developer does not know whether the bug came from memory extraction, retrieval,
checkpoint resume behavior, or stale context carried across nodes.

The value test is not "can the demo run?" The value test is:

1. Can the developer recognize the problem from the first screen?
2. Can they verify the failure locally without a production database?
3. Can they inspect the state transition that made the answer wrong?
4. Can they share a useful, redacted evidence bundle without leaking prompts or
   private user content?

## Entry Path

Expected public entry points:

- GitHub social card after the manual social preview upload.
- README first viewport.
- LangChain Forum / LangGraph category launch post.
- GitHub issue #20 for real checkpoint bug patterns.

Current status:

- The social preview image exists and validates locally.
- GitHub still needs the Settings upload tracked in #23.
- The README and launch post already frame the tool around checkpoint evidence,
  stale memory, and redacted feedback.

## Commands Replayed

Local setup and broad release smoke:

```bash
uv run python scripts/release_smoke.py
```

Result from the latest local run:

- Python tests: `86 passed, 1 skipped`
- Social preview asset validation: passed
- Launch copy guardrails: passed
- `lgmi prove-demo --reset-demo`: passed
- Issue-safe debug bundle smoke: passed
- Package install smoke: passed

Remote launch status:

```bash
uv run python scripts/launch_status.py
```

Result:

- PASS: local git status
- PASS: repository visibility
- PASS: repository discoverability
- PASS: latest main CI
- PASS: v0.1.0 release
- PASS: #20 feedback issue
- MANUAL: #23 social preview upload
- MANUAL: repository OpenGraph image

Latest remote CI:

```text
https://github.com/fengjikui/langgraph-memory-inspector/actions/runs/26647844240
```

Result: success for Python tests, Web build/e2e, and real Postgres integration.

## User-Value Findings

The current project is credible for a first feedback-oriented launch because it
proves four separate promises:

- It can reproduce a concrete LangGraph memory bug from checkpoint evidence.
- It can navigate from the wrong final answer back to node/write attribution.
- It can produce a redacted issue bundle and audit that bundle before sharing.
- It can install as a built wheel and expose the same core `lgmi` commands.

The weakest remaining step is not core debugging behavior. It is external
presentation: GitHub still shows the default OpenGraph image until the social
preview is uploaded through repository Settings.

## Promotion Readiness

Ready to post after the manual social preview upload:

- LangChain Forum draft: `docs/langchain_forum_launch_post.md`
- Public launch packet: `docs/public_launch_packet.md`
- Community launch playbook: `docs/community_launch_playbook.md`
- Feedback issue: `https://github.com/fengjikui/langgraph-memory-inspector/issues/20`

The first post should ask for concrete checkpoint bug patterns, not stars. Stars
are a side effect. The product loop needs real failure cases that can become
fixtures, diagnostics, and regression tests.

## Next Best Action

Upload `docs/assets/github-social-preview.png` in GitHub repository Settings,
then close #23 only after `scripts/launch_status.py` reports the OpenGraph gate
as `PASS` or the preview is externally verified after cache propagation.
