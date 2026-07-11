from __future__ import annotations

from safecode.tools import (
    EditFileTool,
    ListFilesTool,
    ReadFileTool,
    RunShellTool,
    RunTestsTool,
    SearchContentTool,
    Tool,
    ToolDispatcher,
    WriteFileTool,
    create_default_tools,
)


EXPECTED_TOOL_NAMES = {
    "list_files",
    "read_file",
    "search_content",
    "write_file",
    "edit_file",
    "run_tests",
    "run_shell",
}


def test_create_default_tools_returns_all_default_tools() -> None:
    tools = create_default_tools()

    assert len(tools) == 7
    assert {tool.name for tool in tools} == EXPECTED_TOOL_NAMES
    assert all(isinstance(tool, Tool) for tool in tools)


def test_default_tool_names_are_unique() -> None:
    names = [tool.name for tool in create_default_tools()]

    assert len(names) == len(set(names))


def test_create_default_tools_returns_new_instances_each_call() -> None:
    first = create_default_tools()
    second = create_default_tools()

    assert first is not second
    assert [type(tool) for tool in first] == [type(tool) for tool in second]
    assert all(left is not right for left, right in zip(first, second))


def test_tools_package_exports_registry_dispatcher_and_tool_classes() -> None:
    assert ToolDispatcher is not None
    assert ListFilesTool.name == "list_files"
    assert ReadFileTool.name == "read_file"
    assert SearchContentTool.name == "search_content"
    assert WriteFileTool.name == "write_file"
    assert EditFileTool.name == "edit_file"
    assert RunTestsTool.name == "run_tests"
    assert RunShellTool.name == "run_shell"
