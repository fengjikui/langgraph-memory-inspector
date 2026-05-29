# 用例测试报告

## 场景

搬家政策助手 demo 模拟了一个真实的 LangGraph 记忆故障：

1. 用户先说自己住在上海。
2. 用户随后说自己已经搬到杭州。
3. 用户询问应该优先查看哪些本地福利。
4. 图状态已经记住了杭州，但检索节点仍然选择上海。

这是 LangGraph Memory Inspector 的第一个真实产品用例：帮助开发者通过
checkpoint 状态定位 stale memory，而不是靠猜测排查。

## 运行命令

```bash
uv run python scripts/use_case_smoke.py --reset-demo
```

## 预期证据

- 本地生成 checkpoint 数据库。
- 最终状态里的最新居住地记忆是 `Hangzhou`。
- 最终状态里的 `selected_city` 仍然是 `Shanghai`。
- `retrieved_docs` 仍然基于上海内容。
- diagnostics 包含 `conflicting_residence_memory`。
- diagnostics 包含 `stale_selected_city`。
- 测试能定位杭州第一次写入 memory 的 checkpoint。
- 测试能定位 selected city 第一次变成 stale 的 checkpoint。

## 当前观察结果

当前实现已经通过 smoke test：

```text
PASS 检查器证据链已经证明 stale memory 故障路径。
```

默认确定性 demo 会生成 18 条 checkpoint rows 和 41 条 write rows。

本次 smoke test 观察到：

- 最新居住地记忆：`Hangzhou`
- 最终 `selected_city`：`Shanghai`
- 检索文档城市：`Shanghai`
- 第一次杭州记忆写入：已在 `memory_events` 中检测到
- 第一次冲突记忆 checkpoint：已检测到
- 第一次 stale selected-city checkpoint：已检测到
- diagnostics：`conflicting_residence_memory`、`stale_selected_city`、
  `oversized_message_history`、`checkpoint_size_spike`
- 诊断引擎还覆盖 `reducer_append_duplicate_state`、
  `checkpoint_namespace_confusion` 和 `unexpected_parent_checkpoint`，用于后续
  真实 reducer/resume/namespace bug pattern。

## 面向用户的解释

对开发者来说，这意味着工具已经能回答核心调试问题：

> 用户已经搬到杭州，但最终回答仍然使用上海，是因为 `retrieve_policy`
> 选择了最早的居住地记忆。开发者在阅读源码之前，就能先从 checkpoint
> 状态里看到第一条证据。

## 最新产品打磨

当前 UI 已经把 diagnostic 从静态提示改成可点击证据路径：

- 卡片展示对应 checkpoint。
- 卡片展示相关 state path，例如 `selected_city` 或
  `memory_events[type=residence_city]`。
- 卡片展示相关 write channel，例如 `memory_events` 或 `selected_city`。
- 点击 diagnostic 会跳转到对应 checkpoint，缩短从问题到证据的路径。
- 如果 diagnostic 带有 write channel，点击后会自动打开 Writes tab。
- Writes tab 会高亮匹配的写入行，例如 `state.memory_events`。
- 当前 reader 返回的是生成该 checkpoint snapshot 的 incoming writes，因此 live
  demo 可以直接看到 `extract_profile -> state.memory_events` 的写入证据。

新增的浏览器 e2e 覆盖了这个关键交互：

```bash
cd web && npm run test:e2e
```

测试会打开 UI，点击 `conflicting_residence_memory`，并确认 Writes tab 中的
`state.memory_events` 写入被高亮。

## 可分享调试证据包

最新实现新增显式 debug bundle 导出。用户可以在 checkpoint detail 里保持
`Redact private fields` 开启并点击 `Export redacted`，也可以使用 CLI：

```bash
uv run lgmi export-debug-bundle examples/relocation_policy_agent/data/checkpoints.sqlite \
  --thread-id relocation-demo-user-001 \
  --checkpoint-id <checkpoint-id> \
  --redact \
  --output-dir exports
```

这解决了真实用户排查后的下一步问题：不仅要在本机看懂 bug，还要把证据发给
同事、PR、issue 或 incident 复盘。bundle 是 JSON 文件，包含数据库摘要、线程
和 checkpoint 元数据、上下文 timeline、selected checkpoint、incoming writes、
diagnostics 和复现备注。

针对 stale memory demo，测试已经验证 bundle 中同时包含：

- `conflicting_residence_memory`
- `state.memory_events` 里的杭州记忆证据
- 对应 checkpoint 的 `memory_events` 写入

导出动作不会自动发生，必须由 UI、CLI 或 API 显式触发。生成文件位于
`exports/`，已被 git ignore，可以在分享或归档后直接删除。redacted bundle
会保留 checkpoint id、state path、diagnostic、write channel 等调试结构，同时
遮住 message content、evidence、token、email、phone-like string 等容易泄露的值。

## 本轮展示增强

`stale_selected_city` 现在可以展示更完整的 node-level write attribution：

- 把多个 checkpoint 上的相关 writes 串成一条因果链，而不是只看当前 checkpoint。
- 展示 `extract_profile -> memory_events`，说明杭州是在哪里 append 进去的。
- 展示 `retrieve_policy -> selected_city`，说明 stale 上海选择是在哪里发生的。
- 展示 `answer -> messages`，说明最终回答如何继续使用 stale 上海上下文。
- 为 diagnostic 给出“下一步该看哪个节点源码 / state path”的建议。

这让演示路径从“看见某个 write”升级成“看见一条可解释的节点路径”：
`extract_profile -> retrieve_policy -> answer`。
