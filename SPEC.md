# SafeCode Harness — 项目规格说明书 (SPEC)

## 1. 问题陈述

### 1.1 要解决的问题

当前 AI Coding Agent（如 OpenCode、Cursor、Copilot）能够完成代码生成、Bug 修复、功能添加等开发任务，但其内部执行过程缺少透明性和可控性。真实 LLM 本身不能保证安全地修改代码、执行命令和访问文件系统——它的行为需要通过一个**可审计、可治理的代码层**来编排和约束。

SafeCode Harness 面向软件开发场景，实现一个**受控的 Coding Agent 执行框架**。它连接真实 LLM（通过 OpenAI-compatible API，如 Token Hub）和受限代码工作区，使 Agent 能够执行代码阅读、代码修改、测试运行等开发任务，同时通过 Harness 内部机制限制危险行为，并利用测试反馈驱动多轮修正。

软件开发场景天然适合作为 Harness 机制验证领域：
- **工具清晰**：文件读写、代码搜索、测试执行、Shell 命令，每项操作都有明确的输入输出。
- **反馈信号客观**：pytest 通过/失败、编译错误、运行错误，不依赖主观判断。
- **危险动作可定义**：删除文件、访问敏感信息、执行危险命令，都有明确的拦截规则。
- **结果可验证**：测试通过即成功，测试失败即需修正，循环终止条件明确。

SafeCode Harness 本身不是要替代 OpenCode 或成为生产级 Coding Agent 产品，而是实现一个**最小但完整的 Coding Agent 执行框架**，其核心价值在于：所有治理机制（护栏、反馈闭环、上下文管理、停机判断）都以确定性代码实现，可被审计、测试和验证。

### 1.2 目标用户

| 角色 | 描述 | 使用方式 |
|------|------|----------|
| **首要用户：AI 辅助软件开发的开发者或研究者** | 需要让真实 LLM 在受控工作区中执行 coding task 的用户 | 配置 API Key → 编写 `task.yaml` → 通过 CLI 或 WebUI 启动任务 → 观察 Agent 执行过程 |
| **次要用户：学习 Coding Agent Harness 原理的学生** | 通过阅读真实 Harness 实现来理解 agent 内部机制的学习者 | clone 项目 → 阅读源码 → 运行 mock LLM 测试 → 理解每个模块的职责和交互 |
| **验收用户：课程老师/助教** | 最终评分者 | 阅读文档 → 运行 `pytest` → 通过 CLI 和 WebUI 验证真实 LLM 和 mock LLM 两种模式 → 确认 Docker 可复现 |

### 1.3 为什么值得做

- 它提供一个**真实可运行的 Coding Agent 执行框架**，LLM 的行为由代码层编排、限制和验证，而非仅靠 prompt 约束。
- 所有核心机制——工具分发、治理护栏、测试反馈闭环、上下文管理——都以**确定性代码**实现，均可在 mock LLM 下离线验证。
- 重点维度**治理护栏**和**测试反馈闭环**是当前 AI4SE 领域的关键议题，本项目通过工程实现来探索和展示这些机制。
- 软件开发场景提供了最清晰的 Agent 环境交互：工具、反馈、危险、可验证结果，天然适合作为 Harness 机制的验证领域。

---

## 2. 用户故事

| ID | 角色 | 故事 | 验收条件 |
|----|------|------|----------|
| US-01 | 开发者 | 作为开发者，我希望配置真实 LLM API Key 后，通过 CLI 启动一个 bug 修复任务，Agent 自动读取代码、运行测试、根据失败反馈修改代码，最终测试通过 | 运行 `safecode run --workspace examples/fix_bug`，在真实 LLM 模式下 Agent 完成"读取代码 → 运行测试 → 修改代码 → 重跑测试 → 通过"的完整闭环 |
| US-02 | 开发者 | 作为开发者，我希望 Agent 在尝试执行危险操作（如 `rm -rf`、读取 `.env`）时被 Harness 的护栏机制拦截，而非仅靠 LLM 自觉 | 任务中 Agent 尝试危险动作，CLI 输出结构化 `GuardrailEvent`，`blocked = true`，`blocked_count` 递增 |
| US-03 | 研究者 | 作为研究者，我希望用 pytest 运行单元测试，在 mock LLM 下验证所有核心机制的正确性，无需依赖真实 LLM 或网络 | 执行 `pytest`，所有测试通过，核心 harness 模块覆盖率 ≥ 80% |
| US-04 | 学生 | 作为学生，我希望阅读 SafeCode Harness 的源码，理解 Agent Loop、Tool Dispatcher、Guardrail、Test Feedback Summarizer 和 Context Builder 的实现原理 | 每个核心模块有清晰的 docstring 和对应的单元测试，README 提供模块导读 |
| US-05 | 开发者 | 作为开发者，我希望通过 `safecode auth set` 安全地配置 API Key 到系统 keyring，不将密钥明文写入任何文件 | 执行 `safecode auth set` → 输入 Key → `safecode auth status` 显示 `configured`（不回显明文）→ Key 不出现在 git 历史或日志中 |
| US-06 | 老师/助教 | 作为验收者，我希望通过 WebUI 选择一个预置任务，点击运行，观察 Agent 在真实 LLM 驱动下的逐步执行、护栏拦截和测试反馈 | WebUI 启动后，选择任务 → 点击 Run → 逐步展示每轮 action、工具结果、护栏事件、测试状态和最终结果 |
| US-07 | 老师/助教 | 作为验收者，我希望用 Docker 一键构建并运行整个项目，在 mock 模式下验证所有核心机制 | `docker build -t safecode-harness . && docker run --rm -p 8000:8000 safecode-harness`，WebUI 可访问，mock demo 可运行 |

---

## 3. 功能规约

### 3.1 模块总览

```
CLI (Typer) ──┐
              ├── Configuration Manager ──→ Task Config Loader ──→ Session Manager ──→ Agent Loop
WebUI (FastAPI)┘
```

Agent Loop 内部管道（Pipeline Architecture）：

```
Context Builder → LLM → Action Parser → Guardrail → Tool Dispatcher → Tool Executor
                                      ↑ 拦截/错误          ↓
                                      └── 反馈 ←── Test Feedback Summarizer
```

Harness 六大维度在本规约中的对应模块：

| 维度 | 对应模块 | 章节 |
|------|---------|------|
| 决策封装 | Agent Loop + Action Parser | §3.6, §3.8 |
| 动作/工具 | Tool Dispatcher + 7 个工具 | §3.9 |
| 上下文与记忆 | Context/Memory Manager | §3.12 |
| 治理护栏 | Guardrail | §3.10 |
| 反馈闭环 | Test Feedback Summarizer | §3.11 |
| 配置 | Configuration Manager | §3.15 |

### 3.2 CLI 层

