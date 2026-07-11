"""Read-only text file reader tool."""

from pathlib import Path
from typing import Any

from safecode.models import Session, ToolResult
from safecode.tools.base import Tool

MAX_READ_BYTES = 100 * 1024


class ReadFileTool(Tool):
    """Read a UTF-8 text file from a workspace-relative path."""

    name = "read_file"

    def validate_params(self, params: dict) -> None:
        if "path" not in params:
            raise ValueError("path is required")

    def execute(self, params: dict, session: Session) -> ToolResult:
        try:
            self.validate_params(params)
            target = _workspace_path(session, params["path"])
            display_path = str(params["path"])
            if not target.exists():
                return ToolResult(tool=self.name, success=False, error=f"File not found: {display_path}")
            if target.is_dir():
                return ToolResult(tool=self.name, success=False, error=f"Path is a directory: {display_path}")
            if target.stat().st_size > MAX_READ_BYTES:
                return ToolResult(tool=self.name, success=False, error=f"File too large: {display_path}")

            try:
                content = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return ToolResult(tool=self.name, success=False, error=f"File is not valid UTF-8 text: {display_path}")

            selected = _slice_lines(content, params.get("start_line"), params.get("end_line"))
            return ToolResult(
                tool=self.name,
                success=True,
                data={"content": selected, "path": display_path, "lines": _line_count(selected)},
            )
        except Exception as exc:
            return ToolResult(tool=self.name, success=False, error=str(exc))


def _slice_lines(content: str, start_line: Any, end_line: Any) -> str:
    if start_line is None and end_line is None:
        return content

    lines = content.splitlines(keepends=True)
    start = max(int(start_line or 1) - 1, 0)
    end = int(end_line) if end_line is not None else len(lines)
    return "".join(lines[start:end])


def _line_count(content: str) -> int:
    if content == "":
        return 0
    return len(content.splitlines())


def _workspace_path(session: Session, path_value: Any) -> Path:
    return (session.workspace_root / str(path_value)).resolve()