# SafeCode Harness — 从需求到 SPEC 到 PLAN 的过程记录

## brainstorming 关键迭代记录

### 1.明确目标用户与项目定位

#### agent 提问：SafeCode Harness 的主要用户是谁？

候选方向：
- 单人课程项目；
- 面向学生学习 Harness 原理；
- 面向老师展示完整产品。

#### 我的决策

面向学习 Agent Harness 原理的学生/开发者，同时满足老师验收需求。

### 2.明确 Agent 能力范围

#### agent 提问：Agent 支持什么类型的 coding task？

候选方向：
- 单纯补全代码；
- 修复 Bug；
- 添加功能；
- 任意代码生成。

#### 我的决策

支持三类受限 coding task：

1. 补全已有代码；
2. 修复已有 Bug；
3. 为已有项目增加功能。

### 3.确定系统架构

#### agent 提供方案：

方案 A：

Pipeline Architecture

方案 B：

Event Driven Architecture

#### 我的决策

选择 Pipeline Architecture。

原因：

- 数据流清晰；
- 模块职责明确；
- 更容易进行单元测试；
- 更符合教学型项目。

## brainstorming 技能反思

### 做的较好的地方

在项目初期，Brainstorming 过程有效帮助我澄清了项目定位和实现边界。

首先，Agent 通过连续追问的方式，帮助我发现了最初方案中的不足。最开始，我倾向于将项目理解为一个能够调用大模型完成代码任务的 AI 编程助手，但经过讨论后意识到，简单的“用户输入需求 → 调用 LLM → 返回代码”的模式更接近普通 AI 应用，而不是 Coding Agent Harness。

通过进一步分析，项目定位逐渐明确为：

- Harness 自身实现 Agent 主循环；
- LLM 只负责提供决策；
- 工具调用、执行控制、测试反馈和治理机制由代码实现；
- Mock LLM 用于确定性验证。

这一过程帮助项目从一个较宽泛的 AI 应用想法，收敛到一个具有明确工程目标和可验证机制的系统。

### 让我不满的地方

虽然 Brainstorming 过程帮助项目逐渐明确了方向，但其中也存在一些让我不满意的地方。

首先，Agent 在项目初期对项目定位的理解存在偏差。最开始的方案容易将 SafeCode Harness 理解为一个具有 WebUI 的 AI 编程 Demo，而没有充分体现 Coding Agent Harness 的核心价值。例如，初始讨论中更多关注用户交互和功能展示，而对于 Agent 主循环、工具调用机制、测试反馈闭环等 Harness 核心机制关注不足。

这导致我需要主动结合课程要求重新调整方向，强调：

- Harness 本身必须由代码实现；
- LLM 只负责决策，而不是直接完成全部工作；
- 工具、治理、反馈等机制必须能够被单独验证。

其次，Agent 在功能规划阶段有一定的“过度设计”倾向。在讨论系统能力范围时，Agent 曾提出较复杂的产品化方向，例如更完整的 WebUI、更丰富的任务类型以及更多扩展功能。

这些方案从产品角度看具有吸引力，但对于本课程项目而言，会带来两个问题：

增加实现成本，使项目难以保证核心机制质量；
分散对于课程重点要求的关注。

因此，我需要主动限制项目范围，将重点放回：

- Agent Loop；
- Tool System；
- Governance Policy；
- Test Feedback Loop；
- Mock LLM Deterministic Testing。

## 自我验证：冷启动试运行记录

第二个 Agent 选择 Task 0.1 作为最早实现任务。

但是它无法确定：Task 0.1 中 CLI 是否只是空 Typer app，还是要包含后续子命令占位。pytest.ini 与 pyproject.toml 二选一，PLAN 未指定偏好。TaskConfig 的 YAML 加载职责应属于模型还是 loader。

根据以上内容以及其他一些歧义对 SPEC / PLAN 进行了修订。

以下是部分修订前后diff：

前：Task 0.1 测试 CLI help；后：Task 0.1 增加 safecode/cli 模块初始化。
前：TaskConfig.from_yaml()；后：TaskConfig 仅负责数据结构定义。TaskConfigLoader 负责 YAML 解析。