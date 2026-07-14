# SafeCode Harness （网页版演示页面仅供 demo 演示，真正使用该项目请使用命令行）

SafeCode Harness 是一个受控的 Coding Agent Harness，不是普通聊天机器人。它让 LLM 在隔离工作区中通过结构化 JSON action 调用工具，并由 Harness 负责解析、拦截、执行和停止判断。

核心执行闭环是：

```text
Context Builder
  -> LLM
  -> Action Parser
  -> Guardrail
  -> Tool Dispatcher
  -> run_tests / 文件工具 / shell 工具
  -> Test Feedback
  -> Stop Controller
```

也就是说，SafeCode Harness 不只是“把问题发给模型”。它会把任务、历史步骤、测试反馈、护栏事件和工作区信息组织成上下文，让 LLM 输出一个工具 action；然后 Harness 用确定性代码解析 action、检查安全规则、执行工具、读取 pytest 结果，并决定是否继续下一轮或结束。

SafeCode Harness 面向代码修复、函数补全和测试驱动修改任务。一次任务通常包含这些步骤：

1. Context Builder 构造 LLM 输入上下文。
2. LLM 返回一个 JSON action。
3. Action Parser 解析并校验 action。
4. Guardrail 拦截路径逃逸、敏感文件访问和危险 shell 命令。
5. Tool Dispatcher 执行文件读取、文件编辑、测试运行等工具。
6. run_tests 执行 pytest，并将输出交给 Test Feedback Summarizer。
7. Stop Controller 根据测试是否通过、最大轮数、护栏阻断次数等条件决定是否停止。

这种设计把“智能决策”交给 LLM，把“执行边界、工具调用、反馈解析、安全治理”放在 Harness 中实现。

## 项目功能

### 网页版演示页面中 Mock 模式与 Real 模式的区别与共同点

Mock 模式：

- 使用 MockLLM，不调用真实 LLM。
- 不需要 API Key，不消耗额度。

Real 模式：

- 使用真实 LLM API。
- 需要配置 API Key。
- 会消耗模型调用额度。

共同点：

- 均可执行内置的3份demo演示，并验证机制正确。

### 普通用户如何用 SafeCode 修复或补全自己的 Python 项目

使用 CLI 来完成自己的项目。完整流程如下：

```bash
git clone https://git.nju.edu.cn/241880139/ai4se-safecode-harness.git
cd ai4se-safecode-harness
python -m pip install -e ".[dev]"
safecode --help
```

配置真实 LLM API Key：

```bash
safecode auth set
safecode auth status
```

进入你自己的任务目录。这个目录应包含待完成代码、测试文件和 `task.yaml`：

```bash
cd /path/to/your/python/task
```

以下面的模板为例创建 `task.yaml`：

```yaml
id: fix_my_python_bug
title: "Fix my Python bug"
task_type: fix_bug
description: "Fix the failing pytest tests in this project. Read the code, make the smallest correct change, run tests, and finish only after tests pass."
workspace_template: .
test_command: pytest
max_iterations: 10
timeout_seconds: 300
allowed_tools:
  - list_files
  - read_file
  - search_content
  - edit_file
  - write_file
  - run_tests
  - run_shell
  - finish
```

运行 Real 模式：

```bash
safecode run --workspace . --keep-session
```

`--keep-session` 会保留 SafeCode 创建的临时 session workspace。运行结束后，根据 CLI 输出的 session workspace 路径检查完成的代码，再手动复制、diff 或合并回你的原项目。

如果只是验证 CLI 路径，不想调用真实 LLM，可以运行：

```bash
safecode run --workspace . --mock --keep-session
```

但要注意：Mock 模式不会智能修复你的任意代码，它主要用于机制演示和测试。

### 网页版内置 demo 演示页面 （https://safecode-harness.onrender.com/）

网页版 demo 演示页面主要用于运行内置 demo 和查看 Execution Trace。它可以展示每一步 action、工具结果、测试状态和护栏事件。

注意：

