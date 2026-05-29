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

- `/api/threads/{thread_id}/checkpoints` 从数组响应升级为 `{ items, pagination, filters }`，支持 `limit`、`offset`、`from_end`、`diagnostic`、`changed_path`、`checkpoint_id_prefix`。
- SQLite 和 Postgres readers 增加 `count_checkpoints()`，无筛选时走数据库 limit/offset，避免生产大库首屏全量加载。
- UI 首次打开当前 thread/namespace 时请求最新一页；用户可以点击 `Load earlier checkpoints` 逐页加载更早历史，选中的 checkpoint 不会丢。
- Timeline 增加 `Diagnostics only`、checkpoint id prefix 和 state path filter，开发者可以从日志里的 checkpoint id 前缀、“有诊断”或“某个 state channel 变化”切入调试。

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

### Fixture intake policy and first synthetic fixture

用户价值改进：

- 新增 `docs/fixture_policy.md`，明确哪些真实用户材料可以公开接收：redacted debug bundle、synthetic fixture、schema-only PostgresSaver snapshot 或纯调试故事。
- 新增 `tests/fixtures/synthetic/reducer_append_duplicate_memory.json`，把 reducer append duplicate 这类真实调试模式收敛成无隐私、可回归的最小 fixture。
- 新增 fixture 测试，校验公开 fixture 的 metadata、安全边界、文件大小，以及 expected diagnostics 是否真的由 `run_diagnostics()` 产出。
- README、CONTRIBUTING、checkpoint bug pattern issue form、community launch playbook 和 release checklist 都链接到 fixture policy。

为什么重要：

- 真实用户反馈只有进入测试体系，才会持续提高工具质量。否则社区 issue 很容易停留在描述层，无法变成更可靠的 diagnostic。
- fixture policy 把“请给我真实 checkpoint 数据”改成“请给我安全、最小、可测试的问题形状”。这能降低用户分享门槛，也能保护项目不误收私密数据。

产品决策变化：

- 从现在开始，能进入仓库的用户材料必须是 synthetic、redacted 或 schema-only，并且每个被接受的 fixture 都应该对应一个 diagnostic 测试或 reader 兼容性测试。
- #14 的 reducer duplicate 诊断不再只是规则本身；它成为第一条 fixture-driven regression path，后续真实反馈也按同样方式进入产品。

已验证：

- fixture metadata 与 expected diagnostics 由单测覆盖。

### Fixture-driven diagnostic matrix

用户价值改进：

- 新增 `docs/diagnostic_matrix.md`，把 diagnostic id、fixture id、backend shape、source safety、state channels 和 validation command 放在同一张表里。
- 矩阵明确区分 deterministic demo、committed safe fixture 和 unit-only coverage，让维护者知道哪些诊断已经有产品级证据，哪些还需要真实用户模式补强。
- fixture 测试现在会解析矩阵，要求每个 JSON fixture 的 expected diagnostics 都在矩阵中出现，并且 backend、source safety、state channels 和验证命令保持一致。
- README 和 fixture policy 都链接到 diagnostic matrix。

为什么重要：

- 这个项目要靠真实调试模式持续变强，而不是靠零散规则堆叠。矩阵让用户反馈、fixture、diagnostic、测试命令之间的关系一眼可见。
- 对面试展示来说，它也能证明项目有“维护者视角”：我们不只是做了一个 demo，而是在建立一套把用户问题转成可回归能力的机制。

已验证：

- `tests/test_fixtures.py` 覆盖 matrix 与 fixture metadata 的一致性。

### v0.1.0 release candidate audit

用户价值改进：

- 新增 `docs/release_candidate_audit_2026-05-29.md`，把发布前检查从空 checklist 变成带证据的 gate review。
- 新增 `docs/release_notes_v0.1.0.md`，提前准备面向外部开发者的 release note 草稿，突出 stale-memory 调试路径、local-first、redacted export 和 fixture-driven 维护机制。
- `docs/release_checklist.md` 更新为当前 pass/fail 状态，唯一明确 public launch blocker 是仓库仍为 private，需要维护者显式批准后再公开。
- CI workflow 升级到 metadata 使用 `node24` 的 action 版本：`actions/checkout@v6.0.2`、`actions/setup-node@v6.4.0`、`astral-sh/setup-uv@v8.1.0`。

