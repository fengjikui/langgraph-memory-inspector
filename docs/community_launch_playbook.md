# Community Launch Playbook

This playbook turns the first public launch into a user-research loop, not a
one-way announcement. The goal is to find developers who have felt LangGraph
state bugs, help them understand the stale-memory demo in under one minute, and
ask for the next checkpoint bug patterns they want the inspector to detect.

## Launch Principle

Lead with the debugging pain:

> My LangGraph agent answered with stale context. The checkpoint store already
> had the evidence, but I needed a tool to connect the final bad answer back to
> the state write that caused it.

Do not lead with stars, generic "AI DevTools", or a feature list. Every channel
should see a version of the same user story:

1. A user moved from Shanghai to Hangzhou.
2. The agent still retrieved Shanghai policy context.
3. The inspector opens the checkpoint timeline, clicks
   `conflicting_residence_memory`, highlights `state.memory_events` in Writes,
   then exports a debug bundle for handoff.

## Launch Gates

- [ ] Repository visibility is intentionally public.
- [ ] CI is green on `main`.
- [ ] README quickstart passes from a fresh clone.
- [ ] `LICENSE`, `CONTRIBUTING.md`, and known limitations are present.
- [ ] Demo GIF exists at `docs/assets/stale-memory-debugging-demo.gif`.
- [ ] SQLite quickstart and read-only Postgres inspection are documented.
- [ ] Namespace selector is documented as a production-store safety feature.
- [ ] Demo script includes diagnostic click, Writes highlight, and Export bundle.
- [ ] First pinned GitHub issue asks for real checkpoint bug patterns.
- [ ] Fixture policy is linked wherever users are asked to share checkpoint data.
- [ ] No launch post asks for stars as the primary call to action.

## Channel Strategy

| Channel | User framing | Best CTA | Avoid |
| --- | --- | --- | --- |
| GitHub issue/discussion | "Help shape checkpoint diagnostics from real bugs." | Share checkpoint stores, write channels, and bug patterns. | Asking only for stars. |
| LangChain Forum / LangGraph category | "I built a local-first checkpoint debugging workflow for LangGraph." | Ask whether the stale-memory diagnostic matches real LangGraph failures. | Posting as product support or dumping a generic link. |
| LangChain Slack | "Showcasing an agent debugging workflow and asking for feedback." | Ask for one concrete debugging pain point in a public thread. | Unsolicited DMs, double-posting, tagging maintainers, lead-gen language. |
| Hacker News Show HN | "Show HN: Local-first inspector for LangGraph checkpoint bugs." | Try the local demo and critique the debugging flow. | Posting before the repo is runnable, launch hype, upvote requests. |
| Reddit r/LangChain | "Here is a concrete LangGraph memory bug and the checkpoint trail." | Ask what state/writes views would help production users. | Cross-posted marketing copy. |
| X / Twitter | "A 30-second GIF of a stale-memory bug becoming a write-level cause." | Ask for bug patterns to turn into diagnostics. | Long thread full of claims without a runnable repo. |
| Chinese developer communities | "Agent 回答错了，不要只看最后一次 LLM response，要看状态是哪里写坏的。" | Ask for LangGraph / Agent 状态调试痛点. | 只讲框架名和 star，不讲真实场景。 |

## Pinned GitHub Issue Draft

Title:

```text
Looking for real LangGraph checkpoint bug patterns
```

Body:

```markdown
LangGraph Memory Inspector started from one reproducible bug:

- the user first says they live in Shanghai
- later they say they moved to Hangzhou
- the agent still retrieves Shanghai context
- the checkpoint store contains both memories, but the final answer used the
  oldest one

The current inspector can:

- read a local SQLite checkpoint database
- inspect a read-only PostgresSaver store
- show checkpoint state, diffs, writes, and diagnostics
- click `conflicting_residence_memory` to jump to the related checkpoint and
  highlight `state.memory_events`
- export a debug bundle for an issue, teammate, or PR

I am looking for real bug patterns from LangGraph users. Useful feedback:

- Which checkpoint backend do you use: SQLite, Postgres, Redis, custom?
- Do you use multiple checkpoint namespaces for one thread?
- Which state channels are hardest to debug?
- Have you seen stale memory, reducer append bugs, wrong checkpoint resume, or
  oversized message history?
- What would you need to safely inspect a production copy locally?

If you can share a file, please follow the fixture policy:
<repo url>/blob/main/docs/fixture_policy.md

The safest inputs are redacted debug bundles, small synthetic fixtures, or
schema-only backend snapshots. Please do not attach raw production checkpoint
stores or unredacted user state.

Repo/demo: <repo url>
```

