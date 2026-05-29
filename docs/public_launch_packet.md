# Public Launch Packet

Last verified: 2026-05-29

This packet is the copy-paste layer for the first public launch. Keep the tone
practical: lead with a concrete LangGraph checkpoint debugging problem, ask for
real bug patterns, and do not make stars the main call to action. The
copy-paste-ready first external post lives in
`docs/langchain_forum_launch_post.md`.

## Current Proof Points

- Public repo:
  https://github.com/fengjikui/langgraph-memory-inspector
- Release:
  https://github.com/fengjikui/langgraph-memory-inspector/releases/tag/v0.1.0
- Pinned feedback issue:
  https://github.com/fengjikui/langgraph-memory-inspector/issues/20
- Fixture policy:
  https://github.com/fengjikui/langgraph-memory-inspector/blob/main/docs/fixture_policy.md
- Diagnostic matrix:
  https://github.com/fengjikui/langgraph-memory-inspector/blob/main/docs/diagnostic_matrix.md
- Social preview asset:
  `docs/assets/github-social-preview.png`
- Social preview upload guide:
  `docs/social_preview_upload_guide.md`
- LangChain Forum launch draft:
  `docs/langchain_forum_launch_post.md`

Known manual gate before broad posting:

- Upload `docs/assets/github-social-preview.png` in repository Settings >
  Social preview. `docs/social_preview_upload_guide.md` has the verified
  asset checks and exact steps. Issue #23 tracks this.

## Launch Order

1. GitHub issue #20 is the feedback home base.
2. LangChain Forum / LangGraph category is the first external post.
3. LangChain Slack gets a shorter showcase version after the Forum post exists.
4. X / LinkedIn can reuse the short hook and GIF.
5. V2EX or a Chinese developer community gets the Chinese long post.
6. Reddit gets a discussion-first version only after the repo has at least one
   external response or clear maintainer replies.
7. Show HN waits until at least one outside user has tried the quickstart or
   commented on #20.

## Do Not Ship

- Do not ask people to star as the primary CTA.
- Do not claim this replaces LangSmith or LangGraph Studio.
- Do not say it is production-ready for every checkpoint backend.
- Do not ask for raw production checkpoint stores.
- Do not post identical copy across communities.
- Do not tag maintainers unless they invited feedback.

Run the launch-copy guardrail before broad posting:

```bash
uv run python scripts/validate_launch_copy.py
```

## Primary Positioning

One-liner:

```text
LangGraph Memory Inspector is a local-first checkpoint forensics tool for finding the state write behind a bad agent answer.
```

Short story:

```text
The demo reproduces a stale-memory bug: the user moves from Shanghai to Hangzhou, but the agent still answers with Shanghai context. The checkpoint store has the evidence; the inspector connects final answer -> diagnostic -> checkpoint -> write chain, including stale retrieved context and the node path extract_profile -> retrieve_policy -> answer.
```

First feedback ask:

```text
What LangGraph checkpoint bug pattern should this detect next?
```

## LangChain Forum Post

Title:

```text
Local-first checkpoint inspector for debugging LangGraph stale memory bugs
```

Body:

````markdown
I am building LangGraph Memory Inspector, a local-first checkpoint forensics workflow for debugging stateful LangGraph apps.

The current demo is intentionally concrete:

- the user first says they live in Shanghai
- later they say they moved to Hangzhou
- the agent still answers with Shanghai policy context
- the inspector surfaces stale retrieved context, not only conflicting profile
  memory
- the checkpoint store contains the evidence, but the root cause is several checkpoints before the final answer

The Inspector reads the checkpoint store locally and shows:

- checkpoint timeline
- state snapshots and diffs
- node/channel writes
- deterministic diagnostics such as `conflicting_residence_memory` and
  `stale_selected_city`, plus `stale_retrieved_context`
- additional diagnostics for repeated retrieved context, reducer append
  duplicates, message/history bloat, namespace confusion, checkpoint size
  spikes, and wrong-resume lineage jumps
- node-level causal path such as
  `extract_profile -> retrieve_policy -> answer`
- compact causal chain from diagnostic -> checkpoint range -> write evidence
- checkpoint id prefix filtering for jumping from logs to the suspicious
  timeline range
- redacted debug bundle export for issues, teammates, or PRs

Quickstart:

