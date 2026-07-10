from safecode.models import FailedTest, TestFeedback


def test_test_feedback_defaults_and_failed_test_details():
    failed = FailedTest(
        name="test_add",
        assertion="assert 1 == 2",
        traceback="Traceback...",
        file_path="tests/test_calc.py",
        line_number=10,
    )
    feedback = TestFeedback(
        exit_code=1,
        passed_count=1,
        failed_count=1,
        skipped_count=0,
        duration_ms=42,
        status="failed",
        failed_tests=[failed],
        progress_summary="1 failed",
    )

    assert feedback.failed_tests == [failed]
    assert feedback.previous_failed_count is None
    assert feedback.fixed_tests == []
    assert feedback.new_failures == []
    assert feedback.unchanged_failures == []
    assert feedback.hint is None
