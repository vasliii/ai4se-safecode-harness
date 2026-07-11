"""Read-only workspace content search tool."""

from pathlib import Path
import re
from typing import Any

from safecode.models import Session, ToolResult
from safecode.tools.base import Tool

IGNORED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}


class SearchContentTool(Tool):
    """Search workspace text files with a regular expression."""

    name = "search_content"

    def validate_params(self, params: dict) -> None:
        if "pattern" not in params:
            raise ValueError("pattern is required")

    def execute(self, params: dict, session: Session) -> ToolResult:
        try:
            self.validate_params(params)
            root = _workspace_path(session, params.get("path", "."))
            if not root.exists():
                return ToolResult(tool=self.name, success=False, error=f"Path not found: {params.get('path', '.')}")

            pattern = re.compile(str(params["pattern"]))
            file_pattern = params.get("file_pattern")
            matches = []
            for file_path in _iter_files(root, file_pattern):
                try:
                    lines = file_path.read_text(encoding="utf-8").splitlines()
                except UnicodeDecodeError:
                    continue
                for index, line in enumerate(lines, start=1):
                    if pattern.search(line):
                        matches.append(
                            {
                                "file": _relative_path(file_path, session.workspace_root),
                                "line": index,
                                "content": line,
                            }
                        )

            return ToolResult(tool=self.name, success=True, data={"matches": matches, "count": len(matches)})
        except re.error as exc:
            return ToolResult(tool=self.name, success=False, error=f"Invalid regex pattern: {exc}")
        except Exception as exc:
            return ToolResult(tool=self.name, success=False, error=str(exc))


def _iter_files(root: Path, file_pattern: Any) -> list[Path]:
    if root.is_file():
        candidates = [root]
    else:
        candidates = [path for path in root.rglob("*") if path.is_file()]

    files = [path for path in candidates if not _has_ignored_part(path)]
    if file_pattern:
        files = [path for path in files if path.match(str(file_pattern))]
    return sorted(files)


def _has_ignored_part(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def _workspace_path(session: Session, path_value: Any) -> Path:
    return (session.workspace_root / str(path_value)).resolve()


def _relative_path(path: Path, workspace_root: Path) -> str:
    return path.resolve().relative_to(workspace_root.resolve()).as_posix()