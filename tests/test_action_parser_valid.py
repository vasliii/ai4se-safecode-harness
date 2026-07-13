import json

from safecode.core import ActionParser


def test_parse_pure_json_action() -> None:
    action = ActionParser().parse('{"tool": "run_tests", "params": {}, "thought_summary": "Run tests first."}')

    assert action.tool == "run_tests"
    assert action.params == {}
    assert action.thought_summary == "Run tests first."


def test_parse_markdown_json_code_block_action() -> None:
    response = '```json\n{"tool": "read_file", "params": {"path": "src/calculator.py"}}\n```'

    action = ActionParser().parse(response)

    assert action.tool == "read_file"
    assert action.params == {"path": "src/calculator.py"}


def test_parse_explanation_then_json_action() -> None:
    response = (
        'I will run the tests first.\n'
        '{"tool": "run_tests", "params": {}, "thought_summary": "Run tests first."}'
    )

    action = ActionParser().parse(response)

    assert action.tool == "run_tests"
    assert action.params == {}


def test_parse_text_around_json_action() -> None:
    response = (
        'Here is the next action:\n'
        '{"tool": "read_file", "params": {"path": "src/calculator.py"}, "thought_summary": "Inspect file."}\n'
        "I will wait for the result."
    )

    action = ActionParser().parse(response)

    assert action.tool == "read_file"
    assert action.params == {"path": "src/calculator.py"}


def test_parse_uses_first_json_object_when_multiple_exist() -> None:
    response = "\n".join(
        [
            json.dumps({"tool": "run_tests", "params": {}}),
            json.dumps({"tool": "finish", "params": {"summary": "done"}}),
        ]
    )

    action = ActionParser().parse(response)

    assert action.tool == "run_tests"
    assert action.params == {}
