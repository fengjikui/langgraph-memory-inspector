# 维护与推广策略

## 项目原则

LangGraph Memory Inspector 的长期原则是：

> 站在真实开发者用户的角度设计产品，不做只给面试官看的炫技 demo。

每一次迭代都应该回答三个问题：

1. 真实开发者遇到什么痛点？
2. 这个改动是否缩短了他的调试路径？
3. 这个能力是否能被截图、GIF、测试或 demo 明确证明？

## 给未来维护者的提醒

这个项目最容易跑偏的地方，是把“能展示 checkpoint”误认为“能帮助用户调试”。未来每次继续维护前，先用下面这句话校准：

> 不要为了展示技术而做工具，要为了让真实开发者少痛一次而做工具；每个功能都必须回答“用户遇到什么具体麻烦，它怎么帮用户更快定位问题”。

判断一个改动是否值得做，优先看它能不能让用户更快完成一条真实调试链：

1. 发现 Agent 行为异常。
2. 找到最相关的 thread、namespace 或 checkpoint。
3. 看见坏状态第一次出现的位置。
4. 追到导致它的 state path、write channel、node/task 或 retrieved context。
5. 把证据导出给同事、issue、PR 或事故复盘。

如果一个功能不能进入这条链，就先降级为 backlog。漂亮图表、更多筛选项、AI 总结、社区推广文案，都必须服务这条链，而不是替代它。

## 经验教训

- 演示故事比功能列表重要。“可视化 checkpoint”不够强，“定位为什么搬到杭州后 Agent 还在用上海记忆”才是用户能立刻理解的痛点。
- 诊断要给证据，不只给判断。每个 diagnostic 最好能带到 checkpoint、state path、write channel 或 retrieved context，否则用户仍然要自己重新排查。
- 支持新 backend 要先定义安全边界。生产数据必须 read-only、local-first、默认不上传；遇到 latest-only 或不可还原 schema，应明确报告 unsupported，而不是假装能读懂。
- 推广不是拉 star，而是寻找真实 bug pattern。首发内容应该邀请 LangGraph 用户提供他们最痛的 checkpoint / memory 调试场景。
- 每轮维护都要留下可验证痕迹：测试、CI、截图、GIF、release notes、issue 链接或 demo script。没有证据的“完成”不算完成。

## 下一轮行动准则

每次重新开始工作时，按这个顺序选择任务：

1. 先看现有 open issue 是否包含真实用户反馈或能带来真实 bug pattern。
2. 再看 README / quickstart / demo 是否仍然能让新用户在 5 分钟内获得价值。
3. 然后补诊断能力、fixture、测试和 UI 跳转，让调试链更短。
4. 最后再做推广材料、社区帖子和视觉资产。

停手前必须回答：

- 用户现在比上一轮少走了哪一步弯路？
- 这个变化有没有被测试、CI、截图或文档证明？
- 有没有引入隐私、生产数据读取、磁盘增长或误导性诊断风险？
- 下一位维护者打开项目时，是否知道接下来最该做什么？

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

### P0：完成公开首发闭环

- 上传 GitHub social preview，避免公开链接在社区里显得像未完成仓库。
- 发布第一篇 LangChain Forum / Slack 帖子，主诉求是收集真实 checkpoint bug pattern。
- 持续维护 #20，把真实反馈拆成 fixture、diagnostic、UI 跳转或 backend 支持 issue。
- 用当前 stale memory / stale retrieved context demo 作为所有推广内容的主线，不临时换故事。

### P1：围绕真实反馈加深调试能力

- 根据用户反馈增加下一批高价值 diagnostics，例如 reducer append mistake、wrong resume point、message bloat 或 namespace confusion。
- 做 large-store 导航能力时，先从真实生产痛点出发，再决定 metadata search、timeline virtualization 或 server-side index。
- 继续扩展 saver 兼容性，但保持 read-only 和 schema doctor 优先；读不懂的 schema 要诚实报告。
- 把每个新增诊断都绑定一个 fixture、一个测试和一个可演示用户故事。

### P2：提高外部贡献和复用质量

- 把常见反馈沉淀进 issue templates、diagnostic matrix 和 release checklist。
- 为第一个外部贡献者准备更小的 good first issue，而不是只留下大而模糊的路线图。
- 保持 README、release notes、demo GIF 和 quickstart 一致，任何一个入口都不能讲旧能力。
- 如果推广带来真实用户，再考虑更正式的网站、视频和多语言文档。

## 推广策略

### GitHub

首发前仓库应具备：

- 清晰 README 首屏。
- 一张能看出价值的截图。
- 一个 15-60 秒 GIF：从错误回答到 Inspector 定位 checkpoint。
- `uv run lgmi prove-demo --reset-demo` 作为可信 demo 证明。
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

最新 launch checklist 见 `docs/launch_plan.md`，可执行社区发布方案见
`docs/community_launch_playbook.md`。

公开首发前的代码和文档 gate 已经基本就绪。现在优先做两类事：

- 人工上传 GitHub social preview，然后发 LangChain Forum 首帖。
- 把 #20 后续收到的真实反馈继续拆成更小的可实现 issue。
- 已把 [#24](https://github.com/fengjikui/langgraph-memory-inspector/issues/24)
  落成 synthetic fixture、确定性诊断和诊断矩阵回归。
- 已把 [#25](https://github.com/fengjikui/langgraph-memory-inspector/issues/25)
  落成 `ShallowPostgresSaver` schema 检测和安全 doctor 报告。
- 已把 [#26](https://github.com/fengjikui/langgraph-memory-inspector/issues/26)
  落成 checkpoint id 前缀过滤和 filtered-vs-total 计数。
