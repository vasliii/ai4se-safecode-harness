from __future__ import annotations

import subprocess
from pathlib import Path

from safecode.models import Session, TaskConfig
from safecode.tools.run_shell import RunShellTool


def make_session(workspace_root: Path) -> Session:
    return Session(
        session_id="session-run-shell",
        task_config=TaskConfig(
            id="task-run-shell",
            title="Run shell",
            task_type="unit",
            description="Run shell commands",
            workspace_template="template",
            test_command="pytest",
        ),
        workspace_root=workspace_root,
        llm_backend="test",
    )


def test_run_shell_echo_captures_stdout_and_command(tmp_path: Path) -> None:
    result = RunShellTool().execute({"command": "echo hello"}, make_session(tmp_path))

    assert result.tool == "run_shell"
    assert result.success is True
    assert result.data["exit_code"] == 0
    assert "hello" in result.data["stdout"]
    assert isinstance(result.data["stderr"], str)
    assert result.data["command"] == "echo hello"


def test_run_shell_uses_session_workspace_as_cwd(tmp_path: Path) -> None:
    (tmp_path / "workspace_marker.txt").write_text("marker", encoding="utf-8")
    command = "python -c \"from pathlib import Path; print((Path.cwd() / 'workspace_marker.txt').exists())\""

    result = RunShellTool().execute({"command": command}, make_session(tmp_path))

    assert result.success is True
    assert result.data["exit_code"] == 0
    assert "True" in result.data["stdout"]


def test_run_shell_unknown_command_returns_error_and_preserves_data(tmp_path: Path) -> None:
    command = "definitely_missing_safecode_command_12345"

    result = RunShellTool().execute({"command": command}, make_session(tmp_path))

    assert result.success is False
    assert result.error is not None
    assert "not found" in result.error.lower() or "not recognized" in result.error.lower()
    assert result.data["exit_code"] != 0
    assert isinstance(result.data["stdout"], str)
    assert isinstance(result.data["stderr"], str)
    assert result.data["command"] == command


def test_run_shell_missing_command_returns_clear_error(tmp_path: Path) -> None:
    result = RunShellTool().execute({}, make_session(tmp_path))

    assert result.success is False
    assert result.error is not None
    assert "command" in result.error.lower()
    assert "missing" in result.error.lower() or "required" in result.error.lower()


def test_run_shell_timeout_returns_error(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = RunShellTool().execute({"command": "echo hello"}, make_session(tmp_path))

    assert result.success is False
    assert result.error is not None
    assert "timed out" in result.error.lower() or "timeout" in result.error.lower()


def test_run_shell_subprocess_options_and_data_shape(monkeypatch, tmp_path: Path) -> None:
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen.update(kwargs)
        return subprocess.CompletedProcess(
            args=command,
            returncode=7,
            stdout="out",
            stderr="err",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = RunShellTool().execute({"command": "custom command"}, make_session(tmp_path))

    assert seen["command"] == "custom command"
    assert seen["cwd"] == tmp_path
    assert seen["capture_output"] is True
    assert seen["text"] is True
    assert seen["shell"] is True
    assert seen["timeout"] == 30
    assert result.success is True
    assert result.data == {
        "exit_code": 7,
        "stdout": "out",
        "stderr": "err",
        "command": "custom command",
    }