**输入**：命令行参数（子命令、选项）。
**行为**：
- `safecode run --workspace <path>`：以真实 LLM 模式运行指定工作区的任务（需 `task.yaml`）。
- `safecode run --workspace <path> --mock`：以 mock LLM 模式运行，用于测试和验证 Harness 机制。
- `safecode demo list`：列出所有预置示例任务。
- `safecode demo run <demo-id>`：以真实 LLM 模式运行预置 demo。
- `safecode demo run <demo-id> --mock`：以 mock LLM 模式运行预置 demo。
- `safecode auth set`：交互式输入 API Key 并保存到系统 keyring。
- `safecode auth status`：显示 Key 配置状态（`configured` / `missing`），不回显明文。
- `safecode auth clear`：清除 keyring 中已保存的 API Key。
- `safecode serve`：启动 WebUI 服务。
**输出**：结构化执行轨迹（每轮 action、工具结果、测试变化、护栏事件、`final_status`）。
**错误处理**：参数缺失提示帮助信息；API Key 缺失时提示运行 `safecode auth set`。
- 首次运行检测：若启动真实 LLM 模式时检测到 API Key 未配置，CLI 自动引导用户执行 `safecode auth set` 录入 Key，而非直接报错退出。

### 3.3 WebUI 层

**输入**：HTTP 请求（选择任务、启动运行，可选择真实 LLM 或 mock 模式）。
**行为**：
- 首页展示预置示例任务列表（按 `demo_order` 排序）。
- 用户选择任务并选择运行模式（真实 LLM 或 mock），点击 Run。
- 逐步展示执行轨迹：每轮 action、工具名、参数摘要、结果摘要、测试状态变化、护栏拦截事件。
- 最终展示 `final_status` 和会话摘要。
- 不做登录、用户管理、项目管理等复杂功能。
**输出**：HTML 页面，轻量级前端（Jinja2 模板 + 原生 HTML/CSS，不依赖 React/Vue 等重型框架）。
**错误处理**：后端错误返回 HTTP 500 + 错误信息。

### 3.4 Task Config Loader

**输入**：`task.yaml` 文件路径或 demo ID。
**行为**：
- 解析 `task.yaml`（见 6.1 数据模型）。
- 校验必填字段（`id`、`title`、`task_type`、`workspace_template`、`test_command`）。
- 校验 `allowed_tools` 中所有工具名有效。
- 返回 `TaskConfig` 对象。
**输出**：`TaskConfig` 或 `ValidationError`。
**边界条件**：YAML 解析失败、字段缺失、工具名无效时返回明确错误。

### 3.5 Session Manager

**输入**：`TaskConfig` + `LLMBackend`（real 或 mock）。
**行为**：
- 从 `workspace_template` 复制到临时目录 `/tmp/safecode-session-{uuid}`。
- 创建 `Session` 对象，初始化 `blocked_count = 0`、`step_id = 0`、`start_time`。
- 调用 Agent Loop 执行。
- 会话结束或终止后，清理临时工作区（除非 `--keep-session`）。
- 持久化 `session_trace.json` 到 `.safecode/` 目录。
**输出**：`Session` 对象（含完整执行轨迹）。
**错误处理**：模板目录不存在、复制失败、磁盘空间不足。

### 3.6 Agent Loop（主循环）

**输入**：`Session` + `LLMBackend` + `TaskConfig`。
**行为**（每轮迭代）：

1. 检查停止条件（见 3.13），若满足则终止。
2. `Context Builder` 构造当前上下文（见 3.12）。
3. 调用 `LLMBackend.query(context)` 获取 LLM 响应。
4. `Action Parser` 解析 LLM 响应为 `ParsedAction`（见 3.8）。
5. `Guardrail` 检查 action（见 3.10）。
6. 若被拦截：返回结构化错误给 LLM，`blocked_count += 1`，若 `blocked_count >= 3` 则终止。
7. 若通过：`Tool Dispatcher` 分发到对应工具执行（见 3.9）。
8. 若工具为 `run_tests`：`Test Feedback Summarizer` 生成结构化反馈（见 3.11）。
9. 更新 `step_id += 1`，回到步骤 1。

**输出**：`Session` 含完整 `steps` 列表和 `final_status`。
**边界条件**：`max_iterations` 默认 10；单轮超时由 `timeout_seconds` 控制。

### 3.7 LLM 抽象层

SafeCode Harness 的 LLM 抽象层支持两种后端，它们共享同一接口 `LLMBackend.query(context: ContextPayload) -> str`。

**RealLLM（主要运行路径）**：
- 通过 OpenAI-compatible API 调用真实 LLM（如 Token Hub 提供的模型）。
- 配置：`base_url`、`model`、`temperature`（默认 0）、`api_key`。
- `api_key` 从 keyring → 环境变量 → `.env` 按优先级读取。
- 超时处理：单次 API 调用超时 60 秒，返回错误，不计入 `max_iterations`。
- RealLLM 是 SafeCode Harness 的**主要运行模式**。Agent 通过 RealLLM 真实地推理代码问题、决定下一步动作，在受限工作区中完成 coding task。

**MockLLM（工程验证路径）**：
- 用于验证 Harness 内部机制，不依赖网络和真实模型。
- 支持两种模式：
  - **Scripted Mode**：构造函数接收 `actions: list[dict]`，按顺序返回，用于测试 Agent Loop、Tool Dispatcher、Stop Controller 等基础机制。
  - **Rule-based Mode**：构造函数接收 `rules: list[Rule]`，每条规则为 `(predicate, action)`。`predicate` 检查 `ContextPayload` 中的结构化字段（如 `last_test_feedback.failed_test_names`、`last_guardrail_event.reason`、`step_id`），命中则返回对应 `action`。用于测试反馈闭环和护栏恢复等需要上下文感知的机制。
- 两种模式都是**确定性的**：相同输入产生相同输出。
- MockLLM 不是产品能力的替代，而是**工程验证手段**。它确保 Harness 的每个核心机制都能在移除真实 LLM 的不可控因素后被独立验证。

### 3.8 Action Parser

**输入**：LLM 响应字符串。
**行为**：
- 使用严格 JSON parser 解析。
- 校验必填字段 `tool` 和 `params`。
- 校验 `tool` 值在允许列表中（`list_files`、`read_file`、`search_content`、`write_file`、`edit_file`、`run_tests`、`run_shell`、`finish`）。
- 校验 `params` 符合对应工具的 schema。
- 可选字段 `thought_summary` 记录但不用于安全判断。
**输出**：`ParsedAction` 或 `InvalidActionError`（含 `reason`）。
**错误处理**：
- 非 JSON → `invalid_json`。
- 缺少 `tool`/`params` → `missing_fields`。
- 未知 `tool` → `unknown_tool`。
- 参数不符合 schema → `invalid_params`。
- 连续无效动作 ≥ 3 次 → 终止会话。

### 3.9 Tool Dispatcher

**输入**：`ParsedAction` + `Session`。
**行为**：根据 `tool` 字段分发到对应工具函数。
**工具清单**：

