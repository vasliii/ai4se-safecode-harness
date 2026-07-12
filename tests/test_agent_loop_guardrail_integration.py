from __future__ import annotations

import json
from pathlib import Path

from safecode.core.agent_loop import AgentLoop
from safecode.llm import LLMBackend
from safecode.models import ContextPayload, ParsedAction, RuntimeConfig, Session, SessionStatus, TaskConfig, ToolResult


class ScriptedLLM(LLMBackend):
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.contexts: list[ContextPayload] = []

    def query(self, context: ContextPayload) -> str:
        self.contexts.append(context)
        if not self.responses:
            return action("finish", {"summary": "done"})
        return self.responses.pop(0)


class RecordingToolDispatcher:
    def __init__(self) -> None:
        self.actions: list[ParsedAction] = []

    def dispatch(self, action: ParsedAction, session: Session) -> ToolResult:
        self.actions.append(action)
        return ToolResult(tool=action.tool, success=True, data={})


def make_session(workspace_root: Path) -> Session:
    return Session(
        session_id="session-guardrail-agent-loop",
        task_config=TaskConfig(
            id="task-guardrail-agent-loop",
            title="Guardrail Agent Loop",
            task_type="unit",
            description="Exercise guardrail integration",
            workspace_template="template",
            test_command="pytest",
        ),
        workspace_root=workspace_root,
        llm_backend="test",
    )


def action(tool: str, params: dict[str, object] | None = None) -> str:
    return json.dumps({"tool": tool, "params": params or {}})


def test_path_guard_blocks_action_and_increments_blocked_count(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    dispatcher = RecordingToolDispatcher()

    result = AgentLoop(tool_dispatcher=dispatcher).run(
        make_session(workspace),
        ScriptedLLM([action("read_file", {"path": "../outside"})]),
        RuntimeConfig(max_iterations=2, guardrail_threshold=1),
    )

    assert result.blocked_count == 1
    assert result.final_status == SessionStatus.TERMINATED_BY_GUARDRAIL
    assert result.steps[0].guardrail_result is not None
    assert result.steps[0].guardrail_result.reason == "path_outside_workspace"
    assert result.steps[0].tool_result is None
    assert dispatcher.actions == []


def test_three_path_guard_blocks_terminate_by_guardrail(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    responses = [action("read_file", {"path": "../outside"}) for _ in range(3)]

    result = AgentLoop(tool_dispatcher=RecordingToolDispatcher()).run(
        make_session(workspace),
        ScriptedLLM(responses),
        RuntimeConfig(max_iterations=10, guardrail_threshold=3),
    )

    assert result.blocked_count == 3
    assert result.final_status == SessionStatus.TERMINATED_BY_GUARDRAIL
    assert len(result.steps) == 3
    assert all(step.guardrail_result is not None for step in result.steps)
    assert all(step.tool_result is None for step in result.steps)


def test_sensitive_file_guard_blocks_env_read(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = AgentLoop(tool_dispatcher=RecordingToolDispatcher()).run(
        make_session(workspace),
        ScriptedLLM([action("read_file", {"path": ".env"})]),
        RuntimeConfig(max_iterations=2),
    )

    assert result.blocked_count == 1
    assert result.steps[0].guardrail_result is not None
    assert result.steps[0].guardrail_result.reason == "sensitive_file_access"
    assert result.steps[0].tool_result is None


def test_shell_guard_blocks_dangerous_shell_command(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = AgentLoop(tool_dispatcher=RecordingToolDispatcher()).run(
        make_session(workspace),
        ScriptedLLM([action("run_shell", {"command": "rm -rf /"})]),
        RuntimeConfig(max_iterations=2),
    )

    assert result.blocked_count == 1
    assert result.steps[0].guardrail_result is not None
    assert result.steps[0].guardrail_result.reason == "dangerous_shell_command"
    assert result.steps[0].tool_result is None


def test_safe_action_after_blocked_action_can_still_execute(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "main.py").write_text("print('ok')", encoding="utf-8")
    dispatcher = RecordingToolDispatcher()

    result = AgentLoop(tool_dispatcher=dispatcher).run(
        make_session(workspace),
        ScriptedLLM([
            action("read_file", {"path": "../outside"}),
            action("read_file", {"path": "src/main.py"}),
        ]),
        RuntimeConfig(max_iterations=2),
    )

    assert result.blocked_count == 1
    assert result.steps[0].guardrail_result is not None
    assert result.steps[0].tool_result is None
    assert result.steps[1].guardrail_result is None
    assert result.steps[1].tool_result is not None
    assert dispatcher.actions == [ParsedAction(tool="read_file", params={"path": "src/main.py"})]