## English Short Post

```text
I built a local-first inspector for LangGraph checkpoint bugs.

The demo recreates a stale-memory failure: a user moves from Shanghai to
Hangzhou, but the agent still retrieves Shanghai context. The UI lets you click
the diagnostic, jump to the checkpoint, highlight the related `state.memory_events`
write, and export a debug bundle for a teammate or issue.

It currently supports SQLite checkpoint DBs and read-only PostgresSaver stores.
I am looking for real LangGraph bug patterns to turn into diagnostics: stale
memory, reducer append mistakes, wrong resume points, namespace confusion, or
anything else you have hit in production. If you can share evidence, please use
a redacted bundle, synthetic fixture, or schema-only snapshot:
<repo url>/blob/main/docs/fixture_policy.md

Repo/demo: <repo url>
```

## Hacker News Draft

Title:

```text
Show HN: Local-first inspector for LangGraph checkpoint bugs
```

Comment:

```text
I built this after running into a class of LangGraph bugs where the final LLM
answer is wrong, but the real failure happened earlier in checkpoint state.

The included demo is deterministic: the user moves from Shanghai to Hangzhou,
but the agent still answers with Shanghai policy context. The inspector reads
the checkpoint store locally, shows the timeline/diff/writes, and lets you click
the diagnostic to jump to the write that explains the stale memory. It can also
export a JSON debug bundle for a teammate or issue.

Current scope is intentionally narrow: SQLite demo DBs, read-only PostgresSaver
inspection, namespace selection, and one strong debugging path.

I would love feedback from people building stateful agents: what checkpoint
bugs should a tool like this detect next? If you can share fixture-like
evidence, please use a redacted bundle, synthetic fixture, or schema-only
snapshot rather than raw production state.
```

## LangChain Forum / Slack Draft

```text
I am building LangGraph Memory Inspector, a local-first workflow for debugging
checkpoint state instead of guessing from the final LLM response.

The current demo reproduces a stale-memory bug:

- user first lives in Shanghai
- user later moves to Hangzhou
- final answer still uses Shanghai context
- inspector shows the checkpoint timeline, diffs, node writes, and a
  `conflicting_residence_memory` diagnostic
- clicking the diagnostic opens the related checkpoint and highlights
  `state.memory_events`

It supports local SQLite checkpoint DBs and read-only PostgresSaver inspection.
I am looking for feedback on real LangGraph checkpoint pain: namespaces,
reducers, resume bugs, message bloat, custom state channels, or production-store
constraints. If you can share evidence, please use a redacted bundle, synthetic
fixture, or schema-only snapshot and avoid raw/private checkpoint data.

Repo/demo: <repo url>
```

## Reddit Draft

```text
I made a small local-first debugger for LangGraph checkpoints and would love
feedback from people who have debugged stateful agents.

The demo is a concrete memory bug rather than a toy chat UI: a user moves from
Shanghai to Hangzhou, but the agent still answers using Shanghai context. The
checkpoint DB has the evidence. The inspector shows the timeline, state diff,
writes, diagnostics, and can export a debug bundle after you click into the
problem.

It currently handles SQLite checkpoint DBs and read-only PostgresSaver stores.
The most useful feedback would be:

- what checkpoint backend you use
- whether namespaces matter in your setup
- which state channels are hardest to reason about
- what diagnostics would have saved you time in a real incident

If you can share evidence, please use the fixture policy: redacted bundle,
synthetic fixture, or schema-only snapshot. Please do not post raw production
checkpoint state.

Repo/demo: <repo url>
```

## Chinese Long Post Draft

Title:

```text
LangGraph Agent 回答错了，怎么找到是哪一步状态写坏了？
```

Body:

