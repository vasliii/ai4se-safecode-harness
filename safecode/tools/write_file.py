"""Workspace-relative file writing tool."""

from pathlib import Path
from typing import Any

from safecode.models import Session, ToolResult
from safecode.tools.base import Tool


class WriteFileTool(Tool):
    """Create or overwrite a UTF-8 text file inside the workspace."""

    name = "write_file"

    def validate_params(self, params: dict) -> None:
        if "path" not in params:
            raise ValueError("path is required")
        if "content" not in params:
            raise ValueError("content is required")

    def execute(self, params: dict, session: Session) -> ToolResult:
        try:
            self.validate_params(params)
            display_path = str(params["path"])
            content = str(params["content"])
            target = _workspace_path(session, display_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ToolResult(
                tool=self.name,
                success=True,
                data={"path": display_path, "bytes_written": len(content.encode("utf-8"))},
            )
        except Exception as exc:
            return ToolResult(tool=self.name, success=False, error=str(exc))


def _workspace_path(session: Session, path_value: Any) -> Path:
    return (session.workspace_root / str(path_value)).resolve()