为什么重要：

- 发布候选不是“感觉差不多”，而是每个门都有证据。这样公开前能清楚知道哪里已可信，哪里还需要人工决策。
- Node deprecation annotation 虽然不影响功能，但公开项目前 CI 页面应该尽量干净。能安全升级就升级，减少第一批用户看到的噪音。

已验证：

- RC commit 需要通过完整本地验证和 GitHub CI 后才能关闭 #18。

### Diagnostic causal chain

用户价值改进：

- 新增 `GET /api/threads/{thread_id}/causal-chain`，给定 diagnostic、checkpoint 和 namespace 后，返回相关 state paths、write channels、checkpoint range、node/task 和 write evidence。
- 前端点击 diagnostic 后，Writes 面板会展示 compact Causal chain，连接“诊断 -> checkpoint 范围 -> 相关 write channel -> node/task”。
- stale-memory demo 现在可以从最终错误回答追到 `conflicting_residence_memory`，再追到 `state.memory_events` 的 Shanghai/Hangzhou 写入证据。

为什么重要：

- 单个 write highlight 只能回答“这个 checkpoint 有什么写入”，causal chain 开始回答“这个错误是怎么一路形成的”。这是从 JSON viewer 走向真正 checkpoint forensics 的关键一步。

已验证：

- API contract、真实 relocation demo causal chain、前端 build/e2e 需要在提交前通过。

### Single-server demo mode

用户价值改进：

- `create_app(..., ui_dir=...)` 现在可以把 `web/dist` 挂到同一个 FastAPI 服务下，`/` 返回 Inspector UI，`/api/*` 继续返回 checkpoint API。
- `lgmi demo`、`lgmi inspect` 和 `lgmi inspect-postgres` 会自动发现 `web/dist`，也支持显式传入 `--ui-dir`。
- `lgmi doctor` 会检查 built UI 是否存在，并在可用时给出单条下一步命令：`uv run lgmi demo --no-browser`。
- README、demo script 和 public launch packet 后续被 `lgmi demo --build-ui` 进一步简化为一条 demo 命令。

为什么重要：

- 外部用户第一次试用时，两个终端和 Vite proxy 是明显摩擦点。单服务模式让 demo 更像一个完整工具，而不是开发环境拼装。
- 这也降低社区推广后的支持成本：如果用户已经 build 过 UI，后续只要启动 `lgmi demo` 就能打开完整检查器。

已验证：

- `uv run lgmi doctor`
- `uv run lgmi demo --no-browser --port 8771` 后，浏览器打开 `http://127.0.0.1:8771/`，页面标题为 LangGraph Memory Inspector，能看到 `conflicting_residence_memory`，控制台无 error。
- `curl http://127.0.0.1:8771/`、`curl http://127.0.0.1:8771/api/summary` 和静态 JS 资源均返回 200。

### Pasteable doctor reports

用户价值改进：

- `lgmi doctor --json` 输出机器可读的环境和 demo 健康报告。
- `lgmi doctor --issue` 输出可直接粘贴到 GitHub issue 的 Markdown 片段。
- 报告只包含 Python、CLI、demo checkpoint 计数、Node/npm、web dependencies、built UI 和下一步命令，不包含 checkpoint state、message content、prompts、tokens 或 production database rows。
- Bug report issue template 增加 Doctor report 字段；public launch reply template 改成让外部用户贴 `uv run lgmi doctor --issue`。

为什么重要：

- 推广后最容易消耗维护者精力的是“跑不起来但信息不够”的问题。Pasteable report 把支持入口标准化，让维护者先看到同一份安全上下文。
- 结构化 JSON 也给未来自动 triage、CI smoke bot 或 issue parser 留了接口。

已验证：

- `uv run lgmi doctor --json`
- `uv run lgmi doctor --issue`
- `uv run pytest tests/test_cli.py -q`

### One-command UI build for demo

用户价值改进：

- `lgmi demo --build-ui` 会在需要时运行 `npm install`，再运行 `npm run build`，随后把 `web/dist` 和 checkpoint API 放在同一个本地服务里。
- README、demo script 和 public launch packet 的 quickstart 缩短为 `uv sync`、`uv run lgmi doctor`、`uv run lgmi demo --build-ui`。
- `lgmi doctor` 在 built UI 不存在时优先提示 `uv run lgmi demo --build-ui --no-browser`，把首次试用从“理解前后端两个子项目”变成“跑一条产品命令”。

