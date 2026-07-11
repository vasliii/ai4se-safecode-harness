from pathlib import Path

import pytest

from safecode.models import ParsedAction, Session, TaskConfig, ToolResult
from safecode.tools import Tool, ToolDispatcher


class EchoTool(Tool):
    name = "echo"

    def __init__(self) -> None:
        self.received_params: dict[str, object] | None = None
        self.received_session: Session | None = None

    def validate_params(self, params: dict) -> None:
        if "message" not in params:
            raise ValueError("message is required")

    def execute(self, params: dict, session: Session) -> ToolResult:
        self.validate_params(params)
        self.received_params = params
        self.received_session = session
        return ToolResult(tool=self.name, success=True, data={"message": params["message"]})


class FailingTool(Tool):
    name = "fail"

    def validate_params(self, params: dict) -> None:
        return None

    def execute(self, params: dict, session: Session) -> ToolResult:
        raise RuntimeError("tool exploded")


def make_session() -> Session:
    return Session(
        session_id="session-1",
        task_config=TaskConfig(
            id="task",
            title="Task",
            task_type="fix_bug",
            description="Fix a bug",
            workspace_template="examples/fix_bug",
            test_command="pytest",
        ),
        workspace_root=Path("workspace"),
        llm_backend="mock",
    )


def test_tool_is_abstract_base_class() -> None:
    with pytest.raises(TypeError):
        Tool()


def test_concrete_tool_can_execute() -> None:
    tool = EchoTool()
    session = make_session()

    result = tool.execute({"message": "hello"}, session)

    assert isinstance(tool, Tool)
    assert result == ToolResult(tool="echo", success=True, data={"message": "hello"})


def test_dispatcher_registers_tools_by_name() -> None:
    echo = EchoTool()
    failing = FailingTool()

    dispatcher = ToolDispatcher([echo, failing])

    assert dispatcher.registered_tools == {"echo": echo, "fail": failing}


def test_dispatcher_dispatches_to_correct_tool_and_passes_params() -> None:
    echo = EchoTool()
    dispatcher = ToolDispatcher([echo])
    session = make_session()
    action = ParsedAction(tool="echo", params={"message": "hello"})

    result = dispatcher.dispatch(action, session)

    assert result.success is True
    assert result.tool == "echo"
    assert result.data == {"message": "hello"}
    assert echo.received_params == {"message": "hello"}
    assert echo.received_session is session


def test_dispatcher_unknown_tool_returns_error_result() -> None:
    dispatcher = ToolDispatcher([])

    result = dispatcher.dispatch(ParsedAction(tool="missing", params={}), make_session())

    assert result.tool == "missing"
    assert result.success is False
    assert result.data is None
    assert result.error == "Unknown tool: missing"


def test_dispatcher_converts_tool_exceptions_to_error_result() -> None:
    dispatcher = ToolDispatcher([FailingTool()])

    result = dispatcher.dispatch(ParsedAction(tool="fail", params={}), make_session())

    assert result.tool == "fail"
    assert result.success is False
    assert result.data is None
    assert result.error == "tool exploded"


def test_dispatcher_records_duration_ms_for_success_and_failure() -> None:
    dispatcher = ToolDispatcher([EchoTool(), FailingTool()])

    success = dispatcher.dispatch(ParsedAction(tool="echo", params={"message": "hello"}), make_session())
    failure = dispatcher.dispatch(ParsedAction(tool="fail", params={}), make_session())

    assert isinstance(success.duration_ms, int)
    assert success.duration_ms >= 0
    assert isinstance(failure.duration_ms, int)
    assert failure.duration_ms >= 0


def test_dispatcher_returns_validation_errors_as_error_result() -> None:
    dispatcher = ToolDispatcher([EchoTool()])

    result = dispatcher.dispatch(ParsedAction(tool="echo", params={}), make_session())

    assert result.tool == "echo"
    assert result.success is False
    assert result.error == "message is required"