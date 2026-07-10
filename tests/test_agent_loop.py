import json
from pathlib import Path

from safecode.llm import LLMBackend, LLMError
from safecode.models import (
    ContextPayload,
    GuardrailEvent,
    ParsedAction,
    RuntimeConfig,
    Session,
    SessionStatus,
    TaskConfig,
    TestFeedback,
    ToolResult,
)
from safecode.core.agent_loop import AgentLoop


class ScriptedLLM(LLMBackend):
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.contexts: list[ContextPayload] = []

    def query(self, context: ContextPayload) -> str:
        self.contexts.append(context)
        if not self.responses:
            return json.dumps({"tool": "finish", "params": {}})
        return self.responses.pop(0)


class FailingLLM(LLMBackend):
    def query(self, context: ContextPayload) -> str:
        raise LLMError("backend failed")


class RecordingToolDispatcher:
    def __init__(self) -> None:
        self.actions: list[ParsedAction] = []

    def dispatch(self, action: ParsedAction, session: Session) -> ToolResult:
        self.actions.append(action)
        data = {"exit_code": 0} if action.tool == "run_tests" else {}
        return ToolResult(tool=action.tool, success=True, data=data)


class PassingFeedbackSummarizer:
    def summarize(self, tool_result: ToolResult, session: Session) -> TestFeedback:
        return TestFeedback(
            exit_code=0,
            passed_count=1,
            failed_count=0,
            skipped_count=0,
            duration_ms=1,
            status="passed",
        )


class BlockingGuardrail:
    def check(self, action: ParsedAction, session: Session) -> GuardrailEvent | None:
        return GuardrailEvent(
            reason="dangerous_shell_command",
            tool=action.tool,
            action_summary="blocked by test",
            recoverable=True,
        )


class ImmediateStopController:
    def should_stop(self, session: Session, config: RuntimeConfig) -> tuple[bool, SessionStatus]:
        return True, SessionStatus.TIMEOUT


def make_session() -> Session:
    return Session(
        session_id="session-1",
        task_config=TaskConfig(
            id="task",
            title="Task",
            task_type="fix_bug",
            description="Fix the bug",
            workspace_template="examples/fix_bug",
            test_command="pytest",
        ),
        workspace_root=Path("workspace"),
        llm_backend="stub",
    )


def action(tool: str, params: dict[str, object] | None = None) -> str:
    return json.dumps({"tool": tool, "params": params or {}})


def test_agent_loop_stops_successfully_after_passing_tests() -> None:
    session = make_session()
    llm = ScriptedLLM([action("run_tests")])
    dispatcher = RecordingToolDispatcher()

    result = AgentLoop(
        tool_dispatcher=dispatcher,
        feedback_summarizer=PassingFeedbackSummarizer(),
    ).run(session, llm, RuntimeConfig(max_iterations=3))

    assert result.final_status == SessionStatus.SUCCESS
    assert len(result.steps) == 1
    assert result.steps[0].parsed_action == ParsedAction(tool="run_tests", params={})
    assert result.steps[0].tool_result == ToolResult(tool="run_tests", success=True, data={"exit_code": 0})
    assert result.steps[0].test_feedback is not None
    assert dispatcher.actions == [ParsedAction(tool="run_tests", params={})]


def test_agent_loop_continues_after_non_terminal_action() -> None:
    session = make_session()
    llm = ScriptedLLM([action("read_file", {"path": "app.py"}), action("finish", {"summary": "stop"})])

    result = AgentLoop(tool_dispatcher=RecordingToolDispatcher()).run(
        session,
        llm,
        RuntimeConfig(max_iterations=5),
    )

    assert [step.parsed_action.tool for step in result.steps if step.parsed_action] == ["read_file", "finish"]
    assert result.final_status == SessionStatus.FINISHED_WITHOUT_PASSING_TESTS
    assert len(llm.contexts) == 2
    assert llm.contexts[1].step_id == 1


def test_stop_controller_status_is_applied_before_querying_llm() -> None:
    session = make_session()
    llm = ScriptedLLM([action("read_file", {"path": "app.py"})])

    result = AgentLoop(stop_controller=ImmediateStopController()).run(session, llm, RuntimeConfig())

    assert result.final_status == SessionStatus.TIMEOUT
    assert result.steps == []
    assert llm.contexts == []


def test_session_steps_record_llm_request_response_and_action() -> None:
    session = make_session()
    response = action("read_file", {"path": "app.py"})

    result = AgentLoop(tool_dispatcher=RecordingToolDispatcher()).run(
        session,
        ScriptedLLM([response]),
        RuntimeConfig(max_iterations=1),
    )

    step = result.steps[0]
    assert step.step_id == 0
    assert step.llm_request.task_description == "Fix the bug"
    assert step.llm_request.remaining_steps == 1
    assert step.llm_response == response
    assert step.parsed_action == ParsedAction(tool="read_file", params={"path": "app.py"})
    assert step.tool_result == ToolResult(tool="read_file", success=True, data={})


def test_agent_loop_stops_at_max_iterations() -> None:
    session = make_session()
    llm = ScriptedLLM([action("read_file", {"path": "a.py"}), action("read_file", {"path": "b.py"})])

    result = AgentLoop(tool_dispatcher=RecordingToolDispatcher()).run(
        session,
        llm,
        RuntimeConfig(max_iterations=2),
    )

    assert result.final_status == SessionStatus.MAX_ITERATIONS_REACHED
    assert len(result.steps) == 2


def test_llm_error_is_recorded_and_session_reaches_stop_condition() -> None:
    session = make_session()

    result = AgentLoop().run(session, FailingLLM(), RuntimeConfig(max_iterations=1))

    assert result.final_status == SessionStatus.MAX_ITERATIONS_REACHED
    assert len(result.steps) == 1
    assert result.steps[0].parsed_action is None
    assert result.steps[0].tool_result is not None
    assert result.steps[0].tool_result.success is False
    assert result.steps[0].tool_result.tool == "llm"
    assert "backend failed" in result.steps[0].tool_result.error


def test_guardrail_block_is_recorded_and_counted() -> None:
    session = make_session()

    result = AgentLoop(guardrail=BlockingGuardrail()).run(
        session,
        ScriptedLLM([action("run_shell", {"command": "git status"})]),
        RuntimeConfig(max_iterations=1),
    )

    assert result.blocked_count == 1
    assert result.steps[0].guardrail_result is not None
    assert result.steps[0].tool_result is None