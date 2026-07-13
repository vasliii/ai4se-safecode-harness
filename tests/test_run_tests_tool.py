from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from safecode.models import Session, TaskConfig
from safecode.tools.run_tests import RunTestsTool


def make_session(workspace_root: Path) -> Session:
    return Session(
        session_id="session-run-tests",
        task_config=TaskConfig(
            id="task-run-tests",
            title="Run tests",
            task_type="unit",
            description="Run tests",
            workspace_template="template",
            test_command="pytest",
        ),
        workspace_root=workspace_root,
        llm_backend="test",
    )


def write_pytest_file(workspace_root: Path, name: str, content: str) -> None:
    tests_dir = workspace_root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / name).write_text(content, encoding="utf-8")


def test_run_tests_passes_and_captures_output(tmp_path: Path) -> None:
    write_pytest_file(tmp_path, "test_sample.py", "def test_ok():\n    assert True\n")

    result = RunTestsTool().execute({}, make_session(tmp_path))

    assert result.tool == "run_tests"
    assert result.success is True
    assert result.data["exit_code"] == 0
    assert "1 passed" in result.data["stdout"]
    assert isinstance(result.data["stderr"], str)
    assert result.data["command"] == "pytest"


def test_run_tests_failure_is_successful_tool_execution(tmp_path: Path) -> None:
    write_pytest_file(tmp_path, "test_sample.py", "def test_fails():\n    assert False\n")

    result = RunTestsTool().execute({}, make_session(tmp_path))

    assert result.success is True
    assert result.data["exit_code"] == 1
    assert "failed" in result.data["stdout"].lower()
    assert isinstance(result.data["stderr"], str)


def test_run_tests_appends_pytest_args(tmp_path: Path) -> None:
    write_pytest_file(tmp_path, "test_selected.py", "def test_selected():\n    assert True\n")
    write_pytest_file(tmp_path, "test_unselected.py", "def test_unselected():\n    assert False\n")

    result = RunTestsTool().execute({"args": "tests/test_selected.py"}, make_session(tmp_path))

    assert result.success is True
    assert result.data["exit_code"] == 0
    assert result.data["command"] == "pytest tests/test_selected.py"
    assert "1 passed" in result.data["stdout"]


def test_run_tests_uses_session_workspace_as_cwd(tmp_path: Path) -> None:
    (tmp_path / "workspace_marker.txt").write_text("marker", encoding="utf-8")
    write_pytest_file(
        tmp_path,
        "test_cwd.py",
        "from pathlib import Path\n\n"
        "def test_cwd_is_workspace():\n"
        "    assert (Path.cwd() / 'workspace_marker.txt').exists()\n",
    )

    result = RunTestsTool().execute({}, make_session(tmp_path))

    assert result.success is True
    assert result.data["exit_code"] == 0


def test_run_tests_missing_command_returns_error(monkeypatch, tmp_path: Path) -> None:
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("pytest")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = RunTestsTool().execute({}, make_session(tmp_path))

    assert result.success is False
    assert result.error is not None
    assert "not found" in result.error.lower()


def test_run_tests_timeout_returns_error(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = RunTestsTool().execute({}, make_session(tmp_path))

    assert result.success is False
    assert result.error is not None
    assert "timed out" in result.error.lower()


def test_run_tests_nonstandard_exit_code_preserves_output(monkeypatch, tmp_path: Path) -> None:
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen.update(kwargs)
        return subprocess.CompletedProcess(
            args=command,
            returncode=2,
            stdout="usage output",
            stderr="usage error",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = RunTestsTool().execute({}, make_session(tmp_path))

    assert seen["command"] == [sys.executable, "-m", "pytest"]
    assert seen["cwd"] == tmp_path
    assert seen["capture_output"] is True
    assert seen["text"] is True
    assert seen["timeout"] == 60
    assert result.success is False
    assert result.data == {
        "exit_code": 2,
        "stdout": "usage output",
        "stderr": "usage error",
        "command": "pytest",
    }

