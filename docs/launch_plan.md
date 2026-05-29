# Launch Plan

## Goal

Make LangGraph Memory Inspector understandable and credible to a developer in
under one minute, then give them a low-friction path to try the stale-memory
demo locally.

## Current Launch Assets

- README with problem-first positioning and CI badge.
- Real stale-memory demo GIF in `docs/assets/stale-memory-debugging-demo.gif`.
- Deterministic relocation-policy LangGraph demo.
- Local SQLite inspector path.
- Read-only PostgresSaver reader with CI-backed Postgres integration.
- `lgmi prove-demo` product proof command for the stale-memory evidence chain.
- Explicit debug bundle export for teammate, issue, and PR handoff.
- Community launch playbook with channel-specific drafts and feedback prompts
  in `docs/community_launch_playbook.md`.
- Public launch packet with copy-paste-ready posts, reply templates, and
  channel tracking in `docs/public_launch_packet.md`.

## Pre-Public Checklist

- [x] Confirm repository visibility is public.
- [x] Add `LICENSE`.
- [x] Add `CONTRIBUTING.md`.
- [x] Add issue templates for bug reports and feature requests.
- [x] Add a release checklist.
- [x] Add a community launch playbook.
- [x] Add a short "known limitations" section to README.
- [x] Verify README quickstart from a fresh public clone.
- Keep generated checkpoint DBs and export artifacts out of commits.

## Next Product Issues

### Implemented v0.1.0 Issues

- Namespace selector for multi-namespace checkpoint stores.
- Debug bundle export for teammate, issue, and PR handoff.
- Public fresh-clone quickstart and product proof path.
- [#24](https://github.com/fengjikui/langgraph-memory-inspector/issues/24):
  RAG stale-context fixture and `stale_retrieved_context` diagnostic.

### Open Roadmap Issues

These issues are intentionally user-value shaped so community feedback can turn
into fixtures, diagnostics, and tests:

- [#25](https://github.com/fengjikui/langgraph-memory-inspector/issues/25):
  validate `ShallowPostgresSaver` and newer saver variants.
- [#26](https://github.com/fengjikui/langgraph-memory-inspector/issues/26):
  improve large checkpoint-store navigation.

## Community Launch

Detailed drafts and channel rules live in
`docs/community_launch_playbook.md`. The launch should be treated as a
feedback loop, not a one-way announcement.

Core story:

- A user moves from Shanghai to Hangzhou.
- The agent still answers with Shanghai context.
- The inspector clicks `conflicting_residence_memory`, jumps to the checkpoint,
  highlights `state.memory_events` in Writes, and exports a debug bundle.

Primary feedback ask:

- Tell us which checkpoint bug patterns real LangGraph users want detected
  next: stale memory, reducer append mistakes, wrong resume points, namespace
  confusion, message bloat, or production-store constraints.

Anti-spam rule:

- Ask for concrete feedback before asking for stars, rewrite posts per channel,
  and do not use unsolicited DMs or upvote requests.

## Release Candidate Definition

The first public release candidate is ready when:

- CI is green on main.
- README quickstart works from a fresh clone.
- SQLite demo and Postgres integration are both documented.
- The next user-centered product issue is explicit, even if only one or two
  issues remain open after the release-candidate cleanup.
- The repo has license, contribution notes, and clear known limitations.
- The GitHub social preview image has been uploaded before broad social
  posting.
