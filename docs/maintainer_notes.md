# 维护笔记

## 2026-05-29

### Diagnostic 卡片变成调试导航

用户价值改进：

- 之前：diagnostic 只是信息卡片，用户仍然需要自己在 timeline 里找证据。
- 之后：diagnostic 会展示 checkpoint、state path、write channel。点击卡片会跳到相关 checkpoint。

为什么重要：

- 真实开发者不想逐条读 checkpoint。他们想从“这里好像错了”直接跳到“给我看证明它错的状态快照”。
- 这个变化让产品从 JSON viewer 更接近真正的调试工具。

已验证：

- `uv run pytest -q`
- `cd web && npm run build`
- 使用本地 FastAPI 数据渲染 UI 截图，确认 diagnostics panel 出现在首屏。

### Writes Tab 高亮关联写入

用户价值改进：

- 之前：点击 diagnostic 只能跳到 checkpoint，但用户还需要自己在 Writes tab 里找相关写入。
- 之后：如果 diagnostic 带有 `writeChannel`，点击后会自动打开 Writes tab，并高亮对应写入行。
- 对 stale memory demo 来说，`conflicting_residence_memory` 会把用户带到 `state.memory_events` 的写入证据。

为什么重要：

- 真实用户排查的是因果链，不是单个状态字段。高亮 write channel 可以把“状态错了”进一步变成“哪个节点/通道写出了导致问题的状态”。

已验证：

- `uv run pytest -q`
- `cd web && npm run build`
- `cd web && npm run test:e2e`
- `uv run python scripts/use_case_smoke.py`

### 真实录屏与 incoming writes 修正

用户价值改进：

- README 已经使用真实 UI GIF，而不是占位图。
- 录制过程中发现 LangGraph SQLite `writes.checkpoint_id` 更接近“从父 checkpoint 生成当前快照的写入边”。
- `SQLiteCheckpointReader.list_writes()` 现在优先返回生成当前 checkpoint snapshot 的 incoming writes。

为什么重要：

- 用户在某个 checkpoint detail 里点击 Writes，预期看到的是“这个快照为什么变成现在这样”，而不是“这个 checkpoint 之后又写了什么”。
- 这个修正让 live demo 中 `conflicting_residence_memory` 能真正高亮 `state.memory_events`，展示杭州记忆写入的证据。

已验证：

- `uv run pytest -q`
- `cd web && npm run build`
- `cd web && npm run test:e2e`
- `uv run python scripts/use_case_smoke.py`
- 重新录制 `docs/assets/stale-memory-debugging-demo.gif`

### Postgres adapter 前置调研

用户价值改进：

- 当前代码新增 `CheckpointReader` 协议，FastAPI 不再硬绑定 SQLite reader。
- 新增 `docs/postgres_adapter_plan.md`，记录官方 PostgresSaver schema、blob hydration 方案、read-only 约束和后续实现步骤。

为什么重要：

- 真实生产用户更可能使用 Postgres checkpointer。先把 adapter 边界和 schema 风险讲清楚，可以避免为了“支持 Postgres”而引入会误读 checkpoint 或误操作生产库的实现。

已验证：

- 使用 LangGraph 官方持久化文档和 PostgresSaver 源码核对 schema。
- 新增 API adapter 测试，保证 backend route 可以接入非 SQLite reader。

### Postgres adapter 初版实现

用户价值改进：

- 新增 `PostgresCheckpointReader`，支持 full `PostgresSaver` schema 的 read-only inspection。
- 新增 `lgmi inspect-postgres "$DATABASE_URL" --schema public` CLI。
- 支持从 `checkpoint_blobs` 还原非 primitive channel，例如 `memory_events`。
- 支持从 `checkpoint_writes` 解码 node/task writes，并沿用 incoming-writes 语义。

为什么重要：

- 这让项目从 SQLite demo 往真实生产 LangGraph 项目前进了一步。用户可以在不迁移数据、不上传 traces、不调用 LangGraph 写接口的前提下读取 Postgres checkpoint store。

已验证：

- 本机没有 Docker/Postgres server，因此真实 Postgres 集成测试通过 `LGMI_POSTGRES_TEST_DSN` 作为显式可选测试。
- 默认测试已覆盖 blob hydration、write decoding、schema 安全校验。

### GitHub Actions CI

用户价值改进：

- 新增 CI workflow，覆盖 Python 默认测试、stale-memory smoke test、前端 build/e2e，以及真实 Postgres service 集成测试。
- README 增加 CI badge，让第一次访问 GitHub 的开发者能看到项目不是只在本机“口头可跑”。

为什么重要：

