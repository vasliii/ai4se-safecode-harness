from datetime import datetime, timedelta
from pathlib import Path

from safecode.core import StopController
from safecode.models import (
    ContextPayload,
    ParsedAction,
    RuntimeConfig,
    Session,
    SessionStatus,
    SessionStep,
    TaskConfig,
    TestFeedback,
    ToolResult,
)


def make_task_config() -> TaskConfig:
    return TaskConfig(
        id="task",
        title="Task",
        task_type="fix_bug",
        description="Fix a bug",
        workspace_template="examples/fix_bug",
        test_command="pytest",
    )


def make_context(step_id: int = 0) -> ContextPayload:
    return ContextPayload(
        system_prompt="system",
        task_description="task",
        step_id=step_id,
        blocked_count=0,
        remaining_steps=10,
    )


def make_session(**overrides: object) -> Session:
    values = {
        "session_id": "session-1",
        "task_config": make_task_config(),
        "workspace_root": Path("workspace"),
        "llm_backend": "mock",
    }
    values.update(overrides)
    return Session(**values)


def make_test_feedback(status: str, exit_code: int) -> TestFeedback:
    failed_count = 0 if status == "passed" else 1
    passed_count = 1 if status == "passed" else 0
    return TestFeedback(
        exit_code=exit_code,
        passed_count=passed_count,
        failed_count=failed_count,
        skipped_count=0,
        duration_ms=10,
        status=status,
    )


def make_step(
    step_id: int = 0,
    action: ParsedAction | None = None,
    tool_result: ToolResult | None = None,
    test_feedback: TestFeedback | None = None,
) -> SessionStep:
    return SessionStep(
        step_id=step_id,
        llm_request=make_context(step_id),
        llm_response="{}",
        parsed_action=action,
        tool_result=tool_result,
        test_feedback=test_feedback,
    )


def test_stops_when_last_run_tests_passed() -> None:
    session = make_session(
        steps=[
            make_step(
                action=ParsedAction(tool="run_tests", params={}),
                tool_result=ToolResult(tool="run_tests", success=True, data={"exit_code": 0}),
                test_feedback=make_test_feedback(status="passed", exit_code=0),
            )
        ]
    )

    assert StopController().should_stop(session, RuntimeConfig()) == (True, SessionStatus.SUCCESS)


def test_stops_when_max_iterations_reached() -> None:
    session = make_session(steps=[make_step(step_id=0), make_step(step_id=1)])

    assert StopController().should_stop(session, RuntimeConfig(max_iterations=2)) == (
        True,
        SessionStatus.MAX_ITERATIONS_REACHED,
    )


def test_stops_when_guardrail_threshold_reached() -> None:
    session = make_session(blocked_count=3)

    assert StopController().should_stop(session, RuntimeConfig(guardrail_threshold=3)) == (
        True,
        SessionStatus.TERMINATED_BY_GUARDRAIL,
    )


def test_stops_when_session_times_out() -> None:
    session = make_session(start_time=datetime.now() - timedelta(seconds=11))

    assert StopController().should_stop(session, RuntimeConfig(timeout_seconds=10)) == (
        True,
        SessionStatus.TIMEOUT,
    )


def test_finish_with_passing_tests_returns_success() -> None:
    session = make_session(
        steps=[
            make_step(
                step_id=0,
                action=ParsedAction(tool="run_tests", params={}),
                tool_result=ToolResult(tool="run_tests", success=True, data={"exit_code": 0}),
                test_feedback=make_test_feedback(status="passed", exit_code=0),
            ),
            make_step(step_id=1, action=ParsedAction(tool="finish", params={"summary": "done"})),
        ]
    )

    assert StopController().should_stop(session, RuntimeConfig()) == (True, SessionStatus.SUCCESS)


def test_finish_without_passing_tests_stops_with_failure_status() -> None:
    session = make_session(
        steps=[
            make_step(
                step_id=0,
                action=ParsedAction(tool="run_tests", params={}),
                tool_result=ToolResult(tool="run_tests", success=False, data={"exit_code": 1}),
                test_feedback=make_test_feedback(status="failed", exit_code=1),
            ),
            make_step(step_id=1, action=ParsedAction(tool="finish", params={"summary": "stopping"})),
        ]
    )

    assert StopController().should_stop(session, RuntimeConfig()) == (
        True,
        SessionStatus.FINISHED_WITHOUT_PASSING_TESTS,
    )


def test_stops_when_invalid_action_limit_reached() -> None:
    session = make_session(invalid_action_count=3)

    assert StopController().should_stop(session, RuntimeConfig()) == (
        True,
        SessionStatus.INVALID_ACTION_LIMIT_REACHED,
    )


def test_running_session_returns_running() -> None:
    session = make_session(steps=[make_step(action=ParsedAction(tool="read_file", params={"path": "app.py"}))])

    assert StopController().should_stop(session, RuntimeConfig()) == (False, SessionStatus.RUNNING)


def test_empty_session_returns_running() -> None:
    session = make_session()

    assert StopController().should_stop(session, RuntimeConfig()) == (False, SessionStatus.RUNNING)