为什么重要：

- 社区用户第一次试用时，少一个目录切换和少三条 npm 命令就是少一次放弃机会。这个改动把 demo 从开发者拼装流程进一步收敛成产品入口。
- `--build-ui` 是显式选项，不会让普通 `lgmi demo` 在用户不知情时安装或构建前端依赖。

已验证：

- `uv run pytest tests/test_cli.py -q`
- `uv run lgmi demo --help`

### SQLite DB doctor path

用户价值改进：

- `lgmi doctor --sqlite-db ./checkpoints.sqlite` 会只读检查用户自己的 SQLite checkpoint 文件，报告文件是否存在、checkpoint/write/thread 计数、diagnostic 计数和 namespace 列表。
- 报告不包含 checkpoint state、message content、prompts、tokens、raw database rows，也不会默认暴露 thread id。
- `lgmi inspect ./checkpoints.sqlite --build-ui` 让用户自己的 DB 也能一条命令启动完整 UI，不再只对 demo 有单服务体验。
- Bug report template 和 launch reply template 增加 SQLite DB doctor 路径。

为什么重要：

- Demo 能跑起来只是 adoption 的第一步。真正采用发生在用户把自己的 checkpoint store 接进来，并且能快速判断“是我的 DB 形状不对，还是 inspector 有 bug”。
- SQLite doctor 给维护者和用户一个共享的安全诊断边界，减少来回追问，也降低误贴生产状态的风险。

已验证：

- `uv run lgmi doctor --skip-demo --skip-web --sqlite-db examples/relocation_policy_agent/data/checkpoints.sqlite --json`
- `uv run pytest tests/test_cli.py -q`

### PostgresSaver doctor path

用户价值改进：

- `lgmi doctor --postgres-conninfo "$DATABASE_URL" --postgres-schema public` 会用现有 read-only Postgres reader 检查 PostgresSaver store shape。
- 报告包含 checkpoint/write/blob/thread 计数、namespace、migration version 和 adapter，不包含 checkpoint state、thread id、message content、prompts、tokens 或 raw rows。
- Postgres URI 和 libpq `password=...` 连接串在报告里会脱敏；下一步命令使用 `<postgres-conninfo>` 占位符，避免用户直接把密码贴到 issue。
- `lgmi inspect-postgres "$DATABASE_URL" --schema public --build-ui` 现在也支持自动构建并服务 UI。

为什么重要：

- 真实团队更可能把 LangGraph checkpoint 放在 PostgresSaver 里。Postgres doctor 让他们能先验证 store 是否是完整历史表、是否能被 reader 读取，再决定是否启动 UI 或提交反馈。
- 这把“支持 Postgres”从文档声明推进成可诊断的接入路径，也降低维护者远程排查连接/表结构问题的成本。

已验证：

- `uv run pytest tests/test_cli.py -q`
- `uv run lgmi doctor --skip-demo --skip-web --postgres-conninfo postgresql://user:secret@localhost:1/db --json`
- `uv run pytest tests/test_cli.py tests/test_postgres_reader.py -q`
- `uv run pytest -q`
- `cd web && npm run build`
- `cd web && npm run test:e2e`
- `uv build`
- `uv run lgmi prove-demo --reset-demo`
- `ruby -e 'require "yaml"; Dir[".github/ISSUE_TEMPLATE/*.yml"].each { |path| YAML.load_file(path); puts "OK #{path}" }'`

### Postgres confidence mini-pack

用户价值改进：

- 新增 `scripts/postgres_confidence.py`，用于在本地/安全 Postgres 实例中创建一个临时 `lgmi_confidence_*` schema，写入真实 LangGraph `PostgresSaver` demo checkpoints，并用 `PostgresCheckpointReader` + `lgmi doctor` 验证。
- 默认会清理生成 schema，避免长期堆积测试数据；传 `--keep-schema` 时才保留，并打印 `inspect-postgres` 命令和 cleanup SQL。
- README 现在给出已有 `DATABASE_URL` 和 Docker `postgres:16` 两种 confidence path。

为什么重要：