- Postgres adapter 的可信度必须来自真实 PostgresSaver fixture。CI 里的 Postgres service 可以补上本机没有 Docker/Postgres 的验证缺口，也让后续贡献者改动 adapter 时更放心。

### Debug bundle 显式导出

用户价值改进：

- 新增 `lgmi export-debug-bundle`，开发者可以把某个 checkpoint 的证据导出成 JSON。
- 新增 `POST /api/exports/debug-bundle`，为后续 UI 上的“导出证据包”按钮预留入口。
- bundle 包含数据库摘要、thread/checkpoint 元数据、timeline context、selected checkpoint、incoming writes、diagnostics 和复现备注。

为什么重要：

- 真实调试不是止步于“我在本机看到了问题”。开发者通常还要把证据发给同事、写进 PR、挂到 issue，或用于 incident 复盘。
- 证据包把本地 checkpoint 排查结果变成可分享 artifact，同时保持 local-first，不需要上传 traces。
- 导出必须显式触发，默认写到 `exports/`，并在 README 说明可安全删除，避免长期维护时磁盘文件悄悄增长。

已验证：

- `uv run pytest -q`

### Checkpoint Detail 导出按钮

用户价值改进：

- checkpoint detail 顶部新增 `Export` 按钮，直接调用 debug bundle API。
- 导出成功后，UI 显示生成路径、文件大小和 diagnostic ids。
- 真实 demo 时，用户从 diagnostic 跳到 writes 后，可以立刻把同一条证据链导出给同事或 PR。

为什么重要：

- CLI 是 power-user 路径，但面试和首次体验里，用户更容易相信一个看得见、点得动的调试动作。
- 这个按钮把“发现问题”到“分享证据”的动作缩短成一步，也让 debug bundle 不再只是后端能力。

已验证：

- `cd web && npm run build`
- `cd web && npm run test:e2e`
- Browser 渲染检查：diagnostic -> Writes 高亮 -> Export -> 显示 bundle path、size、diagnostic id。

### Release candidate 文档底座

用户价值改进：

- 新增 MIT `LICENSE`，让外部开发者知道项目能否被使用和分发。
- 新增 `CONTRIBUTING.md`，把本地启动、测试、issue workflow、存储卫生和 PR 形状写清楚。
- 新增 `docs/release_checklist.md`，把公开发布前需要证明的 CI、demo GIF、SQLite quickstart、Postgres integration 和 launch assets 固定下来。
- README 顶部链接 license/contributing/release checklist，并新增 Known Limitations。

为什么重要：

- 一个能被 star 和采用的开发者工具，不能只靠 demo 动效。陌生开发者会先判断许可、贡献门槛和限制是否诚实。
- Known Limitations 主动说明 large production stores、namespace handling、Postgres schema 和 debug bundle 隐私边界，能减少误用，也让项目显得更可信。

已验证：

- `uv run pytest -q`
- `uv build`

### Namespace selector 初版

用户价值改进：

- SQLite 和 Postgres readers 支持按 `checkpoint_ns` 过滤 timeline、checkpoint、writes。
- `/api/threads` 现在暴露每个 thread 的 `checkpoint_namespaces`，相关 API 接受 `checkpoint_ns` query 参数。
- 前端 Thread sidebar 显示 active namespace；当一个 thread 有多个 namespace 时，可以在不切换 thread 的情况下切换 namespace。
- Debug bundle export 也会携带 namespace，避免分享证据时丢失 checkpoint lineage。

为什么重要：

- 生产 LangGraph store 可能在同一个 `thread_id` 下保存多个 checkpoint namespace。如果 UI 把这些混在一起，开发者可能在错误 lineage 上排查。
- namespace selector 让“我正在看哪条 checkpoint 线”变成显式选择，而不是隐含假设。

已验证：

- `uv run pytest -q`
- `cd web && npm run build`
- `cd web && npm run test:e2e`

### Community launch playbook

用户价值改进：

- 新增 `docs/community_launch_playbook.md`，把 GitHub、LangChain Forum/Slack、HN、Reddit、X 和中文社区的发布方式拆成不同用户语境。
- 发布目标从“求 star”改为“请真实 LangGraph 用户验证 checkpoint 调试工作流，并提供 bug pattern”。
- 新增 pinned issue、英文短帖、Show HN、LangChain 社区、Reddit、中文长文、中文短帖和 OpenClaw 咨询提示词。
- `docs/demo_script.md` 补齐现场演示闭环：点击 `conflicting_residence_memory` -> Writes 高亮 `state.memory_events` -> Export debug bundle。

为什么重要：

- 一个真正会被采用的开发者工具，需要让用户先看到自己的问题，而不是先看到功能列表。
- 社区发布如果不尊重渠道规则，很容易变成噪音。playbook 明确要求每个渠道都用不同问题 framing、不要拉票、不要私信轰炸、优先收集真实痛点。