```bash
uv sync
uv run lgmi doctor
uv run lgmi prove-demo --reset-demo
uv run lgmi demo --build-ui
```

To try it on your own local SQLite checkpoint copy:

```bash
uv run lgmi doctor --sqlite-db ./checkpoints.sqlite
uv run lgmi inspect ./checkpoints.sqlite --build-ui
```

For a PostgresSaver store:

```bash
uv sync --extra postgres
uv run --extra postgres lgmi doctor --postgres-conninfo "$DATABASE_URL" --postgres-schema public
uv run --extra postgres lgmi inspect-postgres "$DATABASE_URL" --schema public --build-ui
```

`ShallowPostgresSaver` latest-only schemas are detected and reported as
unsupported because they cannot provide checkpoint timelines. Doctor reports
redact connection credentials and do not include checkpoint state.

If you want to test the Postgres path before connecting a private store:

```bash
uv run --extra postgres python scripts/postgres_confidence.py --dsn "$DATABASE_URL" --keep-schema
```

Repo:
https://github.com/fengjikui/langgraph-memory-inspector

I am looking for real LangGraph checkpoint bug patterns to turn into deterministic diagnostics. The most useful feedback:

- Which checkpoint backend do you use?
- Do you use multiple `checkpoint_ns` values under one `thread_id`?
- Which state channel is hardest to debug?
- Have you seen stale memory, stale retrieved context, repeated retrieval, reducer append bugs, wrong resume points, namespace confusion, or message bloat?
- Have you had only a checkpoint id/prefix from logs and needed to jump to that
  part of the timeline?
- What would you need to safely inspect a production copy locally?

Every current diagnostic is backed by the deterministic demo or a committed
safe fixture in the diagnostic matrix; I am especially looking for
production-shaped patterns that should become the next fixture or diagnostic.

If you can share evidence, please use a redacted bundle, synthetic fixture, or schema-only snapshot. Please do not share raw production checkpoint stores:
https://github.com/fengjikui/langgraph-memory-inspector/blob/main/docs/fixture_policy.md
````

## LangChain Slack Post

```text
Sharing a local-first LangGraph checkpoint debugging workflow, and looking for real bug patterns.

Demo bug: a user moves from Shanghai to Hangzhou, but the agent still answers with Shanghai context. LangGraph Memory Inspector reads the checkpoint store locally and connects final answer -> diagnostic -> checkpoint -> write evidence, including stale retrieved context.

Repo/demo: https://github.com/fengjikui/langgraph-memory-inspector
Feedback home base: https://github.com/fengjikui/langgraph-memory-inspector/issues/20

I am especially interested in stale memory, stale retrieved context, repeated retrieval, reducer append mistakes, wrong resume points, namespace confusion, message/history bloat, and production-store constraints. Please share redacted/synthetic/schema-only evidence only; no raw production state.
```

## X / LinkedIn Short Thread

Post 1:

```text
The bad LLM answer was not the root cause.

The checkpoint write was.

I built LangGraph Memory Inspector: a local-first checkpoint forensics tool for debugging stateful LangGraph agents.
```

Post 2:

```text
Demo:

1. User lives in Shanghai
2. User moves to Hangzhou
3. Agent still answers with Shanghai context

The checkpoint store already has the evidence. The tool connects:

final answer -> diagnostic -> checkpoint -> state write
```

Post 3:

```text
Current scope:

- SQLite checkpoint stores
- read-only PostgresSaver inspection
- safe detection for unsupported ShallowPostgresSaver latest-only schemas
- Postgres confidence script for validating the PostgresSaver path
- timeline, diff, writes, diagnostics, checkpoint id prefix filters
- node-level causal path such as extract_profile -> retrieve_policy -> answer
- redacted debug bundle export

Repo:
https://github.com/fengjikui/langgraph-memory-inspector
```

Post 4:

```text
Looking for real LangGraph checkpoint bug patterns:

- stale memory
- reducer append mistakes
- wrong resume point
- namespace confusion
- message/history bloat
- stale retrieved context
- long timelines where you only have a checkpoint id/prefix

Feedback issue:
https://github.com/fengjikui/langgraph-memory-inspector/issues/20
```

## Chinese Long Post

Title:

```text
做了一个 LangGraph checkpoint 调试工具：从错误答案追到是哪一步状态写坏了
```

Body:

````markdown
我最近做了一个小工具：LangGraph Memory Inspector。