- 网页版 demo 演示页面不是完整的在线上传项目平台。
- 网页版 demo 演示页面当前主要面向 `safecode/demos/` 下的内置 demo。
- 完成自己的代码请使用 CLI：`safecode run --workspace . --keep-session`。

## 安装方式

推荐安装开发依赖，因为 CLI、demo 和 Docker 内部测试工具都依赖 pytest：

```bash
git clone https://git.nju.edu.cn/241880139/ai4se-safecode-harness.git
cd ai4se-safecode-harness
python -m pip install -e ".[dev]"
```

确认安装：

```bash
safecode --help
python -m pytest --version
```

## CLI 常用命令

认证：

```bash
safecode auth set
safecode auth status
safecode auth clear
```

运行任务：

```bash
safecode run --workspace <path>
safecode run --workspace <path> --mock
safecode run --workspace <path> --keep-session
safecode run --workspace <path> --max-iterations 5
safecode run --workspace <path> --timeout 300
safecode run --workspace <path> --model qwen3.7-max
```

## API Key 配置

Real 模式需要 API Key。推荐使用系统 keyring：

```bash
safecode auth set
```

也可以使用环境变量：

```bash
SAFECODE_API_KEY="<your-api-key>"
SAFECODE_BASE_URL="<your-base-url>"
SAFECODE_MODEL="<your-model>"
```

API Key 获取优先级：

1. 系统 keyring
2. 环境变量 `SAFECODE_API_KEY`
3. 当前目录 `.env` 文件中的 `SAFECODE_API_KEY`

不要把真实 API Key 写入 README、task.yaml、Dockerfile、render.yaml、测试文件、日志或 Git 历史。

## 架构说明

```text
Session
  -> Context Builder
  -> LLMBackend
  -> ActionParser
  -> Guardrail
  -> ToolDispatcher
  -> ToolResult / TestFeedback / GuardrailEvent
  -> StopController
```

关键模块：

- `safecode/core`：AgentLoop、SessionManager、WorkspaceManager、StopController。
- `safecode/context`：ContextBuilder、MemoryManager。
- `safecode/llm`：LLMBackend、RealLLM、MockLLM、factory。
- `safecode/core/action_parser.py`：解析 LLM 返回的 JSON action。
- `safecode/guardrail`：路径、敏感文件和 shell 命令护栏。
- `safecode/tools`：文件工具、测试工具、shell 工具和 ToolDispatcher。
- `safecode/feedback`：pytest 输出解析和测试反馈摘要。
- `safecode/config`：task.yaml 和运行时配置加载。
- `safecode/cli`：命令行入口。
- `safecode/webui`：FastAPI + Jinja2 WebUI。
- `safecode/demos`：内置 demo 任务。

## 目录结构

```text
.
├── safecode/
│   ├── auth/
│   ├── cli/
│   ├── config/
│   ├── context/
│   ├── core/
│   ├── demos/
│   ├── feedback/
│   ├── guardrail/
│   ├── llm/
│   ├── models/
│   ├── tools/
│   └── webui/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── Procfile
├── pyproject.toml
├── SPEC.md
├── PLAN.md
└── README.md
```

## 安全边界说明

SafeCode Harness 是课程级和实验级 Coding Agent Harness，不是生产级安全沙箱。

它提供的安全机制包括：

- PathGuard：阻止访问 workspace 外的路径。
- SensitiveFileGuard：阻止访问 `.env`、`*.key`、`*.pem`、`secrets.json`、`id_rsa`、`.git/config` 等敏感文件。
- ShellGuard：阻止危险 shell 命令，并限制 `run_shell` 到 allowlist。

限制：

- 不能保证拦截所有恶意代码或所有 shell 绕过方式。
- 不替代 Docker、VM、低权限用户或操作系统级隔离。
- 对真实不可信项目，应在容器、VM 或低权限环境中运行。
- Real 模式会调用真实 LLM，不保证一定修复所有 bug。

## 整体说明

本项目是 AI4SE 课程项目，用于展示 Coding Agent Harness 的实现、验证和演示。