- 真实团队在连接私有 checkpoint store 前，需要先确认“这个工具确实能读 PostgresSaver 的完整历史表”。这个脚本把 CI 内部能力变成用户可复制的本地验证路径。
- 默认清理减少本地数据库脏数据和长期磁盘增长；`--keep-schema` 又保留了可交互演示路径。

已验证：

- `uv run python scripts/postgres_confidence.py --help`
- `env -u DATABASE_URL -u LGMI_POSTGRES_TEST_DSN uv run python scripts/postgres_confidence.py`
- `uv run pytest tests/test_postgres_confidence.py -q`

本机限制：

- 当前本机没有 Docker CLI，因此 Docker 端到端命令依赖 GitHub Actions 的真实 Postgres service 和有 Docker 的用户机器继续验证。

### Product proof CLI

用户价值改进：

- 新增 `lgmi prove-demo --reset-demo`，把原本藏在 `scripts/use_case_smoke.py`
  里的用例冒烟测试提升成正式 CLI 入口。
- 新增 `--json` 输出，方便 CI、issue triage 或外部用户把“工具是否真的证明了
  stale-memory 路径”贴成机器可读证据。
- `scripts/use_case_smoke.py` 仍保留为兼容 wrapper，但实现迁移到
  `src/lgmi/use_case_smoke.py`，让产品证明逻辑跟 CLI 和测试共用同一份代码。
- README、release notes、release checklist、diagnostic matrix、demo script 和
  launch draft 都改成推荐 `uv run lgmi prove-demo --reset-demo`。

为什么重要：

- 外部用户第一次看项目时，需要一个比“跑测试”更像产品承诺的命令。`prove-demo`
  直接回答：这个工具能不能从 checkpoint 证据证明上海到杭州的 stale-memory
  故障路径。
- 这也让面试演示更顺：先 doctor 证明环境，再 prove-demo 证明价值，最后打开 UI
  展示交互证据。

### Product proof in CI and bug reports

用户价值改进：

- GitHub Actions 的 stale-memory gate 改为运行
  `uv run lgmi prove-demo --reset-demo --json`，不再依赖旧的脚本入口。
- Bug report 模板新增 Demo proof report 字段，引导用户在 demo/diagnostic
  行为异常时粘贴安全 JSON proof。

为什么重要：

- CI 应该验证用户真正会复制的命令。这样 README、Forum 首帖、release
  checklist 和 CI 讲的是同一条产品路径。
- Doctor report 回答“环境是否能跑”，proof report 回答“这个 demo 是否真的证明了
  checkpoint 故障路径”。两者分开后，外部 issue 会更容易定位是安装问题、数据问题，
  还是诊断逻辑问题。

### Message history bloat fixture and evidence

用户价值改进：

- 新增 `synthetic_message_history_bloat_v1` 安全 fixture，专门保护
  `oversized_message_history` 诊断，不再只依赖 relocation demo 的顺带覆盖。
- `oversized_message_history` evidence 现在包含 `state_path`、消息数量阈值、
  role 分布、内容字符数、首尾消息摘要、`messages` 写入摘要和建议动作。
- Debug bundle 复现备注会解释 oversized message history 应优先考虑 trimming、
  summarization 或 task-scoped checkpointing。

为什么重要：

- message/history bloat 是真实 Agent 调试里很常见的隐性成本问题。开发者不只想知道
  “消息多”，还需要知道应该去查哪个 state channel、哪个写入节点，以及下一步怎么收敛。
- 独立 fixture 让这个诊断变成可维护的 bug pattern，而不是 demo 的附属现象。

已验证：

- `uv run pytest tests/test_analysis.py tests/test_fixtures.py tests/test_export_bundle.py -q`
- `git diff --check`

### Wrong-resume lineage fixture

用户价值改进：

- 新增 `synthetic_unexpected_parent_checkpoint_v1` 安全 fixture，保护
  `unexpected_parent_checkpoint` 诊断。
- 该 fixture 模拟同一 thread / namespace 下从 `resume-cp-1` 跳到
  `resume-cp-4`，而 timeline 上一个 checkpoint 是 `resume-cp-2` 的 wrong
  resume point 场景。
- `unexpected_parent_checkpoint` evidence 现在会标注当前 checkpoint namespace、
  previous checkpoint namespace、是否同 namespace，以及建议先确认 resume
  checkpoint、checkpoint namespace 和 branch。

