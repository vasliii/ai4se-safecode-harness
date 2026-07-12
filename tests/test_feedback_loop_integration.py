from __future__ import annotations

import json
from pathlib import Path

from safecode.core.agent_loop import AgentLoop
from safecode.llm import LLMBackend
from safecode.models import ContextPayload, ParsedAction, RuntimeConfig, Session, SessionStatus, TaskConfig, TestFeedback, ToolResult


FAILED_THREE_OUTPUT = """
================================== FAILURES ===================================
________________________________ test_add __________________________________
E       assert 3 == 4

tests/test_calc.py:7: AssertionError
________________________________ test_sub __________________________________
E       assert 0 == 1

tests/test_calc.py:12: AssertionError
________________________________ test_mul __________________________________
E       assert 4 == 6

tests/test_calc.py:17: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_calc.py::test_add - assert 3 == 4
FAILED tests/test_calc.py::test_sub - assert 0 == 1
FAILED tests/test_calc.py::test_mul - assert 4 == 6
========================= 3 failed, 1 passed in 0.10s =========================
"""

FAILED_ONE_OUTPUT = """
================================== FAILURES ===================================
________________________________ test_mul __________________________________
E       assert 4 == 6

tests/test_calc.py:17: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_calc.py::test_mul - assert 4 == 6
========================= 1 failed, 3 passed in 0.08s =========================
"""

PASSED_OUTPUT = """
============================= test session starts =============================
collected 4 items

tests/test_calc.py ....                                                   [100%]

========================= 4 passed in 0.05s =========================
"""


class ScriptedLLM(LLMBackend):
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.contexts: list[ContextPayload] = []

    def query(self, context: ContextPayload) -> str:
        self.contexts.append(context)
        if not self.responses:
            return action("finish", {"summary": "done"})
        return self.responses.pop(0)


class ScriptedToolDispatcher:
    def __init__(self, results: list[ToolResult]) -> None:
        self.results = results
        self.actions: list[ParsedAction] = []

    def dispatch(self, action: ParsedAction, session: Session) -> ToolResult:
        self.actions.append(action)
        if action.tool != "run_tests":
            return ToolResult(tool=action.tool, success=True, data={})
        if not self.results:
            raise AssertionError("No scripted run_tests result left")
        return self.results.pop(0)


class RecordingSummarizer:
    def __init__(self) -> None:
        self.calls: list[tuple[ToolResult, int]] = []

    def summarize(self, tool_result: ToolResult, session: Session) -> TestFeedback:
        self.calls.append((tool_result, len(session.steps)))
        return TestFeedback(
            exit_code=0,
            passed_count=99,
            failed_count=0,
            skipped_count=0,
            duration_ms=1,
            status="passed",
            progress_summary="injected summarizer used",
        )


def make_session(workspace_root: Path) -> Session:
    return Session(
        session_id="session-feedback-loop",
        task_config=TaskConfig(
            id="task-feedback-loop",
            title="Feedback Loop",
            task_type="fix_bug",
            description="Fix tests using feedback",
            workspace_template="template",
            test_command="pytest",
        ),
        workspace_root=workspace_root,
        llm_backend="test",
    )


def action(tool: str, params: dict[str, object] | None = None) -> str:
    return json.dumps({"tool": tool, "params": params or {}})


def run_tests_result(stdout: str, exit_code: int) -> ToolResult:
    return ToolResult(
        tool="run_tests",
        success=True,
        data={"exit_code": exit_code, "stdout": stdout, "stderr": "", "command": ["pytest"]},
    )


