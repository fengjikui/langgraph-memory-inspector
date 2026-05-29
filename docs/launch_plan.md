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

## Pre-Public Checklist

- Confirm repository visibility.
- [x] Add `LICENSE`.
- [x] Add `CONTRIBUTING.md`.
- Add issue templates for bug reports and feature requests.
- [x] Add a release checklist.
- [x] Add a short "known limitations" section to README.
- Verify README quickstart from a fresh clone.
- Keep generated checkpoint DBs and export artifacts out of commits.

## Next Product Issues

### Namespace Selector

User value: LangGraph production stores can contain multiple checkpoint
namespaces. A developer needs to know which namespace they are inspecting and
switch deliberately.

Acceptance criteria:

- API exposes namespaces per thread.
- UI shows active namespace.
- UI can switch namespace without losing thread context.
- SQLite and Postgres readers both preserve namespace data.

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

## Community Posts

### English Short Post

Working title:

> Debug LangGraph memory bugs from checkpoints, not guesses

Draft:

> I built a local-first inspector for LangGraph checkpoints. The demo recreates
> a stale-memory bug: a user moves from Shanghai to Hangzhou, but retrieval
> still uses Shanghai. The inspector jumps from diagnostic -> checkpoint ->
> state diff -> node writes, and now supports SQLite plus read-only Postgres
> checkpoint stores.

Call to action:

> Try the deterministic demo, open the GIF, and tell me which checkpoint bug
> patterns you want detected next.

### Chinese Long Post

Working title:

> LangGraph Agent 回答错了，怎么找到是哪一步状态写坏了？

Outline:

1. 为什么 Agent debugging 不只是看最后一次 LLM response。
2. checkpoint / writes / memory_events 的关系。
3. stale memory demo：上海 -> 杭州 -> 仍然检索上海。
4. Inspector 如何从 diagnostic 跳到 checkpoint 和 write channel。
5. 为什么 local-first 和 read-only Postgres 很重要。
6. 下一步：namespace selector、debug bundle、更多真实 bug patterns。

## Release Candidate Definition

The first public release candidate is ready when:

- CI is green on main.
- README quickstart works from a fresh clone.
- SQLite demo and Postgres integration are both documented.
- At least three user-centered issues are open.
- The repo has license, contribution notes, and clear known limitations.
