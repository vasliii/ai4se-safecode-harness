"""Shell command guardrail for run_shell actions."""

from __future__ import annotations

from typing import Optional

from safecode.models import GuardrailEvent


DANGEROUS_COMMAND_PATTERNS = (
    "rm -rf /",
    "rm -rf /*",
    "del /F /S",
    "rmdir",
    "format",
    "shutdown",
    "curl | sh",
    "npm publish",
    "git push --force",
    "chmod 777",
    "dd if=",
    "mkfs",
    ":(){ :|:& };:",
)
EXACT_ALLOWLIST_COMMANDS = {
    "pip install pytest",
    "python -m pip install pytest",
}


class ShellGuard:
    """Block dangerous shell commands and commands outside an allowlist."""

    def check(self, command: str | None, allowlist: list[str]) -> Optional[GuardrailEvent]:
        if command is None:
            return None

        command_value = str(command)
        stripped = command_value.strip()
        if stripped == "":
            return None

        if self._is_dangerous(stripped):
            return self._blocked(command_value, "dangerous shell command")

        if self._is_allowed(stripped, allowlist):
            return None

        return self._blocked(command_value, "command is not in the shell allowlist")

    def _is_dangerous(self, command: str) -> bool:
        normalized = " ".join(command.split())
        return any(self._matches_dangerous_pattern(normalized, pattern) for pattern in DANGEROUS_COMMAND_PATTERNS)

    def _matches_dangerous_pattern(self, command: str, pattern: str) -> bool:
        if pattern == "curl | sh":
            return command.startswith("curl ") and "| sh" in command
        return command.startswith(pattern)

    def _is_allowed(self, command: str, allowlist: list[str]) -> bool:
        for allowed in allowlist:
            if allowed in EXACT_ALLOWLIST_COMMANDS:
                if command == allowed:
                    return True
                continue
            if command.startswith(allowed):
                return True
        return False

    def _blocked(self, command: str, reason_detail: str) -> GuardrailEvent:
        return GuardrailEvent(
            reason="dangerous_shell_command",
            tool="run_shell",
            action_summary=f"blocked shell command ({reason_detail}): {command}",
            recoverable=True,
            suggestion="Use a safe command from the configured shell allowlist.",
        )
