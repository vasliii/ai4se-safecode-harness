"""Demo: failing pytest feedback drives a deterministic bug fix."""

from __future__ import annotations

from safecode.models import SessionStatus

from .conftest import run_demo_session

OLD_ADD = '''def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of two numbers."""
    return a - b'''

NEW_ADD = '''def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of two numbers."""
    return a + b'''


def test_fix_bug_demo_shows_feedback_loop_to_success():
    session = run_demo_session(
        "fix_bug",
        [
            {"tool": "run_tests", "params": {}},
            {
                "tool": "edit_file",
                "params": {
                    "path": "src/calculator.py",
                    "old_text": OLD_ADD,
                    "new_text": NEW_ADD,
                },
            },
            {"tool": "run_tests", "params": {}},
            {"tool": "finish", "params": {"summary": "Fixed calculator.add."}},
        ],
    )

    assert session.final_status is SessionStatus.SUCCESS
    assert not [step for step in session.steps if step.guardrail_result is not None]

    test_steps = [step for step in session.steps if step.parsed_action and step.parsed_action.tool == "run_tests"]
    assert len(test_steps) == 2
    assert test_steps[0].test_feedback is not None
    assert test_steps[0].test_feedback.status == "failed"
    assert test_steps[0].test_feedback.failed_count >= 1
    assert test_steps[1].test_feedback is not None
    assert test_steps[1].test_feedback.status == "passed"
    assert test_steps[1].test_feedback.failed_count == 0
    assert test_steps[1].test_feedback.previous_failed_count == test_steps[0].test_feedback.failed_count
    assert test_steps[1].test_feedback.fixed_tests or "Good progress" in (test_steps[1].test_feedback.progress_summary or "")
