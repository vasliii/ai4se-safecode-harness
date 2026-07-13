"""Demo: guardrails block dangerous actions before tools execute."""

from __future__ import annotations

from safecode.models import SessionStatus

from .conftest import run_demo_session


def test_guardrail_block_demo_terminates_after_three_blocked_actions():
    session = run_demo_session("guardrail_block")

    assert session.final_status is SessionStatus.TERMINATED_BY_GUARDRAIL
    assert session.blocked_count >= 3

    guardrail_steps = [step for step in session.steps if step.guardrail_result is not None]
    reasons = {step.guardrail_result.reason for step in guardrail_steps}

    assert "dangerous_shell_command" in reasons
    assert "sensitive_file_access" in reasons
    assert "path_outside_workspace" in reasons
    assert all(step.tool_result is None for step in guardrail_steps)