已验证：

- 文档一致性检查和完整测试在本次提交前执行。

### GitHub issue templates

用户价值改进：

- 新增 bug report、checkpoint bug pattern、feature/diagnostic request 三类 GitHub issue forms。
- 模板会引导用户填写 checkpoint backend、thread/checkpoint namespace、state path、write channel、debug bundle 和隐私确认。
- `docs/release_checklist.md` 新增 issue templates 检查项，避免公开仓库后反馈入口失控。

为什么重要：

- 早期用户最有价值的不是一句“很好用”，而是真实状态调试场景。issue templates 可以把零散反馈变成可复现、可归类、可转化为 diagnostic 的输入。
- checkpoint bug pattern 单独成表单，是为了把项目的社区增长和产品学习绑定在一起：每个好反馈都应该能变成一个更聪明的诊断规则或更清晰的调试路径。

已验证：

- YAML issue forms 结构检查和文档一致性检查在提交前执行。

### Redacted debug bundle export

用户价值改进：

- debug bundle 支持 `raw` / `redacted` 两种导出模式。
- CLI 新增 `--redact`、`--redaction-mode`、`--redact-path`、`--keep-path`。
- API request 支持 `redaction_mode`、`redact_paths`、`keep_paths`，response 返回 redaction mode、redacted paths 和 redaction count。
- UI 默认开启 `Redact private fields`，导出按钮显示 `Export redacted`，导出结果会标明 redaction 状态。
- 默认 redaction 会遮住 message `content`、`evidence`、prompt/text/input/output、secret/token/password 类字段，以及字符串里的 email、phone-like string 和常见 token。

为什么重要：

- debug bundle 的价值在于分享证据，但真实 checkpoint state 可能包含用户消息和隐私字段。redacted export 让“把问题发给同事或 issue”更接近真实生产流程。
- 结构性字段仍然保留，例如 checkpoint id、state path、write channel、diagnostic id。这样 bundle 既能保护隐私，又不会失去调试价值。

已验证：

- redacted export 不修改原 SQLite checkpoint DB。
- CLI、API、UI mock path 都能请求 redacted export。
- 完整测试和 CI 在提交前执行。

### Timeline pagination and filters

用户价值改进：

- `/api/threads/{thread_id}/checkpoints` 从数组响应升级为 `{ items, pagination, filters }`，支持 `limit`、`offset`、`from_end`、`diagnostic`、`changed_path`。
- SQLite 和 Postgres readers 增加 `count_checkpoints()`，无筛选时走数据库 limit/offset，避免生产大库首屏全量加载。
- UI 首次打开当前 thread/namespace 时请求最新一页；用户可以点击 `Load earlier checkpoints` 逐页加载更早历史，选中的 checkpoint 不会丢。
- Timeline 增加 `Diagnostics only` 和 state path filter，开发者可以从“有诊断”或“某个 state channel 变化”切入调试。

为什么重要：

- 真实 LangGraph checkpoint store 可能远大于 demo。首屏如果一次性读完所有 checkpoint，会让用户在真正需要工具的时候先等一个不透明加载。
- 最新页优先符合调试直觉：开发者通常先看到最终错误回答，再向前追溯状态在哪里写坏。

已验证：

- API 分页边界、`from_end` 和筛选测试通过。
- SQLite reader 分页和筛选测试通过。
- 前端 build/e2e 和本地浏览器截图检查在提交前执行。

### Reducer and resume diagnostics

用户价值改进：

- 新增 `reducer_append_duplicate_state`，检测 `messages` / `memory_events` 这类 reducer-backed channel 中重复的语义条目。
- 新增 `unexpected_parent_checkpoint`，检测当前 ordered timeline 中某个 checkpoint 的 parent 不等于相邻前一个 checkpoint，提示可能存在 resume/branch lineage 跳转。
- debug bundle reproduction notes 会解释这两个新 diagnostic 的下一步排查方向。
- 前端 diagnostic code mapping 增加对应 state path、write channel 和 node 文案，保证 UI 卡片不会退化成裸 code。

为什么重要：

- 很多 LangGraph bug 并不是“值错了”，而是 reducer 把旧值又 append 了一遍，或者用户以为自己从最新状态 resume，实际 lineage 跳到了另一个 parent。
- `unexpected_parent_checkpoint` 明确写入 false-positive 边界：LangGraph branch/namespace 可能故意造成非线性 parent link，所以它是排查信号，不是直接判定数据损坏。

已验证：

- 单测覆盖 reducer duplicate 和 parent jump 两类规则。
- 文档记录 diagnostic id、误报边界和 UI 展示字段。
