import json

import pytest

from safecode.core import ActionParser, InvalidActionError, TOOL_SCHEMAS
from safecode.models import ParsedAction


VALID_ACTIONS = [
    ("list_files", {"path": "."}),
    ("list_files", {"path": ".", "recursive": True}),
    ("read_file", {"path": "src/app.py"}),
    ("read_file", {"path": "src/app.py", "start_line": 1, "end_line": 20}),
    ("search_content", {"pattern": "TODO"}),
    ("search_content", {"pattern": "TODO", "path": "src", "file_pattern": "*.py"}),
    ("write_file", {"path": "src/app.py", "content": "print('ok')\n"}),
    ("edit_file", {"path": "src/app.py", "old_text": "bad", "new_text": "good"}),
    ("run_tests", {}),
    ("run_tests", {"args": "tests/test_app.py"}),
    ("run_shell", {"command": "git status"}),
    ("finish", {}),
    ("finish", {"summary": "done"}),
]


def assert_invalid(response: str, reason: str) -> None:
    parser = ActionParser()

    with pytest.raises(InvalidActionError) as exc_info:
        parser.parse(response)

    assert exc_info.value.reason == reason


@pytest.mark.parametrize(("tool", "params"), VALID_ACTIONS)
def test_parse_valid_json_actions(tool: str, params: dict[str, object]) -> None:
    parser = ActionParser()
    response = json.dumps({"tool": tool, "params": params})

    action = parser.parse(response)

    assert isinstance(action, ParsedAction)
    assert action.tool == tool
    assert action.params == params
    assert action.thought_summary is None


def test_parse_markdown_json_code_block() -> None:
    parser = ActionParser()
    response = '```json\n{"tool": "read_file", "params": {"path": "README.md"}}\n```'

    action = parser.parse(response)

    assert action == ParsedAction(tool="read_file", params={"path": "README.md"})


def test_parse_preserves_optional_thought_summary() -> None:
    parser = ActionParser()
    response = json.dumps(
        {
            "tool": "run_shell",
            "params": {"command": "git status"},
            "thought_summary": "Check current repository status.",
        }
    )

    action = parser.parse(response)

    assert action.thought_summary == "Check current repository status."


def test_tool_schemas_exports_expected_tools() -> None:
    assert set(TOOL_SCHEMAS) == {
        "list_files",
        "read_file",
        "search_content",
        "write_file",
        "edit_file",
        "run_tests",
        "run_shell",
        "finish",
    }


@pytest.mark.parametrize("response", ["", "not json", "{bad json"])
def test_parse_invalid_json_raises_reason(response: str) -> None:
    assert_invalid(response, "invalid_json")


@pytest.mark.parametrize(
    "payload",
    [
        {"params": {}},
        {"tool": "list_files"},
        {"tool": "list_files", "params": None},
    ],
)
def test_parse_missing_fields_raises_reason(payload: dict[str, object]) -> None:
    assert_invalid(json.dumps(payload), "missing_fields")


def test_parse_unknown_tool_raises_reason() -> None:
    assert_invalid(json.dumps({"tool": "unknown", "params": {}}), "unknown_tool")


@pytest.mark.parametrize(
    "payload",
    [
        {"tool": "read_file", "params": {}},
        {"tool": "read_file", "params": {"path": "x.py", "start_line": "1"}},
        {"tool": "list_files", "params": {"path": ".", "recursive": "yes"}},
        {"tool": "search_content", "params": {"pattern": 123}},
        {"tool": "write_file", "params": {"path": "x.py"}},
        {"tool": "edit_file", "params": {"path": "x.py", "old_text": "old"}},
        {"tool": "run_tests", "params": {"args": ["tests"]}},
        {"tool": "run_shell", "params": {"command": 123}},
        {"tool": "finish", "params": {"summary": False}},
    ],
)
def test_parse_invalid_params_raises_reason(payload: dict[str, object]) -> None:
    assert_invalid(json.dumps(payload), "invalid_params")