from safecode.feedback import TestFeedbackSummarizer
from safecode.models import Session, ToolResult
from safecode.models.task_config import TaskConfig


def make_session(tmp_path):
    task = TaskConfig("task", "Task", "fix_bug", "Fix bug", "template", "pytest")
    return Session("session", task, tmp_path, "mock")


def test_timeout_tool_result_returns_timeout_status(tmp_path):
    result = ToolResult(
        tool="run_tests",
        success=False,
        data={"exit_code": None, "stdout": "", "stderr": ""},
        error="pytest timed out after 60 seconds",
    )

    feedback = TestFeedbackSummarizer().summarize(result, make_session(tmp_path))

    assert feedback.status == "timeout"
    assert feedback.exit_code == -1
    assert feedback.hint == "Same failures persist. Try a different approach."
    assert "pytest timed out" in feedback.progress_summary

