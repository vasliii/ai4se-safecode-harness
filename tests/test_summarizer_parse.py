from pathlib import Path

import pytest

from safecode.feedback import TestFeedbackSummarizer
from safecode.models import Session, ToolResult
from safecode.models.task_config import TaskConfig


PASSING_OUTPUT = """
============================= test session starts =============================
collected 3 items

tests/test_calc.py ...                                                    [100%]

========================= 3 passed in 0.12s =========================
"""

FAILING_OUTPUT = """
============================= test session starts =============================
collected 2 items

tests/test_calc.py F.                                                     [100%]

================================== FAILURES ===================================
________________________________ test_add __________________________________

    def test_add():
>       assert add(1, 2) == 4
E       assert 3 == 4
E        +  where 3 = add(1, 2)

tests/test_calc.py:7: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_calc.py::test_add - assert 3 == 4
========================= 1 failed, 1 passed in 0.08s =========================
"""

MIXED_OUTPUT = """
============================= test session starts =============================
collected 5 items

tests/test_calc.py Fs...                                                  [100%]

=================== 1 failed, 3 passed, 1 skipped in 0.42s ====================
"""


def make_session(tmp_path: Path) -> Session:
    task = TaskConfig(
        id="task",
        title="Task",
        task_type="fix_bug",
        description="Fix bug",
        workspace_template="template",
        test_command="pytest",
    )
    return Session(
        session_id="session",
        task_config=task,
        workspace_root=tmp_path,
        llm_backend="mock",
    )


def run_tests_result(stdout: str, exit_code: int = 0, stderr: str = "") -> ToolResult:
    return ToolResult(
        tool="run_tests",
        success=True,
        data={
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "command": ["pytest"],
        },
    )


def test_summarizer_parses_passing_pytest_output(tmp_path):
    feedback = TestFeedbackSummarizer().summarize(
        run_tests_result(PASSING_OUTPUT, exit_code=0), make_session(tmp_path)
    )

    assert feedback.status == "passed"
    assert feedback.exit_code == 0
    assert feedback.passed_count == 3
    assert feedback.failed_count == 0
    assert feedback.skipped_count == 0
    assert feedback.duration_ms == 120
    assert feedback.failed_tests == []
    assert feedback.hint == "All tests pass. Consider calling finish."


def test_summarizer_parses_failed_pytest_output(tmp_path):
    feedback = TestFeedbackSummarizer().summarize(
        run_tests_result(FAILING_OUTPUT, exit_code=1), make_session(tmp_path)
    )

    assert feedback.status == "failed"
    assert feedback.passed_count == 1
    assert feedback.failed_count == 1
    assert feedback.skipped_count == 0
    assert [failed.name for failed in feedback.failed_tests] == ["tests/test_calc.py::test_add"]
    failed = feedback.failed_tests[0]
    assert failed.assertion == "assert 3 == 4"
    assert failed.file_path == "tests/test_calc.py"
    assert failed.line_number == 7
    assert "assert add(1, 2) == 4" in failed.traceback


def test_summarizer_parses_mixed_counts(tmp_path):
    feedback = TestFeedbackSummarizer().summarize(
        run_tests_result(MIXED_OUTPUT, exit_code=1), make_session(tmp_path)
    )

    assert feedback.status == "failed"
    assert feedback.passed_count == 3
    assert feedback.failed_count == 1
    assert feedback.skipped_count == 1
    assert feedback.duration_ms == 420