它不是通用 JSON viewer，而是想解决一个更具体的问题：

> Agent 最后回答错了，但真正的错误往往发生在更早的 checkpoint 里。

我做了一个可复现 demo：

1. 用户先说自己住在上海。
2. 用户后来搬到了杭州。
3. Agent 最后回答时仍然检索了上海的政策上下文。
4. checkpoint 里其实已经有杭州记忆，但 retrieval 节点用了旧的 residence memory。

Inspector 会读取本地 checkpoint store，然后把这条证据链串起来：

- timeline：是哪一个 checkpoint 出现了状态变化
- diff：`memory_events` 从一条 residence 变成两条
- diagnostics：出现 `conflicting_residence_memory`、`stale_selected_city`
  和 `stale_retrieved_context`
- writes：点击 diagnostic 后高亮 `state.memory_events`
- causal chain：从诊断回到相关 checkpoint/write/node，并展示
  `extract_profile -> retrieve_policy -> answer`
- filter：如果日志里只有 checkpoint id 前缀，可以直接缩小到可疑
  timeline 范围
- export：导出 redacted debug bundle，方便发给同事、issue 或 PR

快速试一下：

```bash
uv sync
uv run lgmi doctor
uv run lgmi prove-demo --reset-demo
uv run lgmi demo --build-ui
```

如果想先检查自己的 SQLite checkpoint 文件：

```bash
uv run lgmi doctor --sqlite-db ./checkpoints.sqlite
uv run lgmi inspect ./checkpoints.sqlite --build-ui
```

如果使用 PostgresSaver：

```bash
uv sync --extra postgres
uv run --extra postgres lgmi doctor --postgres-conninfo "$DATABASE_URL" --postgres-schema public
uv run --extra postgres lgmi inspect-postgres "$DATABASE_URL" --schema public --build-ui
```

如果想先用一个安全的小 PostgresSaver schema 验证链路：

```bash
uv run --extra postgres python scripts/postgres_confidence.py --dsn "$DATABASE_URL" --keep-schema
```

现在支持：

- SQLite checkpoint DB
- read-only PostgresSaver inspection
- unsupported ShallowPostgresSaver latest-only schema detection
- PostgresSaver confidence script
- checkpoint namespace selector
- state / diff / writes / diagnostics / causal path / checkpoint id prefix filter
- debug bundle export

我现在最想收集真实开发者的 LangGraph 调试痛点：

- 你们生产里用 SQLite、Postgres，还是其他 checkpoint backend？
- 有没有遇到过同一个 thread 下多个 checkpoint namespace 混淆？
- 哪些 state channel 最难排查？
- 有没有遇到 stale memory、stale retrieved context、reducer append、resume
  错 checkpoint、messages 越积越大的问题？
- 有没有遇到日志里只有 checkpoint id / prefix，需要直接跳到那段 timeline？
- 如果只允许在本地读取生产库副本，你会需要什么隐私/脱敏能力？

如果你愿意分享材料，请优先分享 redacted debug bundle、synthetic fixture 或 schema-only backend snapshot，不要公开贴 raw production checkpoint 或未脱敏用户状态。

Repo:
https://github.com/fengjikui/langgraph-memory-inspector

反馈入口：
https://github.com/fengjikui/langgraph-memory-inspector/issues/20
````

## Reddit Discussion Post

Title:

```text
I built a local-first debugger for LangGraph checkpoint state. What state bugs should it detect next?
```

Body:

```text
I built a small local-first inspector for LangGraph checkpoints and would love feedback from people who have debugged stateful agents.

The demo is a concrete memory bug: a user moves from Shanghai to Hangzhou, but the agent still answers using Shanghai context. The checkpoint DB has the evidence. The inspector shows the timeline, state diff, writes, deterministic diagnostics, stale retrieved context, checkpoint id prefix filtering, and a causal chain from diagnostic to checkpoint/write evidence.

It currently supports SQLite checkpoint DBs and read-only PostgresSaver inspection. It can also export a redacted debug bundle for a teammate, issue, or PR.

I am not trying to replace LangSmith or LangGraph Studio. This is focused on local checkpoint forensics: when did this persisted state become wrong, and which write should I inspect first?

Repo/demo:
https://github.com/fengjikui/langgraph-memory-inspector

Most useful feedback:

- what checkpoint backend you use
- whether checkpoint namespaces matter in your setup
- which state channels are hardest to reason about
- what diagnostics would have saved you time in a real incident

Please do not share raw production checkpoint state. Redacted, synthetic, or schema-only evidence is safer:
https://github.com/fengjikui/langgraph-memory-inspector/blob/main/docs/fixture_policy.md
```

