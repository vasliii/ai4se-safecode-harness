from pathlib import Path

from safecode.context import ContextBuilder
from safecode.models import (
    ContextPayload,
    FailedTest,
    GuardrailEvent,
    ParsedAction,
    RuntimeConfig,
    Session,
    SessionStep,
    TaskConfig,
    TestFeedback,
    ToolResult,
)


def make_session(workspace_root: Path) -> Session:
    return Session(
        session_id="session-context-history",
        task_config=TaskConfig("task", "Task", "fix_bug", "Fix bug", "template", "pytest"),
        workspace_root=workspace_root,
        llm_backend="mock",
    )


def request(step_id: int) -> ContextPayload:
    return ContextPayload("system", "task", step_id, 0, 10)


def test_context_uses_most_recent_test_feedback(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    old_feedback = TestFeedback(1, 0, 2, 0, 10, "failed", [FailedTest("test_old")])
    new_feedback = TestFeedback(1, 1, 1, 0, 12, "failed", [FailedTest("test_new")])
    session.steps.extend([
        SessionStep(0, request(0), "{}", test_feedback=old_feedback),
        SessionStep(1, request(1), "{}", test_feedback=new_feedback),
    ])

    context = ContextBuilder(RuntimeConfig()).build(session)

    assert context.last_test_feedback == new_feedback


def test_context_uses_most_recent_tool_result(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    old_result = ToolResult("read_file", True, {"content": "old"})
    new_result = ToolResult("run_tests", True, {"exit_code": 1, "stdout": "failed"})
    session.steps.extend([
        SessionStep(0, request(0), "{}", tool_result=old_result),
        SessionStep(1, request(1), "{}", tool_result=new_result),
    ])

    context = ContextBuilder(RuntimeConfig()).build(session)

    assert context.last_tool_result == new_result


def test_context_uses_most_recent_guardrail_event(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    first = GuardrailEvent("path_outside_workspace", "read_file", "../outside", True)
    latest = GuardrailEvent("dangerous_shell_command", "run_shell", "rm -rf /", True)
    session.steps.extend([
        SessionStep(0, request(0), "{}", guardrail_result=first),
        SessionStep(1, request(1), "{}", guardrail_result=latest),
    ])

    context = ContextBuilder(RuntimeConfig()).build(session)

    assert context.last_guardrail_event == latest


def test_history_summary_mentions_actions_results_guardrails_and_feedback(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    feedback = TestFeedback(1, 1, 1, 0, 20, "failed", [FailedTest("test_add")])
    guardrail = GuardrailEvent("sensitive_file_access", "read_file", "read .env", True)
    session.steps.extend([
        SessionStep(
            0,
            request(0),
            "{}",
            parsed_action=ParsedAction("run_tests", {}),
            tool_result=ToolResult("run_tests", True, {"exit_code": 1}),
            test_feedback=feedback,
        ),
        SessionStep(
            1,
            request(1),
            "{}",
            parsed_action=ParsedAction("read_file", {"path": ".env"}),
            guardrail_result=guardrail,
        ),
    ])

    summary = ContextBuilder(RuntimeConfig()).build(session).history_summary

    assert "step 0" in summary
    assert "action=run_tests" in summary
    assert "tool=run_tests success=True" in summary
    assert "tests=failed failed=1" in summary
    assert "guardrail=sensitive_file_access" in summary
