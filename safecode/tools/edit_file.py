"""Workspace-relative text editing tool."""

from pathlib import Path
from typing import Any

from safecode.models import Session, ToolResult
from safecode.tools.base import Tool


class EditFileTool(Tool):
    """Replace one unique text segment in a UTF-8 file inside the workspace."""

    name = "edit_file"

    def validate_params(self, params: dict) -> None:
        for field in ["path", "old_text", "new_text"]:
            if field not in params:
                raise ValueError(f"{field} is required")
        if params["old_text"] == "":
            raise ValueError("old_text must not be empty")

    def execute(self, params: dict, session: Session) -> ToolResult:
        try:
            self.validate_params(params)
            display_path = str(params["path"])
            target = _workspace_path(session, display_path)
            if not target.exists():
                return ToolResult(tool=self.name, success=False, error=f"File not found: {display_path}")
            if target.is_dir():
                return ToolResult(tool=self.name, success=False, error=f"Path is a directory: {display_path}")

            try:
                content = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return ToolResult(tool=self.name, success=False, error=f"File is not valid UTF-8 text: {display_path}")

            old_text = str(params["old_text"])
            new_text = str(params["new_text"])
            occurrences = content.count(old_text)
            if occurrences == 0:
                return ToolResult(tool=self.name, success=False, error="text not found")
            if occurrences > 1:
                return ToolResult(
                    tool=self.name,
                    success=False,
                    error="text found multiple times, must be unique",
                )

            target.write_text(content.replace(old_text, new_text, 1), encoding="utf-8")
            return ToolResult(tool=self.name, success=True, data={"path": display_path, "replaced": True})
        except Exception as exc:
            return ToolResult(tool=self.name, success=False, error=str(exc))


def _workspace_path(session: Session, path_value: Any) -> Path:
    return (session.workspace_root / str(path_value)).resolve()