## Show HN Draft

Title:

```text
Show HN: Local-first inspector for LangGraph checkpoint bugs
```

Comment:

```text
I built this after running into a class of LangGraph bugs where the final LLM answer is wrong, but the real failure happened earlier in checkpoint state.

The included demo is deterministic: the user moves from Shanghai to Hangzhou, but the agent still answers with Shanghai policy context. The inspector reads the checkpoint store locally, shows the timeline/diff/writes, and lets you click the diagnostic to jump to the write evidence. It can also export a redacted JSON debug bundle for a teammate or issue.

Current scope is intentionally narrow: SQLite demo DBs, read-only PostgresSaver inspection, namespace selection, deterministic diagnostics, and one strong debugging path.

I would love feedback from people building stateful agents: what checkpoint bugs should a tool like this detect next?

Repo:
https://github.com/fengjikui/langgraph-memory-inspector
```

## Reply Templates

Demo startup issue:

```text
Thanks for trying it. Could you run `uv run lgmi doctor --issue` from the repo root and paste the generated Markdown into the issue? It checks the demo checkpoint, API reader, Node.js/npm, and web dependency state without asking for any private checkpoint data.
```

Own SQLite DB issue:

```text
Thanks for the report. Could you run `uv run lgmi doctor --sqlite-db ./checkpoints.sqlite --issue` against your local copy and paste the generated Markdown? It includes file health, counts, and namespaces, but not checkpoint state or message content.
```

Checkpoint pattern with safe evidence:

```text
This sounds like the kind of pattern the inspector should learn from. If you can share a local SQLite checkpoint copy safely, please run `uv run lgmi export-debug-bundle ./checkpoints.sqlite --thread-id <thread-id> --checkpoint-id <checkpoint-id> --issue --output-dir exports`, then `uv run lgmi audit-debug-bundle exports/<bundle>.json`. Please review the generated JSON locally, paste the Markdown summary, and attach only the redacted bundle; no raw production checkpoint stores.
```

PostgresSaver issue:

```text
Thanks for the report. Could you run `uv run --extra postgres lgmi doctor --postgres-conninfo "$DATABASE_URL" --postgres-schema public --issue` against a local/safe connection and paste the generated Markdown? It redacts credentials and reports store shape/counts without checkpoint state, thread ids, or message content.
```

LangSmith / Studio comparison:

```text
I do not see this as a LangSmith or LangGraph Studio replacement. The focus is narrower: local checkpoint forensics. When a persisted state value is wrong, I want to find which checkpoint and write made it visible, without uploading private state.
```

Toy demo concern:

```text
That is fair. v0.1 is intentionally narrow: one deterministic stale-memory demo, then fixture-driven diagnostics. The next step is collecting redacted/synthetic/schema-only examples from real LangGraph users and turning them into tests.
```

Privacy concern:

```text
Agree. Raw checkpoint stores can contain user messages, prompts, tool arguments, and secrets. The preferred feedback path is redacted debug bundles, synthetic fixtures, or schema-only snapshots.
```

Feature request response:

```text
This sounds like a real checkpoint pattern. Could you describe the backend, thread/checkpoint_ns shape, affected state channels, and what the wrong final behavior looked like? A synthetic fixture is enough; no raw production data needed.
```

## Tracking Table

| Channel | Status | URL | Follow-up |
| --- | --- | --- | --- |
| GitHub feedback issue | Live | https://github.com/fengjikui/langgraph-memory-inspector/issues/20 | Convert useful comments into diagnostic/fixture issues. |
| LangChain Forum | Not posted |  | Post first after social preview upload or with the repo GIF. |
| LangChain Slack | Not posted |  | Post after Forum thread exists. |
| X / LinkedIn | Not posted |  | Use social preview image and GIF. |
| Chinese community | Not posted |  | Rewrite by hand before posting. |
| Reddit | Not posted |  | Wait for initial external feedback. |
| Show HN | Not posted |  | Wait until at least one outside user tries the quickstart. |
