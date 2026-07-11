from __future__ import annotations

from pathlib import Path

from safecode.models import ParsedAction, Session, TaskConfig
from safecode.tools import ToolDispatcher, create_default_tools


def make_session(workspace_root: Path) -> Session:
    return Session(
        session_id="session-tool-integration",
        task_config=TaskConfig(
            id="task-tool-integration",
            title="Tool integration",
            task_type="unit",
            description="Integrate default tools",
            workspace_template="template",
            test_command="pytest",
        ),
        workspace_root=workspace_root,
        llm_backend="test",
    )


def test_default_tools_dispatch_list_files(tmp_path: Path) -> None:
    (tmp_path / "sample.txt").write_text("hello", encoding="utf-8")
    dispatcher = ToolDispatcher(create_default_tools())

    result = dispatcher.dispatch(
        ParsedAction(tool="list_files", params={"path": "."}),
        make_session(tmp_path),
    )

    assert result.success is True
    assert result.tool == "list_files"
    assert "sample.txt" in result.data["files"]


def test_default_tools_dispatch_read_file(tmp_path: Path) -> None:
    (tmp_path / "sample.txt").write_text("safe content", encoding="utf-8")
    dispatcher = ToolDispatcher(create_default_tools())

    result = dispatcher.dispatch(
        ParsedAction(tool="read_file", params={"path": "sample.txt"}),
        make_session(tmp_path),
    )

    assert result.success is True
    assert result.tool == "read_file"
    assert result.data["content"] == "safe content"


def test_default_tools_dispatch_run_shell(tmp_path: Path) -> None:
    dispatcher = ToolDispatcher(create_default_tools())

    result = dispatcher.dispatch(
        ParsedAction(tool="run_shell", params={"command": "echo registry-test"}),
        make_session(tmp_path),
    )

    assert result.success is True
    assert result.tool == "run_shell"
    assert "registry-test" in result.data["stdout"]
