"""Default tool registry for SafeCode Harness."""

from __future__ import annotations

from safecode.tools.base import Tool
from safecode.tools.edit_file import EditFileTool
from safecode.tools.list_files import ListFilesTool
from safecode.tools.read_file import ReadFileTool
from safecode.tools.run_shell import RunShellTool
from safecode.tools.run_tests import RunTestsTool
from safecode.tools.search_content import SearchContentTool
from safecode.tools.write_file import WriteFileTool


def create_default_tools() -> list[Tool]:
    """Create a fresh list of all default SafeCode tools."""
    return [
        ListFilesTool(),
        ReadFileTool(),
        SearchContentTool(),
        WriteFileTool(),
        EditFileTool(),
        RunTestsTool(),
        RunShellTool(),
    ]