def test_default_summarizer_parses_failed_and_passing_run_tests_outputs(tmp_path: Path) -> None:
    dispatcher = ScriptedToolDispatcher([
        run_tests_result(FAILED_THREE_OUTPUT, 1),
        run_tests_result(PASSED_OUTPUT, 0),
    ])

    result = AgentLoop(tool_dispatcher=dispatcher).run(
        make_session(tmp_path),
        ScriptedLLM([action("run_tests"), action("run_tests")]),
        RuntimeConfig(max_iterations=5),
    )

    assert result.final_status == SessionStatus.SUCCESS
    assert len(result.steps) == 2

    first_feedback = result.steps[0].test_feedback
    assert first_feedback is not None
    assert first_feedback.status == "failed"
    assert first_feedback.failed_count == 3
    assert first_feedback.passed_count == 1
    assert [failed.name for failed in first_feedback.failed_tests] == [
        "tests/test_calc.py::test_add",
        "tests/test_calc.py::test_sub",
        "tests/test_calc.py::test_mul",
    ]

    second_feedback = result.steps[1].test_feedback
    assert second_feedback is not None
    assert second_feedback.status == "passed"
    assert second_feedback.failed_count == 0
    assert second_feedback.passed_count == 4
    assert second_feedback.previous_failed_count == 3
    assert second_feedback.fixed_tests == [
        "tests/test_calc.py::test_add",
        "tests/test_calc.py::test_sub",
        "tests/test_calc.py::test_mul",
    ]
    assert second_feedback.progress_summary == "Previous run: 3 failed. Current: 0 failed. Fixed: 3 tests."


def test_second_run_tests_feedback_compares_with_previous_feedback(tmp_path: Path) -> None:
    dispatcher = ScriptedToolDispatcher([
        run_tests_result(FAILED_THREE_OUTPUT, 1),
        run_tests_result(FAILED_ONE_OUTPUT, 1),
    ])

    result = AgentLoop(tool_dispatcher=dispatcher).run(
        make_session(tmp_path),
        ScriptedLLM([action("run_tests"), action("read_file", {"path": "src/main.py"}), action("run_tests")]),
        RuntimeConfig(max_iterations=3),
    )

    assert len(result.steps) == 3
    assert result.steps[1].test_feedback is None
    feedback = result.steps[2].test_feedback
    assert feedback is not None
    assert feedback.status == "failed"
    assert feedback.previous_failed_count == 3
    assert feedback.fixed_tests == ["tests/test_calc.py::test_add", "tests/test_calc.py::test_sub"]
    assert feedback.unchanged_failures == ["tests/test_calc.py::test_mul"]
    assert feedback.new_failures == []
    assert feedback.progress_summary == "Previous run: 3 failed. Current: 1 failed. Fixed: 2 tests."
    assert feedback.hint == "Good progress. Continue fixing remaining failures."


def test_non_run_tests_tool_does_not_generate_test_feedback(tmp_path: Path) -> None:
    dispatcher = ScriptedToolDispatcher([])

    result = AgentLoop(tool_dispatcher=dispatcher).run(
        make_session(tmp_path),
        ScriptedLLM([action("read_file", {"path": "src/main.py"})]),
        RuntimeConfig(max_iterations=1),
    )

    assert result.steps[0].parsed_action == ParsedAction(tool="read_file", params={"path": "src/main.py"})
    assert result.steps[0].test_feedback is None


def test_explicit_summarizer_injection_is_preserved(tmp_path: Path) -> None:
    summarizer = RecordingSummarizer()
    tool_result = run_tests_result(FAILED_THREE_OUTPUT, 1)
    dispatcher = ScriptedToolDispatcher([tool_result])

    result = AgentLoop(tool_dispatcher=dispatcher, feedback_summarizer=summarizer).run(
        make_session(tmp_path),
        ScriptedLLM([action("run_tests")]),
        RuntimeConfig(max_iterations=5),
    )

    assert summarizer.calls == [(tool_result, 0)]
    assert result.final_status == SessionStatus.SUCCESS
    assert result.steps[0].test_feedback is not None
    assert result.steps[0].test_feedback.passed_count == 99
    assert result.steps[0].test_feedback.progress_summary == "injected summarizer used"

