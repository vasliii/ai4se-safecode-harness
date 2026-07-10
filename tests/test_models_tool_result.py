from safecode.models import ToolResult


def test_tool_result_success_defaults():
    result = ToolResult(tool="list_files", success=True, data={"files": []}, duration_ms=12)

    assert result.tool == "list_files"
    assert result.success is True
    assert result.data == {"files": []}
    assert result.error is None
    assert result.duration_ms == 12


def test_tool_result_error_defaults():
    result = ToolResult(tool="read_file", success=False, error="missing", duration_ms=1)

    assert result.data is None
    assert result.error == "missing"