为什么重要：

- LangGraph 应用出现“为什么从旧状态继续跑”的问题时，开发者需要先排除 checkpoint
  lineage / resume point 错误，而不是直接去怀疑 reducer 或业务状态。
- 这个 fixture 把 wrong resume point 从 unit-only 保护升级成诊断矩阵中的可复现
  bug pattern。

已验证：

- `uv run pytest tests/test_analysis.py tests/test_fixtures.py -q`
- `git diff --check`

### Repeated retrieved context fixture and evidence

用户价值改进：

- 新增 `synthetic_repeated_retrieved_context_v1` 安全 fixture，保护
  `repeated_retrieved_context` 诊断。
- `repeated_retrieved_context` evidence 现在包含 `state_path`、retrieved doc
  总数、重复组数量、重复文档数量、重复占比、重复 source/content 预览、retrieval
  writes 摘要和 dedup 建议。
- Debug bundle 复现备注会解释 repeated retrieved context 应优先检查 retrieval
  节点并在 context packing 前按 source/content 去重。

为什么重要：

- RAG/Agent 调试时，重复检索结果会浪费上下文窗口，还会把真正有帮助的证据挤出去。
  用户需要知道是哪个 retrieval write 把重复 docs 放进了 `state.retrieved_docs`。
- 这个 fixture 让诊断矩阵不再有 unit-only 诊断；每个当前 diagnostic 都至少有 demo
  或安全 fixture 支撑。

已验证：

- `uv run pytest tests/test_analysis.py tests/test_fixtures.py tests/test_export_bundle.py -q`
- `git diff --check`

### Launch docs reflect full diagnostic coverage

用户价值改进：

- README Current Scope 现在显式列出 repeated retrieved context、message history
  growth 和 checkpoint size spike，不再低估当前诊断能力。
- Release checklist 和 release candidate audit 记录：当前所有 diagnostic 都由
  deterministic demo 或 committed safe fixture 支撑，诊断矩阵已经没有 unit-only 行。
- Diagnostic matrix 的说明改成未来维护规则：如果后续新增 unit-only 诊断，必须继续补
  fixture、redacted bundle、schema-only snapshot 或 deterministic demo proof。

为什么重要：

- 对外发布材料必须和实际能力一致。否则用户会低估工具，也会让维护者误以为还有已解决的
  fixture 缺口。
- 这轮把“当前诊断覆盖已闭环”的事实写进发布 gate，方便下一步聚焦 social preview、
  Forum 首帖和真实用户反馈。

已验证：

- `uv run pytest tests/test_fixtures.py -q`
- `uv run pytest -q`
- `git diff --check`

### Release and feedback copy reflect fixture coverage

用户价值改进：

- Release notes、public launch packet、LangChain Forum draft 和 pinned GitHub
  issue draft 都补充了 repeated retrieved context、message/history bloat、
  namespace confusion、checkpoint size spike 和 wrong-resume lineage jump。
- 对外反馈 ask 从“再补基础诊断”推进到“请给生产形态/真实模式”，并明确当前所有
  diagnostic 都已经由 deterministic demo 或 committed safe fixture 支撑。

为什么重要：

- 公开首发时，用户看到的反馈入口应该反映当前真实成熟度：不是一个只有 demo 的项目，
  而是已经有诊断矩阵和 fixture 回归的调试工具。
- #20 作为反馈 home base，需要引导用户提交最有价值的下一类证据，而不是重复已经覆盖的
  合成 bug pattern。

已验证：

- `uv run pytest -q`
- `git diff --check`

### Social preview upload gate documented

用户价值改进：

- 新增 `docs/social_preview_upload_guide.md`，把 GitHub social preview 的手动上传
  步骤、上传后验证和 #23 关闭命令写清楚。
- 已验证 `docs/assets/github-social-preview.png` 为 PNG、1280 x 640、375 KB，
  符合 GitHub 当前推荐的 1280 x 640 且小于 1 MB 要求。
- Release checklist、community launch playbook、public launch packet、Forum
  pre-post checklist 和 release candidate audit 都链接到这份 guide。

为什么重要：

- 这是公开首发前最后一个需要账号/Settings 权限的 gate。Codex 不应在没有明确确认时
  代替用户改 GitHub 设置，但可以把手动步骤压缩到几分钟内完成。
