"""Path guardrail for workspace boundary enforcement."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from safecode.models import GuardrailEvent


class PathGuard:
    """Validate that a requested path stays inside the workspace root."""

    def check(self, path: str | None, workspace_root: Path) -> Optional[GuardrailEvent]:
        if path is None:
            return None

        path_value = str(path)
        if path_value.strip() == "":
            return None

        root = workspace_root.resolve()
        requested = Path(path_value)
        if requested.is_absolute():
            return self._blocked(path_value)

        target = (root / requested).resolve()
        if self._is_within_workspace(target, root):
            return None
        return self._blocked(path_value)

    def _is_within_workspace(self, target: Path, workspace_root: Path) -> bool:
        try:
            target.relative_to(workspace_root)
        except ValueError:
            return False
        return True

    def _blocked(self, path: str) -> GuardrailEvent:
        return GuardrailEvent(
            reason="path_outside_workspace",
            tool="path_guard",
            action_summary=f"attempted path outside workspace: {path}",
            recoverable=True,
            suggestion="Use a relative path that stays inside the workspace root.",
        )
