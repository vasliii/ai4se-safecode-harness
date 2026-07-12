"""Guardrail orchestrator for parsed actions."""

from __future__ import annotations

from typing import Optional

from safecode.guardrail.path_guard import PathGuard
from safecode.guardrail.sensitive_file_guard import SensitiveFileGuard
from safecode.guardrail.shell_guard import ShellGuard
from safecode.models import GuardrailEvent, ParsedAction, Session


FILE_TOOLS = {"list_files", "read_file", "search_content", "write_file", "edit_file"}
SENSITIVE_FILE_TOOLS = {"read_file", "write_file", "edit_file"}


class Guardrail:
    """Run applicable guard checks in deterministic order."""

    def __init__(self, shell_allowlist: list[str]) -> None:
        self.shell_allowlist = shell_allowlist
        self.path_guard = PathGuard()
        self.sensitive_file_guard = SensitiveFileGuard()
        self.shell_guard = ShellGuard()

    def check(self, action: ParsedAction, session: Session) -> Optional[GuardrailEvent]:
        if action.tool in FILE_TOOLS:
            path_event = self.path_guard.check(action.params.get("path"), session.workspace_root)
            if path_event is not None:
                return path_event

            if action.tool in SENSITIVE_FILE_TOOLS:
                sensitive_event = self.sensitive_file_guard.check(action.params.get("path"))
                if sensitive_event is not None:
                    return sensitive_event

            return None

        if action.tool == "run_shell":
            return self.shell_guard.check(action.params.get("command"), self.shell_allowlist)

        if action.tool in {"run_tests", "finish"}:
            return None

        return None
