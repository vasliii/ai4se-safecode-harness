from datetime import datetime
from pathlib import Path

from safecode.models import (
    ContextPayload,
    ParsedAction,
    Session,
    SessionStatus,
    SessionStep,
    TaskConfig,
)


def make_task_config():
    return TaskConfig(
        id="fix_bug",
        title="Fix bug",
        task_type="fix_bug",
        description="Fix a bug",
        workspace_template="examples/fix_bug",
        test_command="pytest",
    )


def make_context():
    return ContextPayload(
        system_prompt="system",
        task_description="task",
        step_id=0,
        blocked_count=0,
        remaining_steps=10,
    )


def test_session_status_values():
    assert SessionStatus.RUNNING.value == "running"
    assert SessionStatus.SUCCESS.value == "success"
    assert SessionStatus.MAX_ITERATIONS_REACHED.value == "max_iterations_reached"
    assert SessionStatus.TERMINATED_BY_GUARDRAIL.value == "terminated_by_guardrail"
    assert SessionStatus.TIMEOUT.value == "timeout"
    assert SessionStatus.FINISHED_WITHOUT_PASSING_TESTS.value == "finished_without_passing_tests"
    assert SessionStatus.INVALID_ACTION_LIMIT_REACHED.value == "invalid_action_limit_reached"


def test_session_step_is_frozen_and_contains_structured_fields():
    step = SessionStep(
        step_id=0,
        llm_request=make_context(),
        llm_response='{"tool":"finish","params":{}}',
        parsed_action=ParsedAction(tool="finish", params={}),
        timestamp=datetime(2026, 1, 1),
    )

    assert step.guardrail_result is None
    assert step.tool_result is None
    assert step.test_feedback is None


def test_session_defaults():
    session = Session(
        session_id="session-1",
        task_config=make_task_config(),
        workspace_root=Path("/tmp/workspace"),
        llm_backend="mock",
    )

    assert session.steps == []
    assert session.blocked_count == 0
    assert session.invalid_action_count == 0
    assert session.end_time is None
    assert session.final_status == SessionStatus.RUNNING
