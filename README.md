# SafeCode Harness

SafeCode Harness 是一个面向软件工程任务的最小但完整的 Coding Agent Harness。它让 LLM 在受控工作区中通过结构化 action 调用工具、读取反馈、接受护栏检查，并最终完成代码任务。

本项目不是普通聊天式 AI 应用。它的核心价值在于 Harness 侧的确定性机制：Pipeline Architecture、Action Parser、Guardrail、Tool Dispatcher、Test Feedback、Context Builder、Memory Trace、Configuration 和 CLI/WebUI。真实 LLM 只是其中一个后端；MockLLM 用于离线、确定性地验证同一套执行机制。

项目重点展示：

- 确定性 Guardrail：路径逃逸、敏感文件访问、危险 shell 命令由代码拦截。
- 测试反馈闭环：`run_tests` 输出被解析为结构化 `TestFeedback`，回灌到下一轮上下文。
- 上下文管理：每轮 LLM 调用由 `ContextBuilder` 构造受预算约束的 `ContextPayload`。
- MockLLM 验证：不依赖真实网络、真实 LLM 或 API Key，也能复现核心机制。

## 安装方式

前置要求：

- Python 3.10+
- Git
- 可选：Docker Desktop 或兼容 Docker 环境

安装：

```bash
git clone https://git.nju.edu.cn/241880139/ai4se-safecode-harness.git
cd ai4se-safecode-harness
python -m pip install -e .
```

开发环境可安装测试依赖：

```bash
python -m pip install -e .[dev]
```

安装后应能看到 CLI：

```bash
safecode --help
```

## 使用方法

查看帮助：

```bash
safecode --help
safecode auth --help
safecode demo --help
```

管理 API Key：

```bash
safecode auth set
safecode auth status
safecode auth clear
```

运行一个包含 `task.yaml` 的工作区：

```bash
safecode run --workspace <path>
safecode run --workspace <path> --mock
```

`run` 支持的常用选项：

```bash
safecode run --workspace <path> --max-iterations 5
safecode run --workspace <path> --model qwen3.7-max
safecode run --workspace <path> --timeout 300
safecode run --workspace <path> --keep-session
```

查看和运行内置 demo：

```bash
safecode demo list
safecode demo run guardrail_block --mock
safecode demo run fix_bug --mock
safecode demo run complete_function --mock
```

启动 WebUI：

```bash
safecode serve --host 0.0.0.0 --port 8000
```

启动后访问本机的 `http://localhost:8000/`，可以选择 demo 并以 mock 或 real 模式运行。

## API Key 配置

真实 LLM 模式需要 API Key。推荐使用系统 keyring：

```bash
safecode auth set
safecode auth status
```

`status` 只会显示 `configured` 或 `missing`，不会输出真实 Key。

也可以使用环境变量：

```bash
SAFECODE_API_KEY=<your-api-key>
SAFECODE_BASE_URL=https://njusehub.info/v1
SAFECODE_MODEL=qwen3.7-max
```

配置优先级由当前实现决定：

- API Key：keyring → `SAFECODE_API_KEY` → 当前目录 `.env` 中的 `SAFECODE_API_KEY`
- 运行时配置：CLI 参数 → `SAFECODE_*` 环境变量 → `config.yaml` → 内置默认值

Docker 中通常没有可用的系统 keyring，因此真实模式应通过环境变量注入：

```bash
docker run --rm -p 8000:8000 \
  -e SAFECODE_API_KEY=<your-api-key> \
  -e SAFECODE_BASE_URL=https://njusehub.info/v1 \
  -e SAFECODE_MODEL=qwen3.7-max \
  safecode-harness
```

Render 部署时，在 Render Dashboard 中配置环境变量。`SAFECODE_API_KEY` 应作为 secret 配置，不要写入代码、镜像或 `render.yaml` 明文。

## 分发与部署

构建 Docker 镜像：

```bash
docker build -t safecode-harness .
```

运行 WebUI：

```bash
docker run --rm -p 8000:8000 safecode-harness
```

验证首页：

```bash
curl http://localhost:8000/
```

在容器中查看 demo：

```bash
docker run --rm safecode-harness safecode demo list
```

使用 docker compose：

```bash
docker compose up --build
```

Render 部署步骤：

1. 将仓库连接到 Render。
2. 使用仓库中的 `render.yaml` 创建 Web Service。
3. 确认 runtime 使用 Docker，并指向仓库根目录的 `Dockerfile`。
4. 在 Render Dashboard 中配置 `SAFECODE_API_KEY`、`SAFECODE_BASE_URL`、`SAFECODE_MODEL`。
5. 部署完成后访问 Render 提供的服务地址，首页健康检查路径为 `/`。

已知限制：

- 本项目不是生产级沙箱。
- Docker 非 root 用户、临时工作区和 Guardrail 是防护层，但不能替代容器隔离、VM 隔离或操作系统权限隔离。
- 对真实不可信代码，应在容器、VM 或低权限账户中运行。

## 架构说明

SafeCode Harness 使用 Pipeline Architecture。核心执行链路如下：

```text
Session
  ↓
Context Builder
  ↓
LLM Backend
  ↓
Action Parser
  ↓
Guardrail
  ↓
Tool Dispatcher
  ↓
Tool Executor
  ↓
ToolResult / TestFeedback / GuardrailEvent
  ↓
StopController
```