| 工具 | 功能 | 护栏限制 |
|------|------|----------|
| `list_files` | 列出工作区目录结构，默认忽略 `.git`、`.venv`、`__pycache__`、`.pytest_cache` | 路径护栏 |
| `read_file` | 读取文本文件内容，单次读取大小限制 | 路径护栏 + 敏感文件护栏 |
| `search_content` | 在工作区内按关键词/简单正则搜索内容 | 路径护栏 + 敏感文件护栏 |
| `write_file` | 创建或整体覆盖文件 | 路径护栏 + 敏感文件护栏 |
| `edit_file` | 精确替换（`old_text` → `new_text`），不唯一或找不到则失败 | 路径护栏 + 敏感文件护栏 |
| `run_tests` | 运行 `pytest`，返回结构化结果 | 仅允许预配置的测试命令 |
| `run_shell` | 执行 allowlist 中的低风险命令（`git diff`、`git status`、`python -m py_compile` 等） | 命令 allowlist 护栏 |

**输出**：`ToolResult`（含 `success`、`data`、`error` 等字段）。

### 3.10 Guardrail（治理护栏）

**输入**：`ParsedAction` + `Session`。
**行为**（按检查顺序）：

1. **路径护栏（Path Guard）**：对所有文件工具，`Path.resolve()` 后检查是否在 `workspace_root` 内。禁止 `../`、符号链接、绝对路径逃逸。
2. **敏感文件护栏（Sensitive File Guard）**：禁止读取/写入匹配模式的文件：`.env`、`.env.*`、`*.key`、`*.pem`、`secrets.json`、`id_rsa`、`.git/config`。
3. **命令护栏（Shell Guard）**：对 `run_shell`，检查命令是否在 allowlist 中。禁止 `rm`、`del`、`rmdir`、`format`、`shutdown`、`curl | sh`、`npm publish`、`git push`、`git push --force` 等。

**拦截响应**：
```json
{
  "blocked": true,
  "reason": "dangerous_shell_command | path_outside_workspace | sensitive_file_access",
  "tool": "run_shell",
  "action_summary": "attempted rm -rf /",
  "recoverable": true,
  "suggestion": "请使用允许的命令，如 git diff 或 python -m py_compile"
}
```

**拦截阈值**：同一会话 `blocked_count >= 3` 时终止，`final_status = terminated_by_guardrail`。
**严重性加权**（扩展）：高危命令（`rm -rf /`、`format`、`shutdown`、`curl | sh` 等）可一次性增加更高权重，最小实现先使用统一阈值 3。

### 3.11 Test Feedback Summarizer（测试反馈闭环）

**输入**：`run_tests` 的原始结果（exit_code、stdout、stderr）。
**行为**：
- 解析 pytest 输出，提取 `passed_count`、`failed_count`、`skipped_count`、`duration_ms`。
- 对每个失败测试，提取：测试名、断言信息、关键 traceback 片段（截断）、相关文件路径与行号。
- 截断过长输出，总反馈内容有最大字符数/token 预算。
- 与上一轮测试结果对比，生成：
  - `previous_failed_count` / `current_failed_count`
  - `fixed_tests`：上一轮失败但本轮通过
  - `new_failures`：本轮新增失败
  - `unchanged_failures`：仍然失败
  - `progress_summary`：如 "上一轮 3 个失败，本轮 1 个失败，修复了 2 个"
- 生成下一步提示（如测试全部通过则提示 finish；失败减少则提示继续；失败增加则提示回顾最近修改）。
**输出**：`TestFeedback` 结构化对象。
**边界条件**：pytest 输出不可解析时返回原始摘要；超时返回 `status = timeout`。

### 3.12 Context/Memory Manager

SafeCode Harness 的记忆管理分为**会话内上下文管理**和**跨会话记忆**两个层面。

**会话内上下文管理**：

**输入**：`Session`（含历史 steps）。
**行为**：
- 每轮构造 `ContextPayload` 发送给 LLM。
- 内容优先级（从高到低）：
  1. System prompt 和安全规则（不可裁剪）
  2. 当前任务目标（来自 `task.yaml`）
  3. 最近测试反馈（`TestFeedback`）
  4. 最近工具执行结果（`ToolResult`）
  5. 最近文件修改 diff 摘要
  6. 当前工作区文件树摘要
  7. 历史对话摘要（早期轮次压缩）
- 超出上下文预算时，优先丢弃/压缩早期对话，不丢弃安全规则和当前测试反馈。
- 不记录 API Key、`.env` 内容、敏感文件内容。
**输出**：`ContextPayload`。

**跨会话记忆**：

- 每个会话结束后，`session_trace.json` 持久化到工作区 `.safecode/` 目录。
- `session_trace.json` 保存该会话的**结构化摘要**（`final_status`、`steps` 摘要、护栏事件摘要、测试结果摘要），不保存完整聊天历史。
- 新会话启动时，Context Builder 可以按需加载最近一次会话的摘要信息（如上次任务的 `final_status`、最后一次测试结果），作为历史上下文注入到新会话的 `ContextPayload` 中。
- 跨会话记忆**不全量加载**旧对话——仅加载摘要，避免上下文爆炸。
- 跨会话记忆不跨工作区——每个工作区的 `.safecode/` 目录独立。

### 3.13 Session Stop Controller（停止条件）

**检查顺序**（任一满足即停止）：

| 停止条件 | 判定 | `final_status` |
|----------|------|----------------|
| 测试通过 | `run_tests` 返回 `exit_code = 0` 且 `status = passed` | `success` |
| 最大轮数 | `step_id >= max_iterations` | `max_iterations_reached` |
| 护栏阈值 | `blocked_count >= 3` | `terminated_by_guardrail` |
| 总超时 | 会话总耗时 ≥ `timeout_seconds`（默认 300s） | `timeout` |
| LLM finish | LLM 返回 `finish` action，且测试已通过 | `success` |
| LLM finish（未通过） | LLM 返回 `finish` 但测试未通过 | `finished_without_passing_tests` |
| 连续无效动作 | `invalid_action_count >= 3` | `invalid_action_limit_reached` |

### 3.15 Configuration Manager（配置管理）

Configuration Manager 是 Harness 六大维度中"配置"维度的实现，负责让使用者通过声明式规则约束 Agent 的行为。它不是简单的配置文件读取，而是 Harness 中一个**可编程的配置解析与合并层**。

**配置来源优先级**（从高到低）：
1. 命令行参数（如 `--max-iterations 5`、`--model gpt-4`）
2. 环境变量（`SAFECODE_MODEL`、`SAFECODE_BASE_URL` 等）
3. `config.yaml` 全局配置文件中的非敏感配置
4. 内置默认值

**全局配置项**（`config.yaml` 或环境变量）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `base_url` | `https://njusehub.info/v1` | LLM API 端点 |
| `model` | `qwen3.7-max` | 模型名称 |
| `temperature` | `0` | LLM 温度参数 |
| `max_iterations` | `10` | 最大迭代轮数 |
| `timeout_seconds` | `300` | 会话总超时 |
| `test_command` | `pytest` | 默认测试命令 |
| `context_budget_chars` | `8000` | 上下文字符预算 |
| `guardrail_threshold` | `3` | 护栏拦截阈值 |
| `shell_allowlist` | `["git diff", "git status", "python -m py_compile"]` | 允许的 Shell 命令 |

