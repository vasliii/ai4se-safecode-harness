from safecode.feedback import TestFeedbackSummarizer
from safecode.models import Session, ToolResult
from safecode.models.task_config import TaskConfig


def make_session(tmp_path):
    task = TaskConfig("task", "Task", "fix_bug", "Fix bug", "template", "pytest")
    return Session("session", task, tmp_path, "mock")


def test_long_traceback_is_truncated(tmp_path):
    long_trace = "\n".join(f"    line {index}: details" for index in range(300))
    output = f"""
================================== FAILURES ===================================
________________________________ test_big_failure __________________________________
{long_trace}
E       AssertionError: very long failure

tests/test_big.py:99: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_big.py::test_big_failure - AssertionError: very long failure
========================= 1 failed in 0.10s =========================
"""
    result = ToolResult("run_tests", True, {"exit_code": 1, "stdout": output, "stderr": ""})

    feedback = TestFeedbackSummarizer().summarize(result, make_session(tmp_path))

    assert len(feedback.failed_tests[0].traceback) <= 1200
    assert "[truncated]" in feedback.failed_tests[0].traceback

