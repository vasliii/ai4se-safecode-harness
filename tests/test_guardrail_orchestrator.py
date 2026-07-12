from __future__ import annotations

from pathlib import Path

from safecode.guardrail import Guardrail
from safecode.models import ParsedAction, Session, TaskConfig


SHELL_ALLOWLIST = ["git diff", "git status", "python -m py_compile"]


def make_session(workspace_root: Path) -> Session:
    return Session(
        session_id="session-guardrail",
        task_config=TaskConfig(
            id="task-guardrail",
            title="Guardrail",
            task_type="unit",
            description="Guardrail orchestration",
            workspace_template="template",
            test_command="pytest",
        ),
        workspace_root=workspace_root,
        llm_backend="test",
    )


def check_action(tool: str, params: dict, workspace_root: Path):
    return Guardrail(shell_allowlist=SHELL_ALLOWLIST).check(
        ParsedAction(tool=tool, params=params),
        make_session(workspace_root),
    )


def test_read_file_parent_escape_is_blocked_by_path_guard(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "outside").write_text("outside", encoding="utf-8")

    event = check_action("read_file", {"path": "../outside"}, workspace)

    assert event is not None
    assert event.reason == "path_outside_workspace"
    assert event.recoverable is True
    assert event.suggestion


def test_read_file_sensitive_file_is_blocked_by_sensitive_guard(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    event = check_action("read_file", {"path": ".env"}, workspace)

    assert event is not None
    assert event.reason == "sensitive_file_access"
    assert event.recoverable is True
    assert event.suggestion


def test_run_shell_dangerous_command_is_blocked_by_shell_guard(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    event = check_action("run_shell", {"command": "rm -rf /"}, workspace)

    assert event is not None
    assert event.reason == "dangerous_shell_command"
    assert event.tool == "run_shell"
    assert event.recoverable is True
    assert event.suggestion


def test_safe_read_file_returns_none(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    source = workspace / "src"
    source.mkdir(parents=True)
    (source / "main.py").write_text("print('ok')", encoding="utf-8")

    assert check_action("read_file", {"path": "src/main.py"}, workspace) is None


def test_safe_list_files_returns_none(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    assert check_action("list_files", {"path": "."}, workspace) is None


def test_run_tests_and_finish_are_not_checked(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    assert check_action("run_tests", {}, workspace) is None
    assert check_action("finish", {}, workspace) is None


def test_path_guard_runs_before_sensitive_file_guard(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    event = check_action("read_file", {"path": "../.env"}, workspace)

    assert event is not None
    assert event.reason == "path_outside_workspace"


def test_unknown_tool_has_minimal_noop_behavior(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    assert check_action("unknown_tool", {"path": "../outside"}, workspace) is None


def test_guardrail_is_exported_from_package() -> None:
    assert Guardrail is not None