**任务级配置与全局配置的关系**：
- 每个 `task.yaml` 中的 `max_iterations`、`timeout_seconds`、`allowed_tools`、`forbidden_tools` 等字段为**任务级覆盖**。
- 任务级配置优先级高于全局配置，但低于命令行参数。
- 若 `task.yaml` 未指定某字段，则回退到全局配置或内置默认值。

**运行时覆盖规则**：
- 命令行参数 `--max-iterations` 覆盖 `task.yaml` 和全局配置。
- `--mock` 标志强制使用 MockLLM，忽略全局 `model` 和 `base_url`。
- `--keep-session` 覆盖默认的会话清理行为。
- `api_key` 不能通过 `config.yaml` 配置，只能来自 keyring、环境变量或 `.env`。

**配置校验**：
- 启动时校验所有配置项的类型和范围（如 `max_iterations` 必须为正整数，`temperature` 必须在 0–2 之间）。
- 校验失败时返回明确错误信息，不静默使用默认值。

**输出**：合并后的 `RuntimeConfig` 对象，供 Session Manager 和 Agent Loop 使用。

**边界条件**：配置文件和 task.yaml 解析失败时返回明确错误；必需配置项缺失时终止启动并提示用户。

### 3.14 Workspace Manager

**输入**：`workspace_template` 路径。
**行为**：
- 将模板目录复制到 `/tmp/safecode-session-{uuid}`。
- 设置 `workspace_root` 为该临时路径。
- 会话结束后自动清理临时目录。
- 若指定 `--keep-session`，保留临时目录供调试。
**输出**：`workspace_root` 路径。
**错误处理**：模板不存在、磁盘空间不足、复制权限不足。

---

## 4. 非功能性需求

### 4.1 性能

- Mock LLM 模式下单个 demo 执行时间 < 10 秒。
- 真实 LLM 模式下单次 API 调用超时 60 秒。
- 单个工具执行超时：`run_tests` 默认 60 秒，`run_shell` 默认 30 秒。
- Docker 镜像大小 < 500MB。

### 4.2 安全

- **凭据威胁模型**：API Key 明文不得出现在代码仓库、日志、执行轨迹、测试输出、错误信息中。
- **凭据存储**：首选 keyring（Windows Credential Manager / macOS Keychain / Linux Secret Service），环境变量和 `.env` 仅作兜底。
- **工作区隔离**：代码层路径校验 + Docker 非 root 用户 + 临时工作区副本，三层防护。
- **命令执行**：`run_shell` 仅允许 allowlist 中的命令，禁止任意 shell 执行。
- **敏感文件**：`.env`、`*.key`、`*.pem`、`secrets.json`、`id_rsa`、`.git/config` 禁止读写。
- **安全边界声明**：本项目是受控的 Coding Agent 执行框架，非生产级安全沙箱。README 和 SPEC 中明确此声明。

### 4.3 可用性

- 无网络环境下 `pytest` 和 `safecode run --mock` 必须可运行。
- 有网络 + API Key 时，真实 LLM 模式可运行。
- CLI 帮助信息清晰（`safecode --help`、`safecode run --help`）。
- WebUI 无需登录即可使用（本地或云部署均可）。
- 云部署后公网 URL 可访问 WebUI，mock 模式无需 API Key 也可演示。
- 错误信息包含 actionable 的修复建议（如缺少 API Key 时自动引导 `safecode auth set`）。

### 4.4 可观测性

- 每轮执行记录到 `session_trace.json`。
- CLI 输出完整执行轨迹（每轮 action、工具结果、测试变化、护栏事件）。
- WebUI 逐步展示执行步骤，支持两种模式（真实 LLM 和 mock）。
- 护栏拦截事件以结构化格式记录。
- 日志级别可通过配置调整。

---

## 5. 系统架构

### 5.1 组件图

```
┌─────────────────────────────────────────────────────────────┐
│                      SafeCode Harness                        │
│                                                              │
│  ┌──────┐  ┌───────┐                                        │
│  │ CLI  │  │ WebUI │                                        │
│  └──┬───┘  └───┬───┘                                        │
│     │          │                                             │
│     └────┬─────┘                                             │
│          ▼                                                   │
│  ┌───────────────┐     ┌──────────────┐                     │
│  │ Task Config   │────▶│   Session    │                     │
│  │   Loader      │     │   Manager    │                     │
│  └───────────────┘     └──────┬───────┘                     │
│                               │                              │
│                               ▼                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │                   Agent Loop                        │     │
│  │                                                     │     │
│  │  ┌─────────┐   ┌──────┐   ┌───────┐   ┌────────┐  │     │
│  │  │ Context │──▶│ LLM  │──▶│Action │──▶│Guardrail│  │     │
│  │  │ Builder │   │Backend│   │Parser │   │        │  │     │
│  │  └─────────┘   └──────┘   └───────┘   └───┬────┘  │     │
│  │                     ▲                      │       │     │
│  │                     │              ┌───────▼────┐  │     │
│  │                     │              │    Tool    │  │     │
│  │  ┌─────────────────┐│              │ Dispatcher │  │     │
│  │  │Test Feedback    ││              └───────┬────┘  │     │
│  │  │  Summarizer     ││                      │       │     │
│  │  └────────┬────────┘│         ┌────────────┼───┐   │     │
│  │           │         │         │   Tools    │   │   │     │
│  │           │         │         └────────────┘   │   │     │
│  │           └─────────┘                          │   │     │
│  └────────────────────────────────────────────────┘     │     │
│                                                              │
│  ┌──────────────────┐  ┌──────────────┐                    │
│  │  Stop Controller │  │  Workspace   │                    │
│  │                  │  │  Manager     │                    │
│  └──────────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 数据流

```
1. 用户通过 CLI/WebUI 选择任务，指定运行模式（real / mock）
2. Task Config Loader 解析 task.yaml → TaskConfig
3. Session Manager 复制模板 → 临时工作区 → 创建 Session
4. Agent Loop 开始：
   a. Context Builder 构造 ContextPayload（含 system prompt + 任务 + 历史 + 反馈）
   b. LLMBackend.query(context) → 原始响应字符串
      - RealLLM：通过 OpenAI-compatible API 调用真实模型
      - MockLLM：确定性返回预设 action
   c. Action Parser 解析 → ParsedAction
   d. Guardrail 检查 → 通过/拦截
   e. 若拦截：生成 GuardrailEvent，blocked_count++，返回错误给 LLM，回到步骤 a
   f. 若通过：Tool Dispatcher 分发 → 工具执行 → ToolResult
   g. 若工具为 run_tests：Test Feedback Summarizer 生成 TestFeedback
   h. Stop Controller 检查是否满足停止条件
   i. 若不满足：回到步骤 a
