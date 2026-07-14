# Coding Agent Harness 项目反思报告

在这次 AI4SE 课程中，我选择完成 A 类 Coding Agent Harness 项目，最终实现了 SafeCode Harness：一个可以连接真实 LLM 或 MockLLM，在受控工作区中读取文件、修改代码、运行测试，并根据测试反馈迭代修复 Python 代码任务的执行框架。整个项目开发过程让我印象深刻的是：当 LLM 已经能写大量代码时，人的核心工作不再只是“写函数”，而是定义边界、拆分任务、判断质量、发现风险，并在 AI 偏离时及时纠正方向。

在 Superpowers 的各项技能中，对我帮助最大的是 brainstorming，writing-plans 以及 test-driven-development。brainstorming 使我在项目开始前就对该项目有了一个很深的理解，通过与智能体的不断对话，智能体不断向我追问有关该项目的信息，我一一回答，同时也加深了对这个项目的理解程度；writing-plans 迫使我在真正让智能体写代码前把任务拆成很小的单元。每个 task 都写清楚目标、文件、接口和测试。这个过程一开始显得十分繁琐，但随着与智能体的深入协作，这个过程在后期证明非常有用。因为 SafeCode Harness 本身模块很多，包括 AgentLoop、LLMBackend、ActionParser、Guardrail、ToolDispatcher、RunTestsTool、TestFeedbackSummarizer、ContextBuilder、CredentialManager、CLI、WebUI 和 Docker 部署。如果没有 PLAN.md 中按阶段拆分开来的任务，后期很容易变成“想到哪里写到哪里”；test-driven-development 对 AI 协作来说不是阻碍，而是放大器。以前我会觉得先写测试再写实现比较慢，但在这个项目里，TDD 实际上降低了我对 AI 生成代码的信任成本，每个 task 都先让智能体写失败测试，再实现最小代码让测试通过，这使我不用完全依赖“代码看起来对不对”，而是用 pytest 结果判断是否完成，尤其是 ActionParser、ShellGuard、RunTestsTool 和 StopController 这些模块，如果没有测试，很难发现边界问题。

另外，我还发现，SPEC 和 PLAN 的质量直接影响实现质量。一个具体的例子是，在 Docker 部署阶段，最初 Dockerfile 只安装 pip install -e .，本地看似可以启动 WebUI，但我在 Run Real 的 demo 中发现，LLM 明明已经正确修改了代码，run_tests 却一直是 error，直到它自己执行 pip install pytest 后测试才通过。这个问题本质上不是 LLM 不会修 bug，而是分发环境没有明确保证 pytest 可用。后来我把 Dockerfile 改为安装 .[dev]，并增加测试检查 Docker 镜像内 pytest 是否可用，这个问题才得到解决。这个案例说明了，如果规约只写“Docker 可以运行 WebUI”，而不写“Docker 中 run_tests 所需环境也必须完整”，智能体就可能实现一个表面可运行但真实闭环不稳定的项目版本。

我最有效的 prompt/context 策略是把任务写成“背景—目标—约束—禁止修改—验证命令—输出格式”。例如修复 Run Real 输出不稳定时，我没有只说“让它更稳定”，而是明确要求 ContextBuilder 强化系统提示、ActionParser 支持从混合文本中提取第一个 JSON 对象、WebUI 展示 parser_error 和脱敏后的 llm_response_summary。这样，AI 就不只是泛泛优化，而是围绕具体失败现象修复。另一个有效策略是每次都让智能体先读取 SPEC.md 和 PLAN.md，并使用 verification-before-completion。这样智能体会更多地对照原始需求，而不是凭自己的习惯扩展不应该有的功能。

凭据与分发是我以前最容易忽略的工程问题。最开始我只关注 Harness 本身能不能跑通，但课程要求迫使我考虑“别人怎么获取项目并运行”“API Key 怎么安全配置”“云端部署时谁的额度会被消耗”等问题。因此我实现了对应的项目功能并且在 README.md 中写清楚了该项目对于普通用户的运行方式。

如果重做一次，我会更早把“普通用户路径”作为验收标准，而不是到最后才集中精力去修改 README.md 和 CLI UX。比如原本 safecode run --workspace . --keep-session 成功后只输出 session_id，没有告诉用户修复后的临时工作区在哪里。这个问题不是核心算法错误，但对普通用户而言非常关键。后来我利用智能体补充了 CLI 输出 Session workspace kept at:，才让用户能直接找到修改后的代码。这个经历让我深刻认识到，一个项目的完成不仅是测试通过，还包括用户能否理解和取回结果。

我对 Superpowers 方法论的批判是：它假设开发者愿意并且有能力把大量隐性判断写成明确规约、任务和日志。这个假设在课程项目中是成立的，因为我们需要证明过程；但在真实开发快速迭代中，过多流程可能会让人觉得负担较重。它还假设 task 能被清晰切分，而现实中很多 bug 是跨模块的，需要反复探索明确。不过总体上，在这个项目里 Superpowers 的假设大部分成立，因为 SafeCode Harness 本身就是一个模块化、机制密集、适合 TDD 的项目。它让我从“让 AI 写代码”转向“用工程纪律管理 AI 写代码”，这是我在本项目开发过程中最大的收获。
