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