5. 会话结束，返回 Session（含 final_status + 完整轨迹）
```

### 5.3 外部依赖

| 依赖 | 用途 | 备注 |
|------|------|------|
| OpenAI-compatible API (Token Hub) | 真实 LLM 推理 | 主要运行模式；`--mock` 时不需要 |
| Python keyring 库 | 凭据安全存储 | 对接系统 keyring |
| pytest | 测试执行与项目测试框架 | 核心依赖 |
| Typer | CLI 框架 | 轻量级 |
| FastAPI + uvicorn | WebUI 后端 | 轻量级 |
| PyYAML | task.yaml 解析 | 任务配置 |
| Docker | 分发与运行环境隔离 | 非运行时依赖 |
| Render | 云部署平台 | 免费额度，公网 WebUI 访问 |

---

## 6. 数据模型

### 6.1 TaskConfig（任务配置）

```yaml
id: fix_bug
title: "修复 calculator.add 的错误实现"
task_type: fix_bug  # complete_function | fix_bug | add_feature
description: "修复 src/calculator.py 中 add 函数的 bug，使 tests/test_calculator.py 中的测试全部通过"
workspace_template: examples/fix_bug
test_command: pytest
max_iterations: 10
timeout_seconds: 300
allowed_files: ["src/calculator.py", "tests/test_calculator.py"]
read_only_files: ["tests/test_calculator.py"]
protected_files: [".env", ".env.*", "*.pem", "*.key", "secrets.json", ".git/config"]
allowed_tools: ["list_files", "read_file", "search_content", "edit_file", "run_tests"]
forbidden_tools: ["run_shell"]
forbidden_actions: ["access_outside_workspace", "read_sensitive_file", "delete_files", "publish_package"]
hints: "优先阅读测试文件理解期望行为，修改 src/calculator.py 而不是修改测试"
success_criteria:
  - pytest_exit_code_is_zero
  - no_guardrail_termination
  - modified_files_within_allowed_files
expected_final_files: ["src/calculator.py", "tests/test_calculator.py"]
mock_scenario: fix_bug_feedback_loop  # 用于 mock 模式复现
demo_visible: true
demo_order: 2
expected_trace_events: ["run_tests_failed", "feedback_generated", "edit_file_applied", "tests_passed"]
```

### 6.2 Session（会话）

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | `str` (UUID) | 会话唯一标识 |
| `task_config` | `TaskConfig` | 关联的任务配置 |
| `workspace_root` | `Path` | 临时工作区路径 |
| `steps` | `list[SessionStep]` | 执行步骤列表 |
| `blocked_count` | `int` | 危险动作拦截计数 |
| `invalid_action_count` | `int` | 无效动作计数 |
| `start_time` | `datetime` | 会话开始时间 |
| `end_time` | `datetime` | 会话结束时间 |
| `final_status` | `SessionStatus` | 最终状态 |
| `llm_backend` | `str` | `"real"` 或 `"mock"` |

### 6.3 SessionStep（执行步骤）

| 字段 | 类型 | 说明 |
|------|------|------|
| `step_id` | `int` | 步骤序号（从 0 开始） |
| `llm_request` | `ContextPayload` | 发送给 LLM 的上下文 |
| `llm_response` | `str` | LLM 原始响应 |
| `parsed_action` | `ParsedAction \| None` | 解析后的动作（解析失败则为 None） |
| `guardrail_result` | `GuardrailEvent \| None` | 护栏检查结果（通过则为 None） |
| `tool_result` | `ToolResult \| None` | 工具执行结果（未执行则为 None） |
| `test_feedback` | `TestFeedback \| None` | 测试反馈摘要（非 run_tests 则为 None） |
| `timestamp` | `datetime` | 步骤时间戳 |

### 6.4 ParsedAction（解析后的动作）

| 字段 | 类型 | 说明 |
|------|------|------|
| `tool` | `str` | 工具名 |
| `params` | `dict` | 工具参数 |
| `thought_summary` | `str \| None` | 可选意图摘要 |

### 6.5 ToolResult（工具执行结果）

| 字段 | 类型 | 说明 |
|------|------|------|
| `tool` | `str` | 工具名 |
| `success` | `bool` | 是否执行成功 |
| `data` | `dict \| None` | 执行结果数据 |
| `error` | `str \| None` | 错误信息 |
| `duration_ms` | `int` | 执行耗时 |

### 6.6 GuardrailEvent（护栏事件）

| 字段 | 类型 | 说明 |
|------|------|------|
| `blocked` | `bool` | 始终为 `true` |
| `reason` | `str` | `dangerous_shell_command` / `path_outside_workspace` / `sensitive_file_access` |
| `tool` | `str` | 被拦截的工具名 |
| `action_summary` | `str` | 动作摘要 |
| `recoverable` | `bool` | 是否可恢复 |
| `suggestion` | `str \| None` | 安全替代建议 |

### 6.7 TestFeedback（测试反馈）

| 字段 | 类型 | 说明 |
|------|------|------|
| `exit_code` | `int` | 测试退出码 |
| `passed_count` | `int` | 通过测试数 |
| `failed_count` | `int` | 失败测试数 |
| `skipped_count` | `int` | 跳过测试数 |
| `duration_ms` | `int` | 测试耗时 |
| `status` | `str` | `passed` / `failed` / `error` / `timeout` |
| `failed_tests` | `list[FailedTest]` | 失败测试详情（含断言、traceback、文件路径行号） |
| `previous_failed_count` | `int \| None` | 上一轮失败数 |
| `fixed_tests` | `list[str]` | 本轮修复的测试 |
| `new_failures` | `list[str]` | 本轮新增失败 |
| `unchanged_failures` | `list[str]` | 仍然失败的测试 |
| `progress_summary` | `str` | 人类可读的进展描述 |
| `hint` | `str \| None` | 给 LLM 的下一步提示 |

### 6.8 ContextPayload（LLM 上下文）

| 字段 | 类型 | 说明 |
|------|------|------|
| `system_prompt` | `str` | 系统提示和安全规则 |
| `task_description` | `str` | 当前任务目标 |
| `last_test_feedback` | `TestFeedback \| None` | 最近测试反馈 |
| `last_tool_result` | `ToolResult \| None` | 最近工具执行结果 |
| `last_guardrail_event` | `GuardrailEvent \| None` | 最近护栏事件 |
| `recent_diffs` | `list[str]` | 最近文件修改 diff 摘要 |
| `workspace_tree` | `str \| None` | 文件树摘要 |
| `history_summary` | `str \| None` | 早期对话压缩摘要 |
| `step_id` | `int` | 当前步骤 |
| `blocked_count` | `int` | 当前护栏计数 |
| `remaining_steps` | `int` | 剩余步数 |

### 6.9 SessionStatus（枚举）

```python
class SessionStatus(Enum):
    RUNNING = "running"
    SUCCESS = "success"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    TERMINATED_BY_GUARDRAIL = "terminated_by_guardrail"
    TIMEOUT = "timeout"
    FINISHED_WITHOUT_PASSING_TESTS = "finished_without_passing_tests"
    INVALID_ACTION_LIMIT_REACHED = "invalid_action_limit_reached"
```

---

## 7. 凭据与分发设计

### 7.1 凭据存储方案

| 优先级 | 方式 | 适用场景 |
|--------|------|----------|
| 1（推荐） | 系统 keyring（Windows Credential Manager / macOS Keychain / Linux Secret Service） | 个人开发机，最安全 |
| 2 | 环境变量 `SAFECODE_API_KEY` | CI/CD、Docker 容器 |
| 3（兜底） | `.env` 文件 | 本地开发快速测试 |

### 7.2 凭据生命周期

```
首次运行引导：safecode run（真实模式）→ 检测到 API Key 缺失
             → 自动提示 "未检测到 API Key，请运行 safecode auth set 录入"
             → 用户执行 safecode auth set → 隐藏输入 → 保存到 keyring
