"""Demo: legal file operations and test feedback complete a function."""

from __future__ import annotations

from safecode.models import SessionStatus

from .conftest import run_demo_session


def test_complete_function_demo_uses_legal_file_actions_and_test_feedback():
    session = run_demo_session("complete_function")

    assert session.final_status is SessionStatus.SUCCESS
    assert not [step for step in session.steps if step.guardrail_result is not None]

    actions = [step.parsed_action.tool for step in session.steps if step.parsed_action is not None]
    assert actions[:4] == ["list_files", "read_file", "edit_file", "run_tests"]

    test_step = next(step for step in session.steps if step.parsed_action and step.parsed_action.tool == "run_tests")
    assert test_step.test_feedback is not None
    assert test_step.test_feedback.status == "passed"
    assert test_step.test_feedback.failed_count == 0