模块地图：

- `safecode/core`：AgentLoop、StopController、SessionManager、WorkspaceManager 等核心编排。
- `safecode/guardrail`：PathGuard、SensitiveFileGuard、ShellGuard 和 Guardrail 编排器。
- `safecode/tools`：Tool 抽象类、ToolDispatcher、文件工具、测试工具和 shell 工具。
- `safecode/feedback`：TestFeedbackSummarizer，解析 pytest 输出并生成反馈摘要。
- `safecode/context`：ContextBuilder 和 MemoryManager。
- `safecode/llm`：LLMBackend 抽象接口、RealLLM、MockLLM、LLM factory。
- `safecode/config`：TaskConfigLoader 和 ConfigurationManager。
- `safecode/auth`：CredentialManager。
- `safecode/cli`：`safecode auth`、`run`、`demo`、`serve`。
- `safecode/webui`：FastAPI + Jinja2 的轻量 WebUI。
- `safecode/demos`：内置演示任务。

## 安全说明

威胁模型：

- LLM 可能输出错误、危险或越权 action。
- 任务代码可能包含测试失败、文件访问、shell 命令等交互。
- 用户可能在真实模式中配置 API Key。

凭据来源：

- 首选系统 keyring：`safecode auth set` 使用 keyring 保存 API Key。
- 环境变量：`SAFECODE_API_KEY` 适合 CI、Docker、Render。
- `.env`：仅作为本地兜底来源，不应提交到仓库。

Guardrail 机制：

- `path_outside_workspace`：拦截 `../`、绝对路径、指向工作区外部的符号链接。
- `sensitive_file_access`：拦截 `.env`、`.env.*`、`*.key`、`*.pem`、`secrets.json`、`id_rsa`、`.git/config`。
- `dangerous_shell_command`：拦截危险 shell 命令，并要求 `run_shell` 命令匹配 allowlist。

安全边界声明：

- SafeCode Harness 是课程级 Coding Agent Harness，不提供强隔离安全沙箱。
- Guardrail 是代码层治理机制，不能保证覆盖所有攻击或逃逸方式。
- 真实不可信代码必须放在容器、VM 或低权限系统账户中运行。
- 不要把真实 API Key、私钥、密码或敏感数据写入 demo、测试、日志、README 或 Git 历史。

## 开发与测试

运行完整测试：

```bash
python -m pytest -q -p no:cacheprovider
```

运行机制演示测试：

```bash
python -m pytest tests/demo/ -q -p no:cacheprovider
```

运行覆盖率：

```bash
python -m pytest --cov=safecode --cov-report=term --cov-report=html -p no:cacheprovider
```

覆盖率 HTML 报告会生成到 `htmlcov/`。

CI：

- 仓库包含 `.gitlab-ci.yml`。
- CI 运行单元测试和基础质量验证。
- Mock-only 测试不需要 API Key、真实 LLM 或网络访问。

## 目录结构

```text
.
├── safecode/
│   ├── auth/              # API Key 凭据管理
│   ├── cli/               # Typer CLI
│   ├── config/            # task.yaml 与运行时配置
│   ├── context/           # ContextBuilder 与 session trace
│   ├── core/              # AgentLoop、SessionManager、停止条件、工作区
│   ├── demos/             # 内置演示任务
│   ├── feedback/          # pytest 反馈解析
│   ├── guardrail/         # 路径、敏感文件、shell 护栏
│   ├── llm/               # RealLLM、MockLLM、Backend factory
│   ├── models/            # 核心 dataclass / enum 类型
│   ├── tools/             # Tool 基类、Dispatcher、内置工具
│   └── webui/             # FastAPI WebUI、模板和静态文件
├── tests/                 # 单元测试、集成测试、demo 机制测试
├── Dockerfile             # WebUI Docker 镜像
├── docker-compose.yml     # 本地 compose 部署
├── render.yaml            # Render Docker Web Service 配置
├── Procfile               # 非 Docker 启动命令
├── pyproject.toml         # 项目依赖、入口和测试配置
├── SPEC.md                # 项目规格
├── PLAN.md                # 实现计划
└── README.md              # 本文档
```

## 内置演示 Demos

查看 demo：

```bash
safecode demo list
```

### guardrail_block

展示 Guardrail 拦截危险动作。MockLLM 依次尝试危险 shell、敏感文件访问和路径逃逸，Harness 返回结构化 `GuardrailEvent`，最终达到护栏阈值并终止。

运行：

```bash
safecode demo run guardrail_block --mock
```

### fix_bug

展示测试反馈闭环。初始 `calculator.add` 有 bug，第一次 `run_tests` 失败；MockLLM 随后执行 `edit_file` 修复代码，再次运行测试后通过。

运行：

```bash
safecode demo run fix_bug --mock
```

### complete_function

展示合法文件操作与测试反馈协同。MockLLM 先列出文件、读取函数骨架、补全 `add` 函数，再运行测试并成功结束。

运行：

```bash
safecode demo run complete_function --mock
```

也可以直接运行 demo 机制测试：

```bash
python -m pytest tests/demo/ -q -p no:cacheprovider
```

## License and Authors

本项目是 AI4SE 课程项目，用于展示 Coding Agent Harness 的实现、验证与演示。

当前尚未指定开源许可证。