录入：safecode auth set → 隐藏输入 → 保存到 keyring
查询：safecode auth status → 显示 configured / missing（不回显明文）
清除：safecode auth clear → 从 keyring 删除
```

### 7.3 分发形态

| 形态 | 目标用户 | 命令 |
|------|----------|------|
| 源码 clone | 开发者/学生 | `git clone` → `pip install -e .` → 配置 API Key → `safecode run ...` |
| Docker 镜像（本地构建） | 老师/助教验收 | `docker build -t safecode-harness . && docker run --rm -p 8000:8000 safecode-harness` |
| Docker 镜像（公开 registry，可选） | 无需本地构建的用户 | `docker pull <registry>/safecode-harness && docker run --rm -p 8000:8000 safecode-harness` |
| 云部署（Render） | 在线验收 | 公网 URL 直接访问 WebUI（见 §7.6） |
| pip 包（可选） | 进阶用户 | `pip install safecode-harness` |

### 7.4 目标平台与仓库

- 主仓库：**NJU GitLab**（`https://git.nju.edu.cn/241880139/ai4se-safecode-harness`）
- CI：**GitLab CI**（`.gitlab-ci.yml`），必须包含 `unit-test` job
- 开发与测试：Windows / macOS / Linux
- 容器运行：Docker（Linux 容器）
- 云部署：Render（见 §7.6）

> 注：课程通用要求 §4.7 中存在"公开 GitHub 仓库"与"通过 NJU Git 仓库链接提交"的平台表述冲突。本项目以最终交付物清单（§5）中的 NJU Git 仓库为准，使用 NJU GitLab 作为主仓库，GitLab CI 作为 CI 平台。

### 7.5 Key 在目标机器上的安全配置

- 开发者：运行 `safecode auth set`，输入 Key，保存到系统 keyring。
- Docker 容器：通过 `-e SAFECODE_API_KEY=xxx` 传入环境变量。
- CI：通过 GitLab CI 的 masked variable 传入 `SAFECODE_API_KEY`。
- 明文 Key 不得出现在任何代码文件、配置文件、日志、git 历史中。

### 7.6 云部署（Render）

SafeCode Harness 的 WebUI 通过 Render 部署为公网可访问的服务，满足课程要求中"必须提供应用可访问的 WebUI 接口"的交付项。

**部署平台**：Render（免费额度），支持从 Git 仓库自动构建 Docker 镜像并部署。

**部署流程**：
1. 在 Render 中创建 Web Service，关联 NJU GitLab 仓库。
2. Render 自动检测 `Dockerfile`，构建镜像。
3. 服务启动命令：`uvicorn safecode.webui:app --host 0.0.0.0 --port $PORT`
4. 环境变量配置：
   - `SAFECODE_API_KEY`：通过 Render 的 secret 环境变量注入，不在 `Dockerfile` 或代码中硬编码。
   - `SAFECODE_BASE_URL`、`SAFECODE_MODEL`：可选，通过环境变量覆盖默认值。
5. Render 自动分配公网 URL（如 `https://safecode-harness.onrender.com`）。

**运行模式**：
- 部署后默认以 mock 模式运行 demo，不需要真实 API Key。
- 如需真实 LLM 模式，在 Render dashboard 中配置 `SAFECODE_API_KEY` 环境变量即可。
- mock 模式可脱离真实 API Key 独立运行，保证无 Key 时 WebUI 仍可访问和演示。

**安全注意事项**：
- API Key 通过 Render 的 secret 环境变量注入，不写入镜像或代码仓库。
- Render 提供的 HTTPS 保证传输安全。
- 云部署版本不挂载宿主机文件系统，Agent 工作区在容器内部的临时目录中。
- 这是演示部署，非生产环境；应在 README 中说明安全边界。

**验收标准**：部署后公网 URL 可访问 WebUI，mock 模式下至少一个 demo 可成功运行。

---

## 8. 技术选型与理由

| 技术 | 用途 | 选型理由 |
|------|------|----------|
| **Python 3.10+** | 主语言 | 生态丰富，AI4SE 课程主流语言 |
| **pytest** | 测试框架 | Python 标准测试框架，fixture 强大，mock 生态成熟 |
| **Typer** | CLI 框架 | 基于 Click，类型提示友好，适合构建 CLI 工具 |
| **FastAPI** | WebUI 后端 | 轻量、高性能、自动生成 OpenAPI 文档 |
| **Jinja2 + 原生 HTML/CSS** | WebUI 前端 | 轻量级，不引入 React/Vue 等重型框架；目标是观察 Agent 执行而非构建产品 |
| **Docker** | 分发与隔离 | 保证环境一致性，验收者无需配置 Python 环境 |
| **OpenAI-compatible API** | LLM 接入 | 通过 Token Hub 统一接入真实 LLM，兼容标准接口，支持模型替换 |
| **Python keyring** | 凭据存储 | 跨平台系统 keyring 封装，安全且易用 |
| **PyYAML** | 配置解析 | task.yaml 自然语言友好，可读性高 |
| **GitLab CI** | 持续集成 | 课程要求，与 NJU GitLab 集成 |

### 8.1 WebUI 与 Open Design 说明

WebUI 采用**轻量演示界面**，不引入完整 Open Design 流程。理由：
- 课程通用要求 §3.6 规定：凡涉及前端/UI，强烈推荐使用 Open Design，但纯 CLI/纯后端项目可豁免。
- SafeCode Harness 的 WebUI 并非产品级前端——它仅做任务选择和执行轨迹展示，不涉及复杂交互、设计系统或用户流程。
- 项目核心价值在 Harness 内核和可验证机制，不在 UI 复杂度。
- 使用 Jinja2 模板 + 原生 HTML/CSS + 少量 JavaScript 即可满足需求。
- 不做登录、用户管理、项目管理、文件在线编辑等复杂功能。
- WebUI 的目标是帮助用户**观察 Agent 在真实 LLM 或 mock 模式下的执行过程**，而非提供生产级 coding platform。

### 8.2 关于"不依赖现成 Agent 框架"的声明

SafeCode Harness **必须自己实现**以下核心机制，不能使用 LangChain AgentExecutor、AutoGen、CrewAI、LlamaIndex agent 或任何现成 coding agent runner 作为主循环：

- Agent 主循环（Agent Loop）
- LLM 抽象层（含 RealLLM 和 MockLLM）
- Action Parser（JSON 动作解析）
- Tool Dispatcher（工具分发）
- 治理护栏（Guardrail：路径、敏感文件、命令）
- 测试反馈回灌（Test Feedback Summarizer）
- 记忆/上下文管理（Context Builder）
- 停机判断（Stop Controller）

