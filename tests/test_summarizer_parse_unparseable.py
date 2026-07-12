from safecode.feedback import TestFeedbackSummarizer
from safecode.models import Session, ToolResult
from safecode.models.task_config import TaskConfig


def make_session(tmp_path):
    task = TaskConfig(
        id="task",
        title="Task",
        task_type="fix_bug",
        description="Fix bug",
        workspace_template="template",
        test_command="pytest",
    )
    return Session("session", task, tmp_path, "mock")


def test_unparseable_output_returns_error_with_raw_summary(tmp_path):
    result = ToolResult(
        tool="run_tests",
        success=True,
        data={"exit_code": 2, "stdout": "nonsense without pytest summary", "stderr": "internal error"},
    )

    feedback = TestFeedbackSummarizer().summarize(result, make_session(tmp_path))

    assert feedback.status == "error"
    assert feedback.exit_code == 2
    assert feedback.passed_count == 0
    assert feedback.failed_count == 0
    assert feedback.skipped_count == 0
    assert feedback.failed_tests == []
    assert "nonsense without pytest summary" in feedback.progress_summary
    assert "internal error" in feedback.progress_summary

