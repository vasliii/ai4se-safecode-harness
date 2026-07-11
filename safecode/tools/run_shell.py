"""Tool for running shell commands in a session workspace."""

from __future__ import annotations

import subprocess
from typing import Any

from safecode.models import Session, ToolResult
from safecode.tools.base import Tool


DEFAULT_SHELL_TIMEOUT_SECONDS = 30
UNKNOWN_COMMAND_MARKERS = (
    "command not found",
    "not found",
    "is not recognized",
    "not recognized",
)


class RunShellTool(Tool):
    """Run a shell command in the workspace.

    Safety allowlist checks belong to the upstream Guardrail layer; this tool
    only executes the command it receives and captures raw results.
    """

    name = "run_shell"

    def validate_params(self, params: dict) -> None:
        command = params.get("command")
        if command is None:
            raise ValueError("Missing required command parameter")
        if not isinstance(command, str):
            raise ValueError("command must be a string")
        if not command.strip():
            raise ValueError("command must not be empty")

    def execute(self, params: dict, session: Session) -> ToolResult:
        try:
            self.validate_params(params)
            command = params["command"]
            completed = subprocess.run(
                command,
                cwd=session.workspace_root,
                capture_output=True,
                text=True,
                shell=True,
                timeout=DEFAULT_SHELL_TIMEOUT_SECONDS,
            )
            data = self._result_data(
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                command=command,
            )
            if self._is_unknown_command(completed.stdout, completed.stderr):
                return ToolResult(
                    tool=self.name,
                    success=False,
                    data=data,
                    error=f"Command not found or not recognized: {command}",
                )
            return ToolResult(tool=self.name, success=True, data=data)
        except subprocess.TimeoutExpired as exc:
            return ToolResult(
                tool=self.name,
                success=False,
                error=f"Command timed out after {exc.timeout} seconds",
            )
        except Exception as exc:
            return ToolResult(tool=self.name, success=False, error=str(exc))

    def _is_unknown_command(self, stdout: str, stderr: str) -> bool:
        output = f"{stdout}\n{stderr}".lower()
        return any(marker in output for marker in UNKNOWN_COMMAND_MARKERS)

    def _result_data(
        self,
        *,
        exit_code: int,
        stdout: str,
        stderr: str,
        command: str,
    ) -> dict[str, Any]:
        return {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "command": command,
        }