可以使用第三方库做**辅助功能**（如 Typer 做 CLI、FastAPI 做 Web、PyYAML 解析配置），但 agent harness 的核心决策逻辑必须由本项目自己实现。

### 8.3 Superpowers 与 SafeCode Harness 的关系

本项目使用 **Superpowers**（一个开发流程 Harness）来管理 SafeCode Harness 的整个开发周期：brainstorming 澄清需求、writing-plans 生成实施计划、TDD 驱动实现、code review 保证质量。Superpowers 是**开发 SafeCode Harness 时使用的元工具**，而 SafeCode Harness 是**最终交付的 Coding Agent 执行框架**。

简而言之：**使用一个 Harness（Superpowers）开发另一个 Harness（SafeCode Harness）。**

---

## 9. 验收标准

### 9.1 核心机制验收（Mock LLM 下确定性测试）

| 验收项 | 客观判定标准 | 验证方式 |
|--------|-------------|----------|
| Action Parser 正确解析 JSON action | 合法 JSON 返回 `ParsedAction`；非法 JSON 返回 `InvalidActionError` | 单元测试 |
| Tool Dispatcher 正确分发到 7 个工具 | 给定 `ParsedAction`，调用正确工具函数并返回 `ToolResult` | 单元测试 |
| 路径护栏拦截工作区外访问 | `read_file("../../etc/passwd")` 返回 `blocked`，`reason = path_outside_workspace` | 单元测试 |
| 敏感文件护栏拦截 `.env` 读取 | `read_file(".env")` 返回 `blocked`，`reason = sensitive_file_access` | 单元测试 |
| Shell 护栏拦截 `rm -rf` | `run_shell("rm -rf /")` 返回 `blocked`，`reason = dangerous_shell_command` | 单元测试 |
| 护栏计数达到 3 次终止会话 | Mock LLM 连续 3 次尝试危险动作后 `final_status = terminated_by_guardrail` | 集成测试 |
| Mock LLM scripted 模式按顺序返回 | 给定 action 列表，LLM 按序返回相同 action | 单元测试 |
| Mock LLM rule-based 模式根据上下文匹配 | 上下文中 `last_test_feedback.failed_test_names = ["test_add"]` 时返回 `edit_file` action | 单元测试 |
| 测试反馈闭环（mock 剧本） | Mock LLM 剧本：第 1 轮 run_tests 失败 → 反馈含 test_add → 第 2 轮 edit_file → 第 3 轮 run_tests 通过 | 集成测试 |
| 最大轮数达到后终止 | `max_iterations = 3`，3 轮后未通过测试 → `final_status = max_iterations_reached` | 集成测试 |
| 超时后终止 | `timeout_seconds = 1`，1 秒后 → `final_status = timeout` | 集成测试 |
| 连续无效动作 3 次后终止 | Mock LLM 返回 3 次非法 JSON → `final_status = invalid_action_limit_reached` | 集成测试 |

### 9.2 真实 LLM 验收（实际运行）

| 验收项 | 客观判定标准 | 验证方式 |
|--------|-------------|----------|
| 真实 LLM 连接 | 配置 API Key 后，`safecode run` 能成功调用 Token Hub API 并返回有效响应 | 手动运行 |
| 完整 coding 闭环 | 真实 LLM 在受限工作区中完成至少一个 coding task：读取代码 → 修改代码 → 运行 pytest → 根据反馈修正 → 测试通过 | 手动运行，`final_status = success` |
| 护栏拦截真实 LLM 危险动作 | 真实 LLM 尝试危险操作时被 Harness 护栏拦截（而非 LLM 自觉拒绝），`blocked` 事件记录到轨迹 | 手动运行或集成测试 |
| 反馈闭环驱动行为改变 | 真实 LLM 在收到测试失败反馈后，下一轮动作与上一轮不同（如从 `read_file` 变为 `edit_file`） | 观察执行轨迹 |

### 9.3 Demo 验收（机制演示）

SafeCode Harness 提供 3 个机制演示 demo，分别对应 A 项目 §A.6 要求的三个确定性行为。所有 demo 均可在 mock LLM 模式下无网络运行。

| Demo | 对应机制 | 模式 | 判定标准 |
|------|---------|------|----------|
| `demo guardrail-block` | **治理护栏**：拦截危险动作 | Mock | Mock LLM 连续尝试危险动作（如 `rm -rf`、读取 `.env`），被护栏拦截，`blocked_count >= 3`，`final_status = terminated_by_guardrail`。验证护栏是代码机制而非 prompt 约束。 |
| `demo fix-bug` | **测试反馈闭环**：失败反馈驱动行为改变 | Mock | Mock LLM 剧本：第 1 轮 `run_tests` 失败 → 反馈摘要含 `test_add` 失败信息 → 第 2 轮 `edit_file` 修改代码 → 第 3 轮 `run_tests` 通过。验证反馈回灌机制使 Agent 改变下一轮动作。 |
| `demo complete-function` | **重点维度协同**：护栏 + 反馈闭环协同工作 | Mock | Mock LLM 剧本：Agent 在受限工作区中补全函数骨架，过程中护栏放行合法操作，反馈闭环驱动多轮修正，最终 `final_status = success`。验证两个重点维度在同一会话中协同工作。 |
| `demo real-llm-fix-bug` | 真实 LLM 完整闭环 | Real | Agent 在真实 LLM 驱动下读取代码和测试 → 修改代码 → 运行 pytest → 测试通过，`final_status = success`。验证 Harness 在真实 LLM 下的完整闭环。 |

### 9.4 工程验收

| 验收项 | 判定标准 |
|--------|----------|
| `pytest` 全部通过 | 本地和 CI 中 `pytest` exit code 为 0 |
| 核心模块覆盖率 ≥ 80% | `pytest --cov=safecode --cov-report=term` |
| Docker 构建成功 | `docker build -t safecode-harness .` 无错误 |
| Docker 运行 WebUI | `docker run --rm -p 8000:8000 safecode-harness`，浏览器可访问 |
| `.gitlab-ci.yml` 的 `unit-test` job 通过 | 最后一次 CI pipeline 状态为 passed |
| 云部署 WebUI 可访问 | Render 公网 URL 可访问 WebUI，mock 模式下至少一个 demo 可成功运行 |
| 仓库无敏感凭据 | `git log -p` 中无 API Key 明文 |
| 文档完整 | SPEC.md、PLAN.md、SPEC_PROCESS.md、AGENT_LOG.md、REFLECTION.md、README.md 均存在且内容完整 |

---

## 10. 风险与未决问题

### 10.1 范围控制风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| WebUI 范围蔓延 | 花过多时间在 UI 上，削弱核心机制 | 严格限定 WebUI 为 Jinja2 模板 + 原生 HTML，不做登录/项目管理 |
| 工具数量膨胀 | 7 个工具已足够，新增工具增加测试和维护负担 | 新工具必须证明对核心机制有不可替代的价值 |
| 真实 LLM 行为不可控 | 相同 prompt 可能产生不同输出，导致手动 demo 不够稳定 | 验收核心机制以 mock LLM 测试为准；真实 LLM 仅验证"能跑通"即可 |

