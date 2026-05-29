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
- Use-case smoke test proving the stale-memory evidence chain.
- Explicit debug bundle export for teammate, issue, and PR handoff.
- Community launch playbook with channel-specific drafts and feedback prompts
  in `docs/community_launch_playbook.md`.

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

### Namespace Selector

User value: LangGraph production stores can contain multiple checkpoint
namespaces. A developer needs to know which namespace they are inspecting and
switch deliberately.

Status: implemented for SQLite, Postgres reader APIs, backend routes, and the
thread sidebar UI.

Acceptance criteria:

- [x] API exposes namespaces per thread.
- [x] UI shows active namespace.
- [x] UI can switch namespace without losing thread context.
- [x] SQLite and Postgres readers both preserve namespace data.

### Debug Bundle Export

User value: once a developer finds a bug, they need a shareable artifact for a
teammate, issue, or pull request.

Status: implemented for SQLite, backend API, CLI, and checkpoint detail UI.

Acceptance criteria:

- [x] Export includes summary, timeline slice, selected checkpoint state, writes,
  diagnostics, and reproduction notes.
- [x] Export is explicit and writes to `exports/`.
- [x] Export response displays file path and size.
- [x] Checkpoint detail UI exposes a user-triggered Export action.
- [x] README documents that exports are safe to delete.

### Fresh-Clone Quickstart Audit

User value: first-time users should not need project context from the maintainer
to run the demo.

Acceptance criteria:

- Run from a clean checkout using only README commands.
- Record every missing command, dependency, or confusing output.
- Update README and docs until the path is smooth.
- Keep the audit log in docs.

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
