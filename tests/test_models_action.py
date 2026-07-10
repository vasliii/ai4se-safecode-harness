from safecode.models import ParsedAction


def test_parsed_action_required_and_optional_fields():
    action = ParsedAction(tool="read_file", params={"path": "src/app.py"})

    assert action.tool == "read_file"
    assert action.params == {"path": "src/app.py"}
    assert action.thought_summary is None


def test_parsed_action_accepts_thought_summary():
    action = ParsedAction(tool="run_tests", params={}, thought_summary="check tests")

    assert action.thought_summary == "check tests"
