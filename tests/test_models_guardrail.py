from safecode.models import GuardrailEvent


def test_guardrail_event_reasons_are_supported():
    for reason in [
        "dangerous_shell_command",
        "path_outside_workspace",
        "sensitive_file_access",
    ]:
        event = GuardrailEvent(
            reason=reason,
            tool="run_shell",
            action_summary="blocked action",
            recoverable=True,
        )

        assert event.blocked is True
        assert event.reason == reason
        assert event.suggestion is None