```markdown
我最近在做一个小工具：LangGraph Memory Inspector。

它不是再做一个通用 JSON viewer，而是想解决一个更具体的问题：

> Agent 最后回答错了，但真正的错误往往发生在更早的 checkpoint 里。

我做了一个可复现 demo：

1. 用户先说自己住在上海。
2. 用户后来搬到了杭州。
3. Agent 最后回答时仍然检索了上海的政策上下文。
4. checkpoint 里其实已经有杭州记忆，但 retrieval 节点用了旧的 residence memory。

Inspector 会读取本地 checkpoint store，然后把这条因果链串起来：

- timeline：是哪一个 checkpoint 出现了状态变化
- diff：`memory_events` 从一条 residence 变成两条
- diagnostics：出现 `conflicting_residence_memory`
- writes：点击 diagnostic 后自动高亮 `state.memory_events`
- export：把这条证据链导出成 debug bundle，方便发给同事、issue 或 PR

现在支持：

- SQLite checkpoint DB
- read-only PostgresSaver inspection
- namespace selector
- state / diff / writes / diagnostics
- debug bundle export

我现在最想收集真实开发者的 LangGraph 调试痛点：

- 你们生产里用 SQLite、Postgres，还是其他 checkpoint backend？
- 有没有遇到过同一个 thread 下多个 checkpoint namespace 混淆？
- 哪些 state channel 最难排查？
- 有没有遇到 stale memory、reducer append、resume 错 checkpoint、messages 越积越大的问题？
- 如果只允许在本地读取生产库副本，你会需要什么隐私/脱敏能力？

如果你愿意分享材料，请先看 fixture policy：优先分享 redacted debug bundle、
synthetic fixture 或 schema-only backend snapshot，不要公开贴 raw production
checkpoint 或未脱敏用户状态。

Repo/demo: <repo url>
```

## Chinese Short Social Post

```text
我做了一个 LangGraph checkpoint 调试工具：LangGraph Memory Inspector。

核心 demo：用户从上海搬到杭州，但 Agent 仍然用上海上下文回答。工具会从 checkpoint
timeline 追到 diff、diagnostic、writes，并高亮导致问题的 `state.memory_events`，最后还能导出 debug bundle。

想找真正写 LangGraph / Agent 的同学给反馈：你们最头疼的状态调试问题是什么？

Repo/demo: <repo url>
```

## Early-User Feedback Questions

Ask these one at a time in comments, issues, or DMs only when the other person
has opted into the conversation.

1. Which checkpoint backend do you use today?
2. Do you use multiple `checkpoint_ns` values under the same `thread_id`?
3. Which state channel is hardest to debug in your graph?
4. Have you seen reducer append bugs where old state remains valid-looking?
5. Have you resumed from the wrong checkpoint or thread by accident?
6. Would node-level write attribution help, or is checkpoint-level diff enough?
7. What fields would you need redacted before exporting a debug bundle?
8. How large are your typical checkpoint stores and thread histories?
9. Would you run a local UI against a production database clone?
10. Which diagnostic should exist after `conflicting_residence_memory`?
11. Could your bug be reduced to a redacted, synthetic, or schema-only fixture?

## Anti-Spam Rules

- Post once per channel per meaningful release candidate.
- Rewrite the framing for each community instead of cross-posting identical copy.
- Ask for concrete feedback before asking for stars.
- Do not tag maintainers unless they have invited feedback.
- Do not send unsolicited DMs.
- If a channel has designated showcase/vendor areas, use those areas.
- Bring a runnable repo, a clear demo, and a specific question.

## OpenClaw Consultation Prompt

Use this prompt if OpenClaw is available later:

```text
We are launching LangGraph Memory Inspector, a local-first developer tool for
debugging LangGraph checkpoint state. The demo shows a stale-memory bug where a
user moves from Shanghai to Hangzhou but the agent still retrieves Shanghai
context. The UI connects diagnostic -> checkpoint -> state diff -> writes
highlight -> export debug bundle.

Please critique the positioning and launch plan from a community-growth
perspective. Focus on:

1. Which developer communities are most likely to care?
2. Which launch angle is strongest without sounding like spam?
3. What should the first GitHub issue/discussion ask for?
4. What wording would make LangGraph users feel "this solves my bug"?
5. What channels should we avoid until the product is more mature?

Do not suggest fake engagement, mass DMs, or asking friends to upvote.
```

## Two-Week Launch Rhythm

Day 1:

- Make repo public only after launch gates pass.
- Open the pinned feedback issue.
- Post in one LangGraph-specific channel first.

Day 2-3:

- Reply to every useful comment with a concrete follow-up issue or diagnostic
  idea.
- Update README if repeated questions show the quickstart is unclear.

Day 4-7:

- Post the Chinese long-form version with the GIF and debugging story.
- Open one issue per recurring pain point.

Day 8-14:

- If the local demo is smooth and at least one outside user has tried it, submit
  a Show HN.
- Use the HN thread as product research: answer technical questions, collect
  critiques, and do not ask for votes.
