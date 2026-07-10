from safecode.models import ContextPayload


def test_context_payload_allows_optional_fields_to_be_none():
    context = ContextPayload(
        system_prompt="system",
        task_description="task",
        step_id=2,
        blocked_count=1,
        remaining_steps=8,
    )

    assert context.last_test_feedback is None
    assert context.last_tool_result is None
    assert context.last_guardrail_event is None
    assert context.recent_diffs == []
    assert context.workspace_tree is None
    assert context.history_summary is None
