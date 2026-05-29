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

## 面向用户的解释

对开发者来说，这意味着工具已经能回答核心调试问题：

> 用户已经搬到杭州，但最终回答仍然使用上海，是因为 `retrieve_policy`
> 选择了最早的居住地记忆。开发者在阅读源码之前，就能先从 checkpoint
> 状态里看到第一条证据。

## 剩余展示缺口

下一步最值得增强的是更明确的 node attribution 视图：

- 展示 `extract_profile -> memory_events`，说明杭州是在哪里 append 进去的。
- 展示 `retrieve_policy -> selected_city`，说明 stale 上海选择是在哪里发生的。
- 允许用户从 diagnostic 直接跳转到对应 checkpoint 和 write channel。