- 社交预览不是装饰，它会影响 Forum、Slack、X、LinkedIn、V2EX 或 Show HN 分享时的
  第一眼信任感。

已验证：

- `file docs/assets/github-social-preview.png`
- `ls -lh docs/assets/github-social-preview.png`
- GitHub 官方 social preview 文档

### Social preview asset regression check

用户价值改进：

- 新增 `scripts/validate_social_preview.py`，使用标准库解析 PNG header，校验 social
  preview 资产是否为 PNG、1280 x 640、低于 1 MB，且不是带 alpha 的透明图。
- 新增 `tests/test_social_preview.py`，把这个发布资产要求纳入 pytest 回归。
- `docs/social_preview_upload_guide.md` 和 `docs/release_checklist.md` 记录了上传前
  可运行的验证命令。

为什么重要：

- social preview 是公开传播入口的一部分。如果以后替换图片，CI 应该立刻发现尺寸、大小
  或透明背景不符合 GitHub 推荐，而不是等到发帖后才看到预览卡片异常。

已验证：

- `uv run python scripts/validate_social_preview.py`
- `uv run pytest tests/test_social_preview.py -q`

### Launch copy guardrail

用户价值改进：

- 新增 `scripts/validate_launch_copy.py`，校验 Forum draft、public launch packet 和
  community launch playbook 是否保留 repo 链接、#20 反馈入口、fixture policy、redacted
  evidence 表述、raw production 警示和非求 star 的主 CTA。
- 新增 `tests/test_launch_copy.py`，把推广文案的用户信任边界纳入 pytest。
- Release checklist、public launch packet 和 community launch playbook 记录了发布前运行
  `uv run python scripts/validate_launch_copy.py`。

为什么重要：

- 推广不是硬发链接。公开文案如果丢掉隐私边界、反馈入口或 fixture policy，很容易让项目
  看起来像噪音，甚至诱导用户贴出不该公开的 checkpoint 数据。
- 这个 guardrail 把“站在真实用户角度做推广”变成可测试约束。

已验证：

- `uv run python scripts/validate_launch_copy.py`
- `uv run pytest tests/test_launch_copy.py -q`

### Release smoke command

用户价值改进：

- 新增 `scripts/release_smoke.py`，把 release checklist 中的默认发布前检查收成一条命令：
  `uv run pytest -q`、social preview asset 校验、launch copy guardrail 和
  `lgmi prove-demo --reset-demo`。
- `--include-web` 会额外运行 `web/` 下的 `npm run build` 和 `npm run test:e2e`。
- 新增 `tests/test_release_smoke.py`，防止 release smoke gates 和 release checklist 脱节。
- `docs/release_checklist.md` 现在先给一键 smoke，再保留展开命令。

为什么重要：

- 发布前 gate 越分散，越容易漏跑。把它收成一条命令，可以让后续每次准备 Forum、Reddit、
  HN 或中文社区发布前都先跑同一套证据。
- Web gate 保持可选，是为了让轻量文档/文案检查不用每次都触发浏览器安装，但 broad launch
  前仍然有完整路径。

已验证：

- `uv run python scripts/release_smoke.py`
- `uv run pytest tests/test_release_smoke.py -q`

### Remote launch status command

用户价值改进：

- 新增 `scripts/launch_status.py`，把本地 git 状态、repo visibility、最新 main CI、
  v0.1.0 release、#20、#23 和 repository OpenGraph image 状态汇总成一条命令。
- `#23` open 和默认 GitHub OpenGraph URL 会被标成 `MANUAL`，让维护者清楚知道当前不是
  代码失败，而是等待 Settings 上传 social preview。
- 新增 `tests/test_launch_status.py`，用 fake `gh`/`git` 输出保护状态分类逻辑。
- `docs/release_checklist.md` 和 `docs/social_preview_upload_guide.md` 都记录了
  `uv run python scripts/launch_status.py`。

为什么重要：

- 技术 gate、发布 gate 和社区 gate 现在分布在 CI、issue、release 和 repo settings。
  一个远端状态命令可以减少维护者来回查 GitHub 的认知成本。
- social preview 上传后，也可以用这条命令确认 #23 是否应该关闭、Forum 首帖是否可以发。

已验证：

