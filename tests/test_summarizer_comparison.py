from safecode.feedback import TestFeedbackSummarizer
from safecode.models import (
    ContextPayload,
    FailedTest,
    Session,
    SessionStep,
    TestFeedback,
    ToolResult,
)
from safecode.models.task_config import TaskConfig


def make_session(tmp_path, previous_feedback=None):
    task = TaskConfig(
        id="task",
        title="Task",
        task_type="fix_bug",
        description="Fix bug",
        workspace_template="template",
        test_command="pytest",
    )
    session = Session("session", task, tmp_path, "mock")
    if previous_feedback is not None:
        session.steps.append(
            SessionStep(
                step_id=0,
                llm_request=ContextPayload("sys", "task", 0, 0, 10),
                llm_response="{}",
                test_feedback=previous_feedback,
            )
        )
    return session


def feedback_with_failures(names):
    return TestFeedback(
        exit_code=1 if names else 0,
        passed_count=0,
        failed_count=len(names),
        skipped_count=0,
        duration_ms=0,
        status="failed" if names else "passed",
        failed_tests=[FailedTest(name=name) for name in names],
    )


def run_result(summary, exit_code=1):
    failed_lines = "\n".join(f"FAILED tests/test_calc.py::{name} - assert failed" for name in summary["failed_names"])
    output = f"""
================================== FAILURES ===================================
{failed_lines}
========================= {summary['failed_count']} failed, {summary['passed_count']} passed in 0.10s =========================
"""
    return ToolResult("run_tests", True, {"exit_code": exit_code, "stdout": output, "stderr": ""})


def test_first_run_has_no_history_comparison(tmp_path):
    feedback = TestFeedbackSummarizer().summarize(
        run_result({"failed_names": ["test_add"], "failed_count": 1, "passed_count": 1}),
        make_session(tmp_path),
    )

    assert feedback.previous_failed_count is None
    assert feedback.fixed_tests == []
    assert feedback.new_failures == []
    assert feedback.unchanged_failures == []
    assert feedback.progress_summary == "First run: 1 failed."
    assert feedback.hint == "Same failures persist. Try a different approach."


def test_failure_count_decrease_reports_fixed_tests(tmp_path):
    previous = feedback_with_failures(["tests/test_calc.py::test_add", "tests/test_calc.py::test_sub"])
    feedback = TestFeedbackSummarizer().summarize(
        run_result({"failed_names": ["test_sub"], "failed_count": 1, "passed_count": 2}),
        make_session(tmp_path, previous),
    )

    assert feedback.previous_failed_count == 2
    assert feedback.fixed_tests == ["tests/test_calc.py::test_add"]
    assert feedback.new_failures == []
    assert feedback.unchanged_failures == ["tests/test_calc.py::test_sub"]
    assert feedback.progress_summary == "Previous run: 2 failed. Current: 1 failed. Fixed: 1 tests."
    assert feedback.hint == "Good progress. Continue fixing remaining failures."


def test_new_failures_are_reported(tmp_path):
    previous = feedback_with_failures(["tests/test_calc.py::test_add"])
    feedback = TestFeedbackSummarizer().summarize(
        run_result({"failed_names": ["test_add", "test_mul"], "failed_count": 2, "passed_count": 1}),
        make_session(tmp_path, previous),
    )

    assert feedback.previous_failed_count == 1
    assert feedback.new_failures == ["tests/test_calc.py::test_mul"]
    assert feedback.unchanged_failures == ["tests/test_calc.py::test_add"]
    assert feedback.hint == "Failures increased. Review recent changes."


def test_unchanged_failures_are_reported(tmp_path):
    previous = feedback_with_failures(["tests/test_calc.py::test_add"])
    feedback = TestFeedbackSummarizer().summarize(
        run_result({"failed_names": ["test_add"], "failed_count": 1, "passed_count": 1}),
        make_session(tmp_path, previous),
    )

    assert feedback.previous_failed_count == 1
    assert feedback.fixed_tests == []
    assert feedback.new_failures == []
    assert feedback.unchanged_failures == ["tests/test_calc.py::test_add"]
    assert feedback.progress_summary == "Previous run: 1 failed. Current: 1 failed. Fixed: 0 tests."
    assert feedback.hint == "Same failures persist. Try a different approach."


def test_first_run_all_passed_progress_summary(tmp_path):
    output = "========================= 2 passed in 0.10s ========================="
    result = ToolResult("run_tests", True, {"exit_code": 0, "stdout": output, "stderr": ""})

    feedback = TestFeedbackSummarizer().summarize(result, make_session(tmp_path))

    assert feedback.progress_summary == "All tests passed on first run."
    assert feedback.hint == "All tests pass. Consider calling finish."