### 10.2 安全边界风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 代码层路径校验被绕过 | Agent 可能访问工作区外文件 | 多层防护：路径校验 + Docker 非 root + 临时工作区副本；SPEC 明确声明非生产级安全沙箱 |
| `run_shell` allowlist 不完整 | 危险命令可能漏网 | 默认最小 allowlist；用户扩展 allowlist 需自行承担风险；文档明确警告 |
| `.env` 文件被误提交 | API Key 泄露 | `.env` 加入 `.gitignore`；CI 中包含 secret 扫描；README 包含安全章节 |

### 10.3 实现风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Context Builder 上下文预算估算不准 | 超出 LLM token 限制导致调用失败 | 使用字符数估算 + 安全余量；首先裁剪历史对话，不裁剪安全规则 |
| pytest 输出解析不完整 | 反馈摘要丢失关键信息 | 处理解析失败降级方案：返回原始摘要文本 |
| 跨平台 keyring 兼容性 | 某些 Linux 发行版 keyring backend 不可用 | 自动降级到环境变量方案；文档说明各平台配置方式 |
| 管道式架构的扩展性 | 未来可能需要事件驱动 | 当前架构满足需求；SPEC 中记录此限制，未来可演进为事件驱动架构 |

### 10.4 未决问题与已知冲突

1. **课程文档平台表述冲突**：课程通用要求 §4.7 提及"公开 GitHub 仓库"，但 §5 最终交付物清单要求"通过 NJU Git 仓库链接提交"。本项目以 §5 为准，使用 NJU GitLab 作为主仓库，GitLab CI 作为 CI 平台。不影响交付。
2. **Docker 中 keyring 支持**：容器内 keyring 通常不可用，真实 LLM 模式在 Docker 中只能用环境变量。是否需要支持挂载 keyring socket？
3. **`edit_file` 的精确匹配语义**：`old_text` 按行还是按字符匹配？是否需要处理缩进/空白字符的容错？
4. **`search_content` 的 regex 能力边界**：是否支持复杂正则（如 lookahead/lookbehind）？最小实现先支持简单关键词和基础正则。
5. **WebUI 的实时更新**：WebUI 是轮询还是 SSE？最小实现先使用轮询。

---

## 11. 领域与机制设计（Coding Agent Harness 专属）

### 11.1 为什么选择 Coding 作为 Agent 领域

SafeCode Harness 选择 Coding 作为 Agent 领域，不是因为方便写 demo，而是因为软件开发提供了最清晰的 Agent 环境交互基础：

| 维度 | 软件开发中的具体体现 | 在 Harness 中的实现方式 |
|------|---------------------|------------------------|
| **工具** | 文件读写、代码搜索、测试执行、Shell 命令 | 7 个工具，每个有明确的输入/输出 schema |
| **反馈信号** | pytest 通过/失败、编译错误、运行错误、退出码 | `TestFeedback` 结构化对象，含失败测试名、断言、traceback |
| **危险动作** | 删除文件、访问敏感信息、执行危险命令 | 路径护栏 + 敏感文件护栏 + 命令 allowlist 护栏 |
| **可验证结果** | 测试通过即成功，失败即需修正 | `SessionStatus` 枚举，客观判定 |

这些要素都可以被 Harness 以**确定性代码**形式实现，而不依赖 LLM 的 prompt 约束或"自觉"。这是 SafeCode Harness 作为受控执行框架的核心价值。

### 11.2 Coding 领域的反馈信号

Coding Agent 的核心反馈信号是**自动化测试结果**（pytest exit code、通过/失败测试数、失败断言、traceback）。此外还有：
- **语法/编译错误**：`python -m py_compile` 或 `run_tests` 中的 SyntaxError。
- **工具执行错误**：文件不存在、权限不足、搜索无结果。
- **护栏拦截**：危险动作被拒绝的结构化错误。

### 11.3 危险动作

- **危险 Shell 命令**：`rm -rf /`、`del /F /S`、`format`、`shutdown`、`curl | sh`、`npm publish`、`git push --force`、`chmod 777` 等。
- **越权路径访问**：`../` 逃逸、绝对路径 `/etc/passwd`、符号链接指向工作区外。
- **敏感文件访问**：`.env`、`*.key`、`*.pem`、`secrets.json`、`id_rsa`、`.git/config`。

### 11.4 所需工具

7 个工具：`list_files`、`read_file`、`search_content`、`write_file`、`edit_file`、`run_tests`、`run_shell`（allowlist 受限）。

### 11.5 记忆需求

- **会话内上下文**：对话历史（带压缩，超出上下文预算时优先裁剪早期对话）、结构化执行轨迹（每轮 action、结果、护栏事件）、工作区状态摘要（文件树、最近 diff）、测试反馈历史对比（本轮 vs 上一轮）。
- **跨会话记忆**：每个会话结束后持久化 `session_trace.json`（含结构化摘要，不含完整对话历史）。新会话按需加载最近一次会话的摘要信息（如 `final_status`、最后一次测试结果），不全量加载旧对话。跨会话记忆按工作区隔离，每个工作区的 `.safecode/` 目录独立。

### 11.6 重点维度及其理由

SafeCode Harness 的重点维度是**治理护栏**和**测试反馈闭环**。

**治理护栏**：
- 现实意义：Coding Agent 执行代码和命令的能力本质上是危险的。LLM 可能被 prompt injection 诱导执行危险操作，仅靠 prompt 约束不可靠，必须在代码层面建立可审计、可验证的治理机制。
- 实现方式：路径护栏、敏感文件护栏、命令 allowlist 护栏都是确定性代码逻辑，不依赖 LLM 判断。给定输入，必然拦截或放行。
- 可验证性：每个护栏规则都可以在单元测试中独立验证，无需真实 LLM。

**测试反馈闭环**：
- 现实意义：Coding Agent 的核心能力是"写代码 → 运行测试 → 根据失败修正 → 再次测试"的闭环。这个闭环的质量直接决定了 Agent 能否完成任务。
- 实现方式：结构化摘要（不塞原始输出）+ 历史对比（感知进展）+ 下一步提示（引导方向），全部由 Harness 代码生成，在 mock LLM 下可验证。
- 可验证性：给定已知的 pytest 输出，`TestFeedback` 的每个字段都有确定值，可被断言。

### 11.7 确定性代码验证

所有核心机制均可通过以下方式在 mock LLM 下用确定性单元测试验证：

- **Agent Loop**：Scripted mock LLM 返回固定序列，验证主循环是否正确迭代、何时停止。
- **Action Parser**：给定合法/非法 JSON 字符串，验证解析结果。
- **Guardrail**：给定危险路径/命令，验证是否被拦截及拦截原因。
- **Test Feedback Summarizer**：给定已知 pytest 输出，验证摘要的每个字段。
- **Context Builder**：给定已知 Session 状态，验证构造的 ContextPayload 包含正确内容和优先级顺序。
- **Mock LLM (Rule-based)**：给定已知 ContextPayload，验证是否返回预期 action。
- **Stop Controller**：给定已知 Session 状态，验证是否触发正确的停止条件和 `final_status`。