- `uv run python scripts/launch_status.py`
- `uv run pytest tests/test_launch_status.py -q`

### CI environment boundary for doctor tests

用户价值改进：

- 修复 `tests/test_cli.py::test_doctor_prefers_build_ui_when_dist_is_missing`
  对 CI runner Node/npm 环境的隐式依赖。
- 这个测试现在只验证它真正关心的行为：当 `web/dist` 不存在时，`lgmi doctor --json`
  应该推荐 `uv run lgmi demo --build-ui --no-browser`，而不是被 Python CI job
  是否安装 Node/npm 影响。

为什么重要：

- `lgmi doctor` 是新用户遇到启动问题时最先运行的诊断入口，相关测试必须稳定。
- CI 失败暴露了一个维护经验：测试如果想验证某条用户指引，就应该显式固定无关环境，
  避免把 runner 工具链当成产品行为的一部分。

已验证：

- `uv run pytest tests/test_cli.py::test_doctor_prefers_build_ui_when_dist_is_missing -q`
- `uv run pytest -q`
- GitHub Actions main CI run `26645996221`

### Issue-safe debug bundle handoff

用户价值改进：

- `lgmi export-debug-bundle` 新增 `--issue`，用于真实用户在 GitHub issue 中分享 checkpoint
  bug 证据。
- `--issue` 默认使用 redacted export，输出可粘贴的 Markdown 摘要，只展示 bundle 文件名、
  schema version、thread/checkpoint/ns、文件大小、redaction 统计和 diagnostic ids。
- `--issue` 的 redacted path 列表只展示少量 sample，完整列表保留在生成的 JSON bundle，
  避免 issue 摘要变成几十行噪声。
- 如果用户显式传 `--issue --redaction-mode raw`，CLI 会返回错误，避免把 public issue
  路径变成 raw checkpoint 泄漏通道。
- 修正 phone-like string redaction 的边界，避免 UUID checkpoint id 和 ISO timestamp 被误遮蔽；
  redacted bundle 会继续保留结构字段，同时仍遮蔽 message/evidence 等敏感内容。
- README、fixture policy、checkpoint bug pattern issue template 和 public launch packet
  都增加了这条安全分享路径。

为什么重要：

- 推广后的第一批真实反馈很可能不是 PR，而是“我这里也有类似 bug”。如果他们不知道怎么安全
  分享证据，反馈会变成模糊描述，或者更糟，贴出 raw production checkpoint。
- 这个命令把“真实用户反馈 -> redacted bundle -> maintainer 复现 -> fixture/diagnostic”
  这条路径缩短成一个明确动作。

已验证：

- `uv run pytest tests/test_export_bundle.py -q`
- `uv run lgmi export-debug-bundle examples/relocation_policy_agent/data/checkpoints.sqlite --thread-id relocation-demo-user-001 --checkpoint-id 1f15b739-6741-66e0-8007-516937504e51 --issue --output-dir /tmp/lgmi-issue-export`

### Debug bundle audit command

用户价值改进：

- 新增 `lgmi audit-debug-bundle <bundle.json>`，让用户在把 redacted bundle 贴到 public issue
  前先做一次本地自动检查。
- audit 会检查 bundle JSON 是否可读、schema version、关键结构字段、privacy metadata、
  redaction mode 是否为 `redacted`，以及是否残留明显 token/email/phone-like 字符串。
- `export-debug-bundle` 现在会把缺失 checkpoint id 等常见错误转成清晰 stderr 和 exit 2，
  避免用户复制错 id 时看到 traceback。
- `launch_status.py` 改成每个 probe 独立失败，GitHub CLI/API 短暂抖动会显示对应 gate
  `FAIL`，不会中断整份 launch report。
- README、fixture policy、checkpoint bug pattern template、public launch packet 和 release
  checklist 都记录了 audit path。

为什么重要：

- 真实用户愿意反馈时，最大的阻力不是“不会描述”，而是不确定什么可以安全公开。audit 命令把
  这一步变成一个可复制的本地动作。
- launch status 是维护者发布前的仪表盘，不能因为一个远端请求抖动就失去全部可见性。

已验证：

- `uv run pytest tests/test_export_bundle.py tests/test_launch_status.py -q`
- `uv run lgmi audit-debug-bundle /tmp/lgmi-audit-export/<bundle>.json`
