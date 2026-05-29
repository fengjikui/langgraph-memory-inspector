# 维护与推广策略

## 项目原则

LangGraph Memory Inspector 的长期原则是：

> 站在真实开发者用户的角度设计产品，不做只给面试官看的炫技 demo。

每一次迭代都应该回答三个问题：

1. 真实开发者遇到什么痛点？
2. 这个改动是否缩短了他的调试路径？
3. 这个能力是否能被截图、GIF、测试或 demo 明确证明？

## 产品定位

一句话：

> Local-first DevTools for debugging LangGraph checkpoints and agent memory.

中文解释：

> 一个本地优先的 LangGraph checkpoint / memory 调试工具，帮助开发者从
> thread timeline、state diff、node writes 和 diagnostics 中定位 Agent
> 为什么跑偏。

核心价值不是“展示 JSON”，而是帮助开发者回答：

- 哪个 checkpoint 第一次出现坏状态？
- 哪个 state channel 发生了变化？
- 哪个 node write 可能导致了最终错误？
- memory 是 stale、conflicting，还是过度膨胀？
- 这个问题应该去看哪段代码？

## 近期产品路线

### P0：把当前 MVP 打磨成可信 demo

- Diagnostic 点击后跳转到对应 checkpoint。
- Writes tab 改成 node attribution 视图。
- Diff viewer 支持选择任意两个 checkpoint，而不是只看当前与前一个。
- README 首屏加入截图和 3 步 quickstart。
- 增加 `docs/screenshots/` 或远端 assets 的展示图，但不要提交临时大文件。

### P1：变成开发者真正可试用的工具

- 支持用户传入任意 SQLite checkpoint DB。
- 支持 checkpoint namespace 选择。
- 支持按 thread 搜索、按 diagnostic 过滤。
- 支持导出 debug bundle，包含 timeline、diff、diagnostics、复现说明。
- 增加更真实的 example apps：RAG stale context、tool call failure、human-in-the-loop resume。

### P2：GitHub 发布准备

- 加 LICENSE。
- 加 issue templates。
- 加 CONTRIBUTING。
- 加 release checklist。
- 加 demo GIF。
- README 顶部讲清楚：谁需要它、它解决什么痛点、如何 3 分钟跑起来。

## 推广策略

### GitHub

首发前仓库应具备：

- 清晰 README 首屏。
- 一张能看出价值的截图。
- 一个 15-60 秒 GIF：从错误回答到 Inspector 定位 checkpoint。
- `uv run python scripts/use_case_smoke.py --reset-demo` 作为可信 demo 证明。
- Issues 里预置 good first issue，例如 Postgres adapter、namespace selector、debug bundle export。

README 首屏建议采用英文为主、中文材料另放 docs：

- 第一行直接讲痛点：Debug LangGraph agent memory like you debug web apps.
- 前 3 行放 demo GIF。
- 先讲 problem，再讲 solution。
- Quick Start 控制在 3-5 行命令。
- 不把首屏写成 feature dump。

### 开发者社区

适合标题：

- 我做了一个 LangGraph checkpoint 的本地黑匣子查看器
- Debugging LangGraph memory bugs from checkpoints, not guesses
- LangGraph Agent 回答错了，怎么找到是哪一步状态写坏了？
- Agent memory 不只是存进去，还要能查清楚哪里污染了

适合渠道：

- GitHub README + demo GIF
- X / Twitter 英文短帖
- LangChain / LangGraph 相关社区
- Reddit `r/LangChain`、`r/LocalLLaMA` 的工具帖
- 掘金 / 知乎中文长文
- 面试项目展示视频

### 内容节奏

1. 内测阶段：私有仓库，完善 demo 和截图。
2. 预发布阶段：公开仓库，但标记 `experimental`。
3. 首发阶段：发布 demo GIF、中文文章、英文短帖。
4. 反馈阶段：把用户 issue 转成 roadmap。

### OpenClaw 脑暴输入

OpenClaw 给出的推广侧高优先级建议：

- 先强化 timeline、diagnostics、diff 这三个最能截图/GIF 化的能力。
- Diagnostics 不只列问题，还要有 `Jump to checkpoint`。
- Postgres checkpoint saver 是生产用户最关心的下一个后端。
- 最容易传播的 demo 是 stale memory bug：错误回答 -> Inspector 定位 -> 修复方向。
- 社区节奏建议：先 LangChain Discord / show-and-tell，再 Hacker News / Reddit / 博客。
- 现在不要做 SaaS、权限系统、复杂品牌设计或过早商业化。

采纳方式：

- 中文文档继续服务求职和本地展示。
- 公开 GitHub README 和首发推广内容优先英文，必要时提供中文镜像文档。
- 下一轮产品打磨优先做 diagnostic -> checkpoint/write 的跳转闭环。

## 暂时不做

- 不做云端账号系统。
- 不急着支持所有 saver backend。
- 不做复杂商业化。
- 不做“AI 自动解释一切”的黑箱诊断。
- 不做华丽但不可调试的图形效果。

## 维护节奏

已经配置工作日周期性维护任务：每天从真实用户角度 review 项目，选择一个最能提升用户价值的小切片，实现、验证、记录。

每次维护都应该留下：

- 改了什么。
- 改善了哪个用户痛点。
- 跑了哪些验证。
- 下一步最值得做什么。

## 当前发布准备状态

最新 launch checklist 和社区内容草稿见 `docs/launch_plan.md`。

在公开首发前，优先补齐：

- license 和 contribution 文档。
- fresh-clone quickstart audit。
- namespace selector。
- debug bundle export。
