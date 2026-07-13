import json

import pytest

from safecode.core import ActionParser, InvalidActionError


def assert_invalid(response: str, reason: str) -> None:
    with pytest.raises(InvalidActionError) as exc_info:
        ActionParser().parse(response)

    assert exc_info.value.reason == reason


def test_rejects_unknown_tool_after_json_extraction() -> None:
    response = 'Use this:\n{"tool": "unknown", "params": {}}'

    assert_invalid(response, "unknown_tool")


def test_rejects_invalid_params_after_json_extraction() -> None:
    response = json.dumps({"tool": "read_file", "params": {"path": 123}})

    assert_invalid(response, "invalid_params")


def test_no_json_object_is_invalid_json() -> None:
    assert_invalid("I will run tests but forgot the JSON action.", "invalid_json")


def test_extracted_malformed_json_is_invalid_json() -> None:
    assert_invalid('Next action: {"tool": "run_tests", "params": ', "invalid_json")
