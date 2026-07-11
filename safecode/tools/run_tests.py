"""Tool for running pytest in a session workspace."""

from __future__ import annotations

import shlex
import subprocess
from typing import Any

from safecode.models import Session, ToolResult
from safecode.tools.base import Tool


DEFAULT_TEST_TIMEOUT_SECONDS = 60


class RunTestsTool(Tool):
    """Run pytest inside the session workspace and return raw output."""

    name = "run_tests"

    def validate_params(self, params: dict) -> None:
        args = params.get("args")
        if args is not None and not isinstance(args, str):
            raise ValueError("args must be a string")

    def execute(self, params: dict, session: Session) -> ToolResult:
        try:
            self.validate_params(params)
            command = self._build_command(params)
            command_text = " ".join(command)
            completed = subprocess.run(
                command,
                cwd=session.workspace_root,
                capture_output=True,
                text=True,
                timeout=DEFAULT_TEST_TIMEOUT_SECONDS,
            )
            data = self._result_data(
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                command=command_text,
            )
            if completed.returncode in (0, 1):
                return ToolResult(tool=self.name, success=True, data=data)
            return ToolResult(
                tool=self.name,
                success=False,
                data=data,
                error=f"Test command exited with code {completed.returncode}",
            )
        except subprocess.TimeoutExpired as exc:
            return ToolResult(
                tool=self.name,
                success=False,
                error=f"Test execution timed out after {exc.timeout} seconds",
            )
        except FileNotFoundError as exc:
            missing = exc.filename or "pytest"
            return ToolResult(
                tool=self.name,
                success=False,
                error=f"Test command not found: {missing}",
            )
        except Exception as exc:
            return ToolResult(tool=self.name, success=False, error=str(exc))

    def _build_command(self, params: dict[str, Any]) -> list[str]:
        command = ["pytest"]
        args = params.get("args")
        if args:
            command.extend(shlex.split(args))
        return command

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
