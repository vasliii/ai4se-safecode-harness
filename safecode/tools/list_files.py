"""Read-only directory listing tool."""

from pathlib import Path
from typing import Any

from safecode.models import Session, ToolResult
from safecode.tools.base import Tool

IGNORED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}


class ListFilesTool(Tool):
    """List files under a workspace-relative path."""

    name = "list_files"

    def validate_params(self, params: dict) -> None:
        if "path" not in params:
            raise ValueError("path is required")

    def execute(self, params: dict, session: Session) -> ToolResult:
        try:
            self.validate_params(params)
            target = _workspace_path(session, params["path"])
            if not target.exists():
                return ToolResult(tool=self.name, success=False, error=f"Path not found: {params['path']}")
            if not target.is_dir():
                return ToolResult(tool=self.name, success=False, error=f"Path is not a directory: {params['path']}")

            recursive = params.get("recursive", True)
            files = _list_files(target, session.workspace_root, recursive=recursive)
            tree = "\n".join(files)
            return ToolResult(tool=self.name, success=True, data={"tree": tree, "files": files})
        except Exception as exc:
            return ToolResult(tool=self.name, success=False, error=str(exc))


def _list_files(target: Path, workspace_root: Path, *, recursive: bool) -> list[str]:
    if recursive:
        paths = [path for path in target.rglob("*") if path.is_file() and not _has_ignored_part(path)]
    else:
        paths = [path for path in target.iterdir() if path.is_file() and not _has_ignored_part(path)]
    return sorted(_relative_path(path, workspace_root) for path in paths)


def _has_ignored_part(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def _workspace_path(session: Session, path_value: Any) -> Path:
    return (session.workspace_root / str(path_value)).resolve()


def _relative_path(path: Path, workspace_root: Path) -